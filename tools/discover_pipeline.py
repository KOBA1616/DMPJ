"""ループと手順の自律発見パイプライン（docs/loop-discovery.md）。

学習は2層に分ける。
- マクロ（大局観）: ターンの初めに局面全体を見て、このターンの狙い（intent）を決める。
  整える / ループ導入 / リーサル（ループキル）実行 / 妨害。狙いごとに探索の予算・
  ストック方針・目標部品を切り替える。学習対象は「局面の特徴 → 狙い」の対応。
- ミクロ（詳細）: ターン内の個々の決定（プレイ順、捨てる札、蘇生先、回すか抜けるか、
  リソースの温存）を方策が案内する。学習対象は「決定の種類と文脈 → 選ぶキー」の選好。

パイプラインの段階:
  1. ゾーン変換グラフでループ候補を静的に列挙する
  2. 初期盤面から探索の収集モードでループ証明書を動的に発見し、再生で検証する
  3. 教師（最初は台本）で案内した探索の勝ち手順を再生しながら決定データを収穫する
  4. 収穫データからミクロ選好を学習し、方策ファイル (JSON) に出す
  5. 学習方策だけで案内した探索を、未使用シードの初期盤面で検証する
  6. マクロが狙いを切り替える階層版でも同じ検証を行い、ミクロ単独と比較する

実行: PYTHONPATH=. python tools/discover_pipeline.py [--train 20] [--holdout 30] [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))          # tools/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # リポジトリ直下

from discover_dig import ME, start as saga_start  # noqa: E402
from loopcheck_full_chain import policy as script_policy  # noqa: E402

import dmsim.solitaire as sol  # noqa: E402
from dmsim.defs import load_rules  # noqa: E402
from dmsim.loop_first import discover_loops  # noqa: E402
from dmsim.zone_graph import find_cycles  # noqa: E402

_SOL_CANDIDATES = sol.candidates   # 差し替え前の候補生成（モジュール読み込み時に退避）

SAGA, SHAKO, DRAG, IWA = "dm22ex2-021", "dmrp03-s03", "dm22ex1-007", "dmrp03-036"
BUDGET = 3000

# 勝ち方の文脈。検出器の analyze が分類するのは相手山札切れとシールド0までで、
# サガのような置換勝利（自分の山札切れを効果で勝ちに変える）は win_by=None になる。
# 勝ち方で「何を守り、何を伸ばすか」が逆転する（例: 置換勝利では自分の山札が命綱、
# シールド0型では相手のシールドと打点が全て）ため、マクロ・ミクロ双方の文脈に入れる。
WIN_CONTEXTS = ("opp_deck_out", "shield_zero", "effect", "resource")


def dig_prob(deck_n: int, hits: int, look: int = 5) -> float:
    """山札の上から look 枚を見たとき、欲しいカードが少なくとも1枚ある確率。

    山札の厚さそのものではなく、「残りの山札に欲しいカードが何枚残っていて、
    それを掘れるか」で判断するための特徴。残り枚数はデッキリストから公開領域
    （手札・墓地・マナ・場）を引いたものと等しい。
    """
    from math import comb
    if deck_n <= 0 or hits <= 0:
        return 0.0
    look = min(look, deck_n)
    if deck_n - hits < look:
        return 1.0
    return round(1.0 - comb(deck_n - hits, look) / comb(deck_n, look), 3)


def classify_win(win_by: str | None, verified: bool = False) -> str:
    """証明書の win_by と検証結果から勝ち方の文脈を決める。

    win_by が無いのに検証で勝てているなら、ループ中の効果で勝った（置換勝利など）。
    勝てていないものは資源を増やすだけの循環として扱う。
    """
    if win_by in WIN_CONTEXTS:
        return win_by
    return "effect" if verified else "resource"


# ---- マクロ（大局観） ---------------------------------------------------------------------------

@dataclass
class Intent:
    """このターンの狙いと、その狙いで探索をどう動かすか。"""
    name: str                       # setup / enter_loop / execute / beatdown / control / disrupt
    budget: int = BUDGET
    burn_stock: bool = True         # 山札を削るループを自動でストックするか
    stock_offsets: tuple = (0, 1)   # ストック量の候補（上限から何周手前まで試すか）
    weights: object = None          # この狙い用の evaluate の重み（None なら既定）
    note: str = ""


@dataclass
class MacroPlanner:
    """局面の特徴から狙いを決める。v3 はサガループを目標にした規則ベース。

    v2 の前提（墓地の準備・闇マナ）に加え、目標ループの勝ち方（win_by）を文脈に入れる。
    setup の山札保護と execute の評価の重みは勝ち方で切り替わる: 置換勝利（effect）では
    自分の山札が勝敗に直結するので厚く守り、シールド0型では相手のシールドと打点を、
    相手山札切れ型では相手の山札の消費を優先する。

    学習版では、この「特徴 → 狙い」の対応自体を、狙いごとの勝率・到達率から学ぶ想定。
    特徴はゾーンごとの部品の有無と山札・マナ・ターンという、ループに依らない形に寄せる。
    """
    loop_card: str = SAGA
    kill_pieces_hand: tuple = (DRAG,)
    kill_pieces_grave: tuple = (IWA, SHAKO)
    win_by: str = "effect"          # 目標ループの勝ち方（classify_win の値）
    bruce_card: str = "dmbd17-009"  # 墓地の起点を場に戻す呪文面を持つツインパクト
    digger_card: str = "dm22ex1-025"  # 登場時に山札の上5枚から1枚を手札に加える（起点を探せる）

    def features(self, eng, me: int = ME) -> dict:
        z = eng.s.zones
        names = lambda zone: [eng.s.cards[c].defn for c in z[zone][me]]  # noqa: E731
        hand, grave = names("hand"), names("graveyard")
        dark_mana = sum(1 for c in z["mana"][me]
                        if "darkness" in eng.cdef(c).face(None).civs)

        def threat(p: int) -> int:
            # 次に攻撃できる打点の近似（evaluate と同じ見方: 場のクリーチャーのブレイク数）
            return sum(eng.chars(c)["breaks"] for c in eng.bz_tops(p)
                       if "creature" in eng.chars(c)["types"])

        deck_names = names("deck")
        targets = (self.loop_card, self.digger_card, self.bruce_card) \
            + self.kill_pieces_hand + self.kill_pieces_grave
        pieces_in_deck = sum(1 for n in deck_names if n in targets)
        return {
            "turn": eng.s.turn,
            "win_by": self.win_by,
            "deck": len(z["deck"][me]),
            "pieces_in_deck": pieces_in_deck,
            "dig_hit_prob": dig_prob(len(deck_names), pieces_in_deck),
            "hand_n": len(hand),
            "mana": len(z["mana"][me]),
            "dark_mana": dark_mana,
            "loop_available": self.loop_card in hand or self.loop_card in grave,
            "grave_prep": self.loop_card in grave or "dm26ex2-071" in grave,
            "bruce_route": (self.loop_card in hand and self.digger_card in hand
                            and self.bruce_card in hand),
            "intro_in_hand": sum(1 for p in (SAGA, "dm22ex1-025", "dmex10-020") if p in hand),
            "kill_in_hand": all(p in hand for p in self.kill_pieces_hand),
            "kill_in_grave": all(p in grave for p in self.kill_pieces_grave),
            "opp_shield": len(z["shield"][1 - me]),
            "opp_deck": len(z["deck"][1 - me]),
            "my_threat": threat(me),
            "opp_threat": threat(1 - me),
        }

    def plan(self, eng, me: int = ME) -> Intent:
        f = self.features(eng, me)
        if f["kill_in_hand"] and f["kill_in_grave"]:
            # 部品が揃えば山札の厚さは条件にしない。コンボを決め切れば、
            # 山札が尽きる前に勝てる（尽きるのは負けになる時だけ悪い）
            w = None
            if self.win_by == "shield_zero":
                w = sol.Weights(shield=200.0, threat=80.0, board=6.0)
            elif self.win_by == "opp_deck_out":
                w = sol.Weights(opp_deck=30.0, shield=50.0)
            elif self.win_by == "resource":
                w = sol.Weights(hand=10.0, mana=20.0)
            return Intent("execute", weights=w,
                          note="キル部品が揃った。ループキルを取りに行く")
        if f["loop_available"] and f["grave_prep"] and f["dark_mana"] >= 1:
            return Intent("enter_loop", note="起点と墓地の準備と闇マナがある。導入して部品を集める")
        if f["bruce_route"] and f["dark_mana"] >= 1:
            # 起点が1枚しかなくても、掘る役の登場時効果で山札から起点や部品を探し、
            # 呪文面で墓地の起点を場に戻せる。墓地の準備が無くても導入に値する
            return Intent("enter_loop", note="ブルース経由: 掘る役で探し、呪文面で起点を戻して導入する")
        # ループ以外の勝ち筋: 盤面で殴り切れるならそれが最速（ビートダウン）
        if f["my_threat"] >= f["opp_shield"] + 1:
            return Intent("execute", weights=sol.Weights(shield=200.0, threat=80.0, board=6.0),
                          note="盤面の打点でリーサルが見える。殴り切る")
        if f["my_threat"] >= 2:
            return Intent("beatdown", weights=sol.Weights(shield=200.0, threat=80.0, board=6.0),
                          note="ループの筋が無く盤面の圧力がある。シールドを削りに行く")
        if f["opp_threat"] >= 3 and f["opp_threat"] > f["my_threat"]:
            # コントロール: 相手の圧力が高い間は盤面を捌いてターンを稼ぎ、
            # 手札とマナを整えてコンボの確率を上げる
            return Intent("control", budget=800,
                          weights=sol.Weights(board=8.0, hand=6.0, shield=120.0),
                          note="相手の圧力が高い。盤面を捌いてターンを稼ぐ")
        # 整える: 山札は「尽きて負ける」時だけ悪いので、守るのは残りわずかの時だけ。
        # 固定の厚さを基準にせず、山札切れの直前（deck_keep=2）まで削ることを許す。
        # 置換勝利では、勝敗に直結しない資源ループの自動反復だけは止める。
        if self.win_by == "effect":
            w, burn = sol.Weights(stock_cap=0, deck_keep=2), False
            note = "部品か前提が不足。山札切れの直前だけ守って整える"
        elif self.win_by == "resource":
            w, burn = sol.Weights(stock_cap=4, deck_keep=2), True
            note = "部品か前提が不足。資源を貯めながら整える"
        else:
            w, burn = sol.Weights(stock_cap=8, deck_keep=2), True
            note = "部品か前提が不足。自分の山札の消耗は許して整える"
        return Intent("setup", budget=600, burn_stock=burn, weights=w, note=note)


# ---- ミクロ（詳細） -----------------------------------------------------------------------------

def deck_bucket(deck_n: int) -> str:
    """文脈の粗い切り分け。山札の厚さで捨てる／残すの判断が変わるため。"""
    return "thin" if deck_n <= 8 else "mid" if deck_n <= 18 else "thick"


def grave_bucket(eng, player: int) -> str:
    """墓地のクリーチャー数の区分。サガの蘇生条件（3体以上）で判断が切り替わるため、
    山札の厚さとは独立の文脈として持つ。"""
    n = 0
    for c in eng.s.zones["graveyard"][player]:
        if "creature" in (eng.cdef(c).face(None).types or []):
            n += 1
    return "g3p" if n >= 3 else "g02"


def learn_preferences(records: list[dict]) -> dict:
    """決定レコードから、決定の種類ごとのキーの選好率を学ぶ。

    records: [{"kind":..., "options":[key...], "chosen":[key...]}]
    選好率 = 選べた回数のうち選ばれた割合。出現1回だけのキーはノイズとして捨てる。
    """
    avail: dict[str, Counter] = defaultdict(Counter)
    chosen: dict[str, Counter] = defaultdict(Counter)
    for rec in records:
        for k in rec["options"]:
            avail[rec["kind"]][k] += 1
        for k in rec["chosen"]:
            chosen[rec["kind"]][k] += 1
    policy: dict[str, dict[str, float]] = {}
    for kind, counter in avail.items():
        policy[kind] = {k: round(chosen[kind][k] / a, 3)
                        for k, a in counter.items() if a >= 2}
    # 文脈条件付き: 山札の厚さごとに同じ集計をする（データが薄い区分は使わない）
    by_bucket: dict[str, dict] = {}
    buckets = sorted({r.get("bucket") for r in records if r.get("bucket")})
    for b in buckets:
        sub = [r for r in records if r.get("bucket") == b]
        b_avail: dict[str, Counter] = defaultdict(Counter)
        b_chosen: dict[str, Counter] = defaultdict(Counter)
        for rec in sub:
            for k in rec["options"]:
                b_avail[rec["kind"]][k] += 1
            for k in rec["chosen"]:
                b_chosen[rec["kind"]][k] += 1
        by_bucket[b] = {kind: {k: round(b_chosen[kind][k] / a, 3)
                               for k, a in counter.items() if a >= 2}
                        for kind, counter in b_avail.items()}
    # 文脈ごとにも集計する。文脈は 勝ち方×厚さ（v3）と、勝ち方×狙い×墓地区分×厚さ
    # （v4）の2段。同じ厚さでも、整えるターンとループのターンでは捨てる札が違い、
    # 墓地のクリーチャー数が蘇生条件を満たすかどうかでも判断が切り替わる。
    # 区分のデータが薄ければ、その段は使われず下の段に落ちる。
    by_context: dict[str, dict] = {}

    def aggregate(sub):
        c_avail: dict[str, Counter] = defaultdict(Counter)
        c_chosen: dict[str, Counter] = defaultdict(Counter)
        for rec in sub:
            for k in rec["options"]:
                c_avail[rec["kind"]][k] += 1
            for k in rec["chosen"]:
                c_chosen[rec["kind"]][k] += 1
        return {kind: {k: round(c_chosen[kind][k] / a, 3)
                       for k, a in counter.items() if a >= 2}
                for kind, counter in c_avail.items()}

    for wb in sorted({r.get("win_by") or "any" for r in records}):
        for b in sorted({r["bucket"] for r in records if r.get("bucket")}):
            sub = [r for r in records
                   if (r.get("win_by") or "any") == wb and r.get("bucket") == b]
            if sub:
                by_context[f"{wb}|{b}"] = aggregate(sub)
            for intent in sorted({r.get("intent") or "any" for r in sub}):
                for g in sorted({r.get("grave") or "any" for r in sub}):
                    sub2 = [r for r in sub if (r.get("intent") or "any") == intent
                            and (r.get("grave") or "any") == g]
                    if sub2:
                        by_context[f"{wb}|{intent}|{g}|{b}"] = aggregate(sub2)
    return {"global": policy, "by_bucket": by_bucket, "by_context": by_context}


@dataclass
class MicroPolicy:
    """ターン内の決定を案内する方策。

    v4: 文脈は山札の厚さだけではない。重ね順は 全体 → 厚さ区分 → 勝ち方×厚さ →
    勝ち方×狙い×墓地区分×厚さ。整えるターンとループのターンでは同じ決定でも
    正解が違い、墓地のクリーチャー数が蘇生条件を満たすかでも判断が切り替わる。
    狙い（intent）は階層版でマクロがターンごとに差し込む。
    """
    preferences: dict = field(default_factory=dict)
    win_by: str = "effect"          # この方策が狙う勝ち方
    intent: str | None = None       # このターンの狙い（マクロが設定する）

    def prefer(self, eng, d) -> list[int] | None:
        prefs = self.preferences or {}
        if "global" in prefs:   # v2 以降の形式
            rates = dict(prefs["global"].get(d["kind"], {}))
            if eng is not None:
                bucket = deck_bucket(len(eng.s.zones["deck"][d["player"]]))
                rates.update(prefs.get("by_bucket", {}).get(bucket, {}).get(d["kind"], {}))
                by_ctx = prefs.get("by_context", {})
                rates.update(by_ctx.get(f"{self.win_by}|{bucket}", {}).get(d["kind"], {}))
                if self.intent is not None:
                    key = f"{self.win_by}|{self.intent}|{grave_bucket(eng, d['player'])}|{bucket}"
                    rates.update(by_ctx.get(key, {}).get(d["kind"], {}))
        else:                    # v1 形式（kind の直下にキー選好）
            rates = prefs.get(d["kind"], {})
        if not rates:
            return None
        keys = [o["key"] for o in d["options"]]
        scored = sorted(range(len(keys)), key=lambda j: -rates.get(keys[j], 0.0))
        n = d["min"] if d["min"] >= 1 else 1
        if not (d["min"] <= n <= d["max"]):
            return None
        return sorted(scored[:n])

    def candidates(self, eng, d, w, cap: int = 6):
        """solitaire.candidates と同じ形。方策の答えを候補の先頭に置く。"""
        out = _base_candidates(eng, d, w, cap)
        pref = self.prefer(eng, d)
        if pref is None:
            return out
        rest = [c for c in out if list(c) != pref]
        return [pref] + rest[: max(cap - 1, 0)]


def _base_candidates(eng, d, w, cap):
    """差し替え前の solitaire.candidates。

    以前は Pipeline 初期化時の退避に頼っていたため、MicroPolicy を単独で
    sol.candidates に差し込むと自分自身を呼び続けて再帰した。読み込み時に退避する。
    """
    return _SOL_CANDIDATES(eng, d, w, cap)


def script_candidates(eng, d, w, cap: int = 6):
    """教師（台本）で案内する候補順序。収穫段階でのみ使う。"""
    out = _base_candidates(eng, d, w, cap)
    try:
        pref = list(script_policy(eng, d))
    except Exception:
        return out
    keys = [o["key"] for o in d["options"]]
    if not (d["min"] <= len(pref) <= d["max"] and all(0 <= j < len(keys) for j in pref)):
        return out
    rest = [c for c in out if list(c) != pref]
    return [pref] + rest[: max(cap - 1, 0)]


# ---- パイプライン --------------------------------------------------------------------------------

class Pipeline:
    def __init__(self, rules, out_dir: Path, win_by: str = "effect"):
        self.rules = rules
        self.win_by = win_by        # 目標ループの勝ち方（マクロ・ミクロの文脈）
        self.out = out_dir
        self.out.mkdir(parents=True, exist_ok=True)
        if not hasattr(sol, "_orig_candidates"):
            sol._orig_candidates = sol.candidates

    def build(self, seed: int):
        rng = random.Random(seed)
        return saga_start(self.rules, rng, deck_left=18)

    # 段階1
    def static_candidates(self) -> dict:
        cycles = find_cycles(self.rules, max_cards=2)
        return {"count": len(cycles),
                "top": [{"cards": c.cards, "delta": c.delta(), "period": c.period}
                         for c in cycles[:30]]}

    # 段階2
    def dynamic_loops(self, seeds: list[int]) -> dict:
        found: dict[str, dict] = {}
        for s in seeds:
            for f in discover_loops(self.build(s), ME, budget=BUDGET):
                key = json.dumps(f.cert.delta, sort_keys=True) + f"/len{len(f.cert.actions)}"
                e = found.setdefault(key, {"delta": f.cert.delta, "length": len(f.cert.actions),
                                            "win_by": classify_win(f.cert.win_by, f.verified),
                                            "verified": False, "setups": 0})
                e["setups"] += 1
                e["verified"] = e["verified"] or f.verified
                e["win_by"] = classify_win(f.cert.win_by, e["verified"])
        return {"distinct_loops": len(found),
                "verified_loops": sum(1 for v in found.values() if v["verified"]),
                "loops": sorted(found.values(), key=lambda x: -x["setups"])}

    def run_search(self, seed: int, candidates_fn, intent: Intent | None = None):
        sol.candidates = candidates_fn
        eng = self.build(seed)
        t0 = eng.s.turn
        ts = sol.TurnSearch(ME, (intent.budget if intent else BUDGET),
                            intent.weights if intent else None)
        if intent:
            ts.burn_stock = intent.burn_stock
            ts.stock_offsets = tuple(intent.stock_offsets)
        out, st = ts.run(eng)
        r = out.s.result
        won = bool(r and r.get("winner") == ME and r.get("turn") == t0)
        return won, out, st.nodes

    # 段階3
    def harvest(self, seeds: list[int]):
        wins, records = 0, []
        planner = MacroPlanner(win_by=self.win_by)
        for s in seeds:
            won, leaf, _ = self.run_search(s, script_candidates)
            if not won:
                continue
            eng = self.build(s)
            intent_name = planner.plan(eng).name   # このターンの狙いを文脈として記録する
            i, ok = 0, True
            for _ in range(4000):
                d = eng.advance()
                if d is None or eng.s.result:
                    break
                if i >= len(leaf.log):
                    ok = False
                    break
                entry = leaf.log[i]
                i += 1
                if d["player"] == ME:
                    deck_n = len(eng.s.zones["deck"][ME])
                    records.append({"kind": d["kind"],
                                    "options": [o["key"] for o in d["options"]],
                                    "chosen": entry["keys"],
                                    "deck": deck_n, "bucket": deck_bucket(deck_n),
                                    "win_by": self.win_by, "intent": intent_name,
                                    "grave": grave_bucket(eng, ME)})
                try:
                    eng.answer_by_keys(entry["keys"])
                except Exception:
                    ok = False
                    break
            r = eng.s.result
            if ok and r and r.get("winner") == ME:
                wins += 1
            else:
                print(f"  seed {s}: 再生で勝ちを再現できず、収穫に数えない", flush=True)
        return wins, records

    # 段階5・6
    def evaluate(self, seeds: list[int], micro: MicroPolicy, macro: MacroPlanner | None):
        wins, nodes = 0, 0
        for s in seeds:
            if macro is not None:
                intent = macro.plan(self.build(s))
                micro.intent = intent.name   # ミクロの文脈にこのターンの狙いを渡す
                try:
                    won, _, nd = self.run_search(s, micro.candidates, intent)
                finally:
                    micro.intent = None
            else:
                won, _, nd = self.run_search(s, micro.candidates)
            wins += won
            nodes += nd
        return {"setups": len(seeds), "wins": wins,
                "avg_nodes": round(nodes / max(len(seeds), 1))}


def main(argv=None):
    ap = argparse.ArgumentParser(description="ループと手順の自律発見パイプライン")
    ap.add_argument("--train", type=int, default=20)
    ap.add_argument("--holdout", type=int, default=30)
    ap.add_argument("--out", default="loop_discovery_out")
    a = ap.parse_args(argv)

    rules = load_rules()
    pipe = Pipeline(rules, Path(a.out))
    catalog: dict = {}
    t_all = time.time()

    print("段階1: ループ候補の静的列挙", flush=True)
    catalog["stage1_static_candidates"] = pipe.static_candidates()
    print(f"  候補 {catalog['stage1_static_candidates']['count']} 件", flush=True)

    print("段階2: 初期盤面からのループ発見", flush=True)
    catalog["stage2_dynamic_loops"] = pipe.dynamic_loops([10_000 + i for i in range(5)])
    print(f"  distinct {catalog['stage2_dynamic_loops']['distinct_loops']}, "
          f"検証済み {catalog['stage2_dynamic_loops']['verified_loops']}", flush=True)

    print(f"段階3: 勝ち手順の収穫（訓練シード{a.train}件）", flush=True)
    wins, records = pipe.harvest([10_000 + i for i in range(a.train)])
    catalog["stage3_harvest"] = {"train_setups": a.train, "wins": wins,
                                  "decision_records": len(records)}
    print(f"  勝ち {wins}/{a.train}, 決定レコード {len(records)} 件", flush=True)

    print("段階4: ミクロ選好の学習", flush=True)
    micro = MicroPolicy(learn_preferences(records), win_by=pipe.win_by)
    (pipe.out / "learned_policy.json").write_text(
        json.dumps(micro.preferences, ensure_ascii=False, indent=1), encoding="utf-8")
    catalog["stage4_learned_kinds"] = {k: len(v) for k, v in micro.preferences["global"].items()}

    print(f"段階5: 未使用シード{a.holdout}件で検証（ミクロ単独）", flush=True)
    holdout = [50_000 + i for i in range(a.holdout)]
    catalog["stage5_holdout_micro_only"] = pipe.evaluate(holdout, micro, None)
    print(f"  {catalog['stage5_holdout_micro_only']}", flush=True)

    print("段階6: マクロ＋ミクロの階層版で検証", flush=True)
    catalog["stage6_holdout_hierarchical"] = pipe.evaluate(holdout, micro, MacroPlanner(win_by=pipe.win_by))
    print(f"  {catalog['stage6_holdout_hierarchical']}", flush=True)

    catalog["elapsed_sec"] = round(time.time() - t_all)
    (pipe.out / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"DONE in {catalog['elapsed_sec']}s -> {a.out}/catalog.json", flush=True)
    return catalog


if __name__ == "__main__":
    main()
