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


# ---- マクロ（大局観） ---------------------------------------------------------------------------

@dataclass
class Intent:
    """このターンの狙いと、その狙いで探索をどう動かすか。"""
    name: str                       # setup / enter_loop / execute / disrupt
    budget: int = BUDGET
    burn_stock: bool = True         # 山札を削るループを自動でストックするか
    stock_offsets: tuple = (0, 1)   # ストック量の候補（上限から何周手前まで試すか）
    weights: object = None          # この狙い用の evaluate の重み（None なら既定）
    note: str = ""


@dataclass
class MacroPlanner:
    """局面の特徴から狙いを決める。v2 はサガループを目標にした規則ベース
    （前提として墓地の準備と闇マナを見るようにし、setup では山札を守る重みを使う）。

    学習版では、この「特徴 → 狙い」の対応自体を、狙いごとの勝率・到達率から学ぶ想定。
    特徴はゾーンごとの部品の有無と山札・マナ・ターンという、ループに依らない形に寄せる。
    """
    loop_card: str = SAGA
    kill_pieces_hand: tuple = (DRAG,)
    kill_pieces_grave: tuple = (IWA, SHAKO)

    def features(self, eng, me: int = ME) -> dict:
        z = eng.s.zones
        names = lambda zone: [eng.s.cards[c].defn for c in z[zone][me]]  # noqa: E731
        hand, grave = names("hand"), names("graveyard")
        dark_mana = sum(1 for c in z["mana"][me]
                        if "darkness" in eng.cdef(c).face(None).civs)
        return {
            "turn": eng.s.turn,
            "deck": len(z["deck"][me]),
            "hand_n": len(hand),
            "mana": len(z["mana"][me]),
            "dark_mana": dark_mana,
            "loop_available": self.loop_card in hand or self.loop_card in grave,
            "grave_prep": self.loop_card in grave or "dm26ex2-071" in grave,
            "intro_in_hand": sum(1 for p in (SAGA, "dm22ex1-025", "dmex10-020") if p in hand),
            "kill_in_hand": all(p in hand for p in self.kill_pieces_hand),
            "kill_in_grave": all(p in grave for p in self.kill_pieces_grave),
            "opp_shield": len(z["shield"][1 - me]),
            "opp_deck": len(z["deck"][1 - me]),
        }

    def plan(self, eng, me: int = ME) -> Intent:
        f = self.features(eng, me)
        if f["kill_in_hand"] and f["kill_in_grave"] and f["deck"] <= 10:
            return Intent("execute", note="キル部品が揃い山札も薄い。ループキルを取りに行く")
        if f["loop_available"] and f["grave_prep"] and f["dark_mana"] >= 1:
            return Intent("enter_loop", note="起点と墓地の準備と闇マナがある。導入して部品を集める")
        # 整える: 山札を削らず、手札とマナの評価を優先してターンを渡す
        w = sol.Weights(stock_cap=0, deck_keep=18)
        return Intent("setup", budget=600, burn_stock=False, weights=w,
                      note="部品か前提が不足。山札を守って手札とマナを整える")


# ---- ミクロ（詳細） -----------------------------------------------------------------------------

def deck_bucket(deck_n: int) -> str:
    """文脈の粗い切り分け。山札の厚さで捨てる／残すの判断が変わるため。"""
    return "thin" if deck_n <= 8 else "mid" if deck_n <= 18 else "thick"


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
    return {"global": policy, "by_bucket": by_bucket}


@dataclass
class MicroPolicy:
    """ターン内の決定を案内する方策。

    v2: 決定の種類ごとのキー選好率に、文脈（山札の厚さの区分）ごとの選好を重ねる。
    区分のデータが無い決定は全体の選好に落とす。
    """
    preferences: dict = field(default_factory=dict)

    def prefer(self, eng, d) -> list[int] | None:
        prefs = self.preferences or {}
        if "global" in prefs:   # v2 形式
            rates = dict(prefs["global"].get(d["kind"], {}))
            if eng is not None:
                bucket = deck_bucket(len(eng.s.zones["deck"][d["player"]]))
                rates.update(prefs.get("by_bucket", {}).get(bucket, {}).get(d["kind"], {}))
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
    def __init__(self, rules, out_dir: Path):
        self.rules = rules
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
                                            "win_by": f.cert.win_by, "verified": False, "setups": 0})
                e["setups"] += 1
                e["verified"] = e["verified"] or f.verified
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
        for s in seeds:
            won, leaf, _ = self.run_search(s, script_candidates)
            if not won:
                continue
            eng = self.build(s)
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
                                    "deck": deck_n, "bucket": deck_bucket(deck_n)})
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
                won, _, nd = self.run_search(s, micro.candidates, intent)
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
    micro = MicroPolicy(learn_preferences(records))
    (pipe.out / "learned_policy.json").write_text(
        json.dumps(micro.preferences, ensure_ascii=False, indent=1), encoding="utf-8")
    catalog["stage4_learned_kinds"] = {k: len(v) for k, v in micro.preferences["global"].items()}

    print(f"段階5: 未使用シード{a.holdout}件で検証（ミクロ単独）", flush=True)
    holdout = [50_000 + i for i in range(a.holdout)]
    catalog["stage5_holdout_micro_only"] = pipe.evaluate(holdout, micro, None)
    print(f"  {catalog['stage5_holdout_micro_only']}", flush=True)

    print("段階6: マクロ＋ミクロの階層版で検証", flush=True)
    catalog["stage6_holdout_hierarchical"] = pipe.evaluate(holdout, micro, MacroPlanner())
    print(f"  {catalog['stage6_holdout_hierarchical']}", flush=True)

    catalog["elapsed_sec"] = round(time.time() - t_all)
    (pipe.out / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"DONE in {catalog['elapsed_sec']}s -> {a.out}/catalog.json", flush=True)
    return catalog


if __name__ == "__main__":
    main()
