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
from dmsim.engine import Engine  # noqa: E402
from dmsim.loop import fast_forward  # noqa: E402
from dmsim.loop_first import cycle_counts  # noqa: E402
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
    suppress_beatdown: bool = True  # 一時的にビートダウンを抑え、ループ等の発見に寄せる
    allow_dig_enter: bool = True    # 部品の一部が山札でも、掘れる確率が高ければ導入する
    core_pieces: tuple = (SAGA, "dm22ex1-025", DRAG, SHAKO)  # ループの最小部品

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
        here = set(hand) | set(grave) | set(names("bz")) | set(names("mana"))
        pieces_here = sum(1 for p in self.core_pieces if p in here)
        # マナに埋まった部品はループに使えないので、最小盤面はマナを除いて数える
        playable = set(hand) | set(grave) | set(names("bz"))
        pieces_playable = sum(1 for p in self.core_pieces if p in playable)
        grave_creatures = sum(1 for c in z["graveyard"][me]
                              if "creature" in eng.chars(c)["types"])
        return {
            "turn": eng.s.turn,
            "win_by": self.win_by,
            "deck": len(z["deck"][me]),
            "pieces_in_deck": pieces_in_deck,
            "dig_hit_prob": dig_prob(len(deck_names), pieces_in_deck),
            "hand_n": len(hand),
            "mana": len(z["mana"][me]),
            "dark_mana": dark_mana,
            "pieces_here": pieces_here,      # 最小部品のうち手元（手札・場・墓地・マナ）にある数
            "pieces_playable": pieces_playable,  # マナを除いた「使える場所」にある数
            "loop_board": pieces_playable >= len(self.core_pieces),  # ループの最小盤面に到達
            "grave_creatures": grave_creatures,
            "loop_ready": (pieces_playable >= len(self.core_pieces)
                           and grave_creatures >= 3),  # 到達＋墓地の前提まで満たした
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
            if f["loop_board"]:
                # 最小盤面に届いたら、変換（キルへの移行）に計算を寄せる
                return Intent("enter_loop", budget=4000, weights=sol.Weights(civ=10.0),
                              note="最小盤面に到達。変換に計算を寄せて導入する")
            return Intent("enter_loop", weights=sol.Weights(civ=10.0),
                          note="起点と墓地の準備と闇マナがある。導入して部品を集める")
        if f["bruce_route"] and f["dark_mana"] >= 1:
            # 起点が1枚しかなくても、掘る役の登場時効果で山札から起点や部品を探し、
            # 呪文面で墓地の起点を場に戻せる。墓地の準備が無くても導入に値する
            return Intent("enter_loop", weights=sol.Weights(civ=10.0),
                          note="ブルース経由: 掘る役で探し、呪文面で起点を戻して導入する")
        if (self.allow_dig_enter and f["pieces_here"] >= 2 and f["pieces_in_deck"] >= 1
                and f["dig_hit_prob"] >= 0.5 and f["dark_mana"] >= 1):
            # 部品が全部手元に無くても、残りが山札にあり掘れる確率が高いなら、
            # 整え続けるより導入しながら掘る方が勝ちに近い
            return Intent("enter_loop", budget=3000, weights=sol.Weights(civ=10.0),
                          note="部品の一部は山札にあるが当たる確率が高い。掘りながら導入する")
        # ループ以外の勝ち筋: 盤面で殴り切れるならそれが最速（ビートダウン）。
        # ただし抑制中は、殴りの勝ちに流れてループの手順が育たないため選ばない
        if not self.suppress_beatdown and f["my_threat"] >= f["opp_shield"] + 1:
            return Intent("execute", weights=sol.Weights(shield=200.0, threat=80.0, board=6.0),
                          note="盤面の打点でリーサルが見える。殴り切る")
        if not self.suppress_beatdown and f["my_threat"] >= 2:
            return Intent("beatdown", weights=sol.Weights(shield=200.0, threat=80.0, board=6.0),
                          note="ループの筋が無く盤面の圧力がある。シールドを削りに行く")
        if f["opp_threat"] >= 3 and f["opp_threat"] > f["my_threat"]:
            # コントロール: 相手の圧力が高い間は盤面を捌いてターンを稼ぎ、
            # 手札とマナを整えてコンボの確率を上げる
            return Intent("control", budget=800,
                          weights=sol.Weights(board=8.0, hand=6.0, shield=120.0, civ=10.0),
                          note="相手の圧力が高い。盤面を捌いてターンを稼ぐ")
        # 整える: 山札は「尽きて負ける」時だけ悪いので、守るのは残りわずかの時だけ。
        # 固定の厚さを基準にせず、山札切れの直前（deck_keep=2）まで削ることを許す。
        # 置換勝利では、勝敗に直結しない資源ループの自動反復だけは止める。
        if self.win_by == "effect":
            w, burn = sol.Weights(stock_cap=0, deck_keep=2, civ=20.0), False
            note = "部品か前提が不足。山札切れの直前だけ守って整える"
        elif self.win_by == "resource":
            w, burn = sol.Weights(stock_cap=4, deck_keep=2, civ=20.0), True
            note = "部品か前提が不足。資源を貯めながら整える"
        else:
            w, burn = sol.Weights(stock_cap=8, deck_keep=2, civ=20.0), True
            note = "部品か前提が不足。自分の山札の消耗は許して整える"
        return Intent("setup", budget=600, burn_stock=burn, weights=w, note=note)


def try_loop_first(eng, me: int = ME, discover_budget: int = 2000,
                   seek_budget: int = 2000):
    """そのターンに検証済みループで勝てるなら、勝った局面を返す。無ければ None。

    最小盤面に届いたターンでは、通常の探索は攻撃の勝ち（同じく勝ちで、より浅い）
    に流れがちなので、ループの手順（発見→早送り→仕上げ）を先に試す。
    """
    for f in discover_loops(eng, me, discover_budget):
        if not f.verified:
            continue
        for n in cycle_counts(f.cert, len(f.start.zlist("deck", me))):
            e = f.start.clone()
            try:
                fast_forward(e, f.cert, n)
            except Exception:
                continue
            ts = sol.TurnSearch(me, seek_budget)
            ts.burn_stock = False
            leaf, _ = ts.run(e)
            r = leaf.s.result
            if r is not None and r["winner"] == me:
                return leaf
    return None


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


# マナチャージで温存するカード（目標ループの部品）。MacroPlanner の既定と揃える
TARGET_CARDS = (SAGA, DRAG, IWA, SHAKO, "dm22ex1-025", "dmbd17-009")


def charge_scores(eng, d, targets=TARGET_CARDS, loop_card: str = SAGA) -> dict[int, float]:
    """マナチャージの判断: 選択肢ごとに「置く向き」のスコアを付ける。

    考え方は「手札で失う価値が小さく、マナとして困らない札から置く」。
    固定の枚数条件は置かず、すべて位置に応じた連続的な損得で比べる。
    - 目標の部品は温存する（同名が2枚以上ある場合だけ置く候補に戻す）
    - 既にマナにある文明しか持たない札は、新しい文明が増えないので置きやすい
    - 直近2ターンで使えないコストの札は、当面の手札価値が低い
    - 逆に、マナに無い文明を持ち、手札の他の札が必要としているなら、
      補完として置く価値がある（その文明が使えるようになる）
    - 多色は「手札でプレイする価値」と「マナとしての柔軟さ」の両方がある。
      手札に多色が多いほど1枚置く痛みは相対的に小さくなり、逆に近く
      プレイできる多色があるなら単色側を置いて残す動きも取れる。
      置きたい単色のプレイを残すために多色を置く動きも同様にあり得る。
      最終的な釣り合いは、勝ち筋から収穫した選好の学習に委ねる
    """
    me = d["player"]
    z = eng.s.zones
    mana_civs = set()
    for c in z["mana"][me]:
        mana_civs.update(eng.cdef(c).civs)
    mana_n = len(z["mana"][me])
    hand_ids = list(z["hand"][me])
    hand_names = [eng.s.cards[c].defn for c in hand_ids]
    # 手札が必要とする文明（近く使える札の文明）と、このターン使えるようになる札
    needs = set()
    fix_civs = set()    # 1枚置けばこのターン出せる札が必要とする文明
    multi_in_hand = 0   # 手札の多色の枚数（置く痛みの相対的な物差し）
    playable_multi = False  # 近くプレイできる多色があるか（残す価値がある）
    keep_mono = False       # 近くプレイしたい単色があるか（残すために多色を置く動き）
    for c in hand_ids:
        cd = eng.cdef(c)
        cost = min([f.cost for f in cd.faces] or [cd.cost])
        if cost <= mana_n + 2:
            needs.update(cd.civs)
            if len(cd.civs) >= 2:
                playable_multi = True
            else:
                keep_mono = True
        if cost == mana_n + 1:
            fix_civs.update(cd.civs)
        if len(cd.civs) >= 2:
            multi_in_hand += 1
    scores: dict[int, float] = {}
    for j, o in enumerate(d["options"]):
        if not o["key"].startswith("charge:") or o.get("cid") is None:
            continue
        cd = eng.cdef(o["cid"])
        name = eng.s.cards[o["cid"]].defn
        civs = set(cd.civs)
        cost = min([f.cost for f in cd.faces] or [cd.cost])
        s = 0.0
        if name in targets:
            # 部品は「干渉できるゾーン（手札・場・墓地）」に残す。マナは戻せない。
            # 置いた後に干渉できる同名が、メインパーツは2枚、その他は1枚を
            # 切るようなら置かない
            accessible = sum(1 for zone in ("hand", "bz", "graveyard")
                             for c in z[zone][me] if eng.s.cards[c].defn == name)
            need = 2 if name == loop_card else 1
            if accessible - 1 < need:
                s -= 100.0
        new_civs = civs - mana_civs
        if not new_civs:
            s += 30.0                       # 新しい文明が増えない札は置きやすい
        elif new_civs & needs:
            s += 20.0                       # 足りない文明の補完になる
            target_civs = set()
            for c in hand_ids:
                if eng.s.cards[c].defn in targets:
                    target_civs.update(eng.cdef(c).civs)
            if new_civs & target_civs:
                s += 10.0                   # 部品が使えるようになる文明は特に欲しい
            if new_civs & fix_civs:
                s += 15.0                   # この1枚でこのターン出せる札が増える
        if len(civs) >= 2:
            s += 4.0 * multi_in_hand       # 多色が多いほど1枚置く痛みは相対的に小さい
            if keep_mono:
                s += 6.0                    # 残したい単色のプレイのために多色を置く動き
        elif playable_multi:
            s += 10.0                       # 多色をプレイする方針なら単色側を置く
                                            # （単色のドローを期待して多色を温存する）
        if cost > mana_n + 2:
            s += 15.0                       # 直近では使えない
        elif cost <= mana_n:
            s -= 10.0                       # すぐ使える札は手札に残す
        scores[j] = s
    return scores


def charge_choice(eng, d, targets=TARGET_CARDS, loop_card: str = SAGA) -> int | None:
    """チャージすべき選択肢の添字（pass は選ばない）。判断が付かなければ None。"""
    scores = charge_scores(eng, d, targets, loop_card)
    if not scores:
        return None
    return max(scores, key=lambda j: scores[j])


def learn_play_shaping(records: list[dict], win_reason: str | None = None) -> dict[str, float]:
    """報酬の自動設計: 成功した対戦（到達/勝利した軌跡）の中で、どのカードの
    プレイがどれだけの割合の対戦に現れたかから、プレイへの報酬を決める。

    人手で「必要なプレイ」を列挙する代わりに、成功軌跡への出現率を使う。
    戻り値は最大値を1にそろえた {カードID: 報酬}。対戦の区切り（game）が
    無いレコードだけなら空を返す。

    win_reason を指定すると、その勝ち方で勝った対戦だけから学ぶ。到達した
    対戦の多くは別の勝ち方（攻撃）で終わるため、混ぜて学ぶと狙う勝ち方と
    無関係なプレイ（例: 打点として出したカード）まで報酬に入ってしまう。
    """
    games: dict = defaultdict(set)
    game_result: dict = {}
    for rec in records:
        g = rec.get("game")
        if g is None:
            continue
        game_result[g] = rec.get("result")
        for k in rec["chosen"]:
            if k.startswith("play:"):
                games[g].add(k.split(":")[1])
    if win_reason is not None:
        games = {g: p for g, p in games.items() if game_result.get(g) == win_reason}
    if not games:
        return {}
    n = len(games)
    counts: Counter = Counter()
    for played in games.values():
        for defn in played:
            counts[defn] += 1
    top = max(counts.values())
    return {defn: round(c / top, 3) for defn, c in counts.items() if c >= 2}


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
    targets: tuple = TARGET_CARDS   # マナチャージで温存する部品
    restrain_attack: bool = False   # 攻撃を候補の後ろに回す（禁止はしない。
                                    # ドラゲリオンの攻撃時効果など、計画に必要な攻撃は残す）
    loop_priority: bool = False     # 最小盤面に届くまでは攻撃せず、ループの成立を優先する
    core_pieces: tuple = (SAGA, "dm22ex1-025", DRAG, SHAKO)  # ループの最小部品
    loop_card: str = SAGA           # 起点（チャージで特に守るメインパーツ）
    plan_plays: tuple = TARGET_CARDS + ("dm26ex2-071", "dmpromoy22-p51", "dmex10-020")
    # 戦略に必要なプレイ: 部品、掘る呪文（タイフーン系）、マナ加速（コダマダンス）。
    # これ以外のプレイは、成立優先の間は候補の後ろに回す（微小なペナルティ）
    play_shaping: dict = field(default_factory=dict)
    # 成功軌跡から学んだプレイへの報酬（learn_play_shaping の出力）。
    # あれば人手の plan_plays より優先し、寄与するプレイを候補の前に、
    # 寄与しないプレイを後ろに回す

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

    def board_reached(self, eng, me: int) -> bool:
        """ループの最小部品が「使える場所」（手札・場・墓地）に揃っているか。

        マナに埋まった部品はループに使えないため数えない。
        """
        z = eng.s.zones
        here = set()
        for zone in ("hand", "bz", "graveyard"):
            here.update(eng.s.cards[c].defn for c in z[zone][me])
        return all(p in here for p in self.core_pieces)

    def loop_ready(self, eng, me: int) -> bool:
        """到達の条件: 部品が揃い、墓地の前提（クリーチャー3枚）も満たして、
        ループが回り始められる状態か。"""
        if not self.board_reached(eng, me):
            return False
        grave_creatures = sum(1 for c in eng.s.zones["graveyard"][me]
                              if "creature" in eng.chars(c)["types"])
        return grave_creatures >= 3

    def candidates(self, eng, d, w, cap: int = 6):
        """solitaire.candidates と同じ形。方策の答えを候補の先頭に置く。"""
        if (self.loop_priority and d["kind"] == "attack" and eng is not None
                and self.intent != "execute"
                and not self.loop_ready(eng, d["player"])):
            # ループの成立を優先する間は殴らない。回り始められる状態になった後と
            # キルの狙いのターンでは、攻撃時効果やリーサルのために攻撃を残す
            keys = [o["key"] for o in d["options"]]
            if "pass" in keys:
                return [[keys.index("pass")]]
        out = _base_candidates(eng, d, w, cap)
        if (self.intent == "enter_loop" and d["kind"] == "choose_cards"
                and eng is not None):
            # 墓地の準備: ループの前提（墓地のクリーチャー3枚）に届いていない間は、
            # 捨てる選択ではクリーチャーを優先して墓地に送る
            me = d["player"]
            grave_creatures = sum(1 for c in eng.s.zones["graveyard"][me]
                                  if "creature" in eng.chars(c)["types"])
            if grave_creatures < 3:
                def picks_creature(cand):
                    if not cand:
                        return False
                    cid = d["options"][cand[0]].get("cid")
                    return cid is not None and "creature" in eng.chars(cid)["types"]
                out = sorted(out, key=lambda c: 0 if picks_creature(c) else 1)
                return [list(c) for c in out]
        if self.restrain_attack and d["kind"] == "attack":
            # 大局観レベルの抑制: むやみに殴らない方針として pass を先に置く。
            # 攻撃の候補自体は残すので、リーサルや攻撃時効果（メテオバーン等）が
            # 必要な筋は探索が拾える
            keys = [o["key"] for o in d["options"]]
            if "pass" in keys:
                p = [keys.index("pass")]
                out = [p] + [c for c in out if list(c) != p]
            return out
        pref = self.prefer(eng, d)
        if d["kind"] == "charge" and eng is not None:
            # マナチャージは学習選好より先に、文明と使用見込みの判断で並べる
            j = charge_choice(eng, d, self.targets, self.loop_card)
            if j is not None:
                pref = [j]
        if pref is None:
            res = out
        else:
            rest = [c for c in out if list(c) != pref]
            res = [pref] + rest[: max(cap - 1, 0)]
        if (self.loop_priority and d["kind"] == "main" and self.intent != "execute"):
            # 戦略に不要なプレイへの微小なペナルティと、寄与するプレイへの
            # 微小な報酬: 部品集めの挙動は妨げず、それ以外のプレイ
            # （余分なクリーチャー等）を候補の後ろに回す。場に残った余分な
            # 打点が、後のターンに攻撃の勝ち筋を作ってしまうため。
            # 報酬表（play_shaping）があれば人手の列挙より優先する
            keys = [o["key"] for o in d["options"]]

            def tier(cand):
                if not cand:
                    return 1
                k = keys[cand[0]]
                if not k.startswith("play:"):
                    return 1                    # pass などは真ん中
                defn = k.split(":")[1]
                if self.play_shaping:
                    return 0 if self.play_shaping.get(defn, 0.0) >= 0.5 else 2
                return 0 if defn in self.plan_plays else 2
            res = sorted(res, key=tier)
        return res


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
                    mana_civs = {c for cid in eng.s.zones["mana"][ME]
                                 for c in eng.cdef(cid).civs}
                    multi_hand = sum(1 for cid in eng.s.zones["hand"][ME]
                                     if len(eng.cdef(cid).civs) >= 2)
                    records.append({"kind": d["kind"],
                                    "options": [o["key"] for o in d["options"]],
                                    "chosen": entry["keys"],
                                    "deck": deck_n, "bucket": deck_bucket(deck_n),
                                    "win_by": self.win_by, "intent": intent_name,
                                    "grave": grave_bucket(eng, ME),
                                    "mana_civs": len(mana_civs),   # チャージ判断の学習用文脈
                                    "multi_hand": multi_hand})
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

    def harvest_games(self, deck: list, opp_deck: list, seeds: list[int],
                      micro: MicroPolicy, macro: MacroPlanner, horizon: int = 10):
        """通し対戦から判断を収穫する（序盤〜中盤の文脈を埋めるため）。

        階層版で対戦し、「最小盤面に到達した対戦」と「ループで勝った対戦」の
        判断だけを、対戦を再生しながら記録する。狙いはターンごとに付け直す。
        戻り値: (対象になった対戦数, レコード)。
        """
        kept, records = 0, []
        for s in seeds:
            eng = Engine.new_game(self.rules, [deck, opp_deck], s, 0)
            start_ot = sol.own_turn(eng, ME)
            reached = False
            leaf = eng
            while True:
                d = eng.advance()
                if d is None or eng.s.result:
                    leaf = eng
                    break
                if eng.s.active != ME or d["player"] != ME:
                    eng.answer(sol.charge_only_policy(eng, d))
                    continue
                if sol.own_turn(eng, ME) > start_ot + horizon - 1:
                    leaf = eng
                    break
                if macro.features(eng)["loop_board"]:
                    reached = True
                intent = macro.plan(eng)
                micro.intent = intent.name
                ts = sol.TurnSearch(ME, intent.budget, intent.weights)
                ts.burn_stock = intent.burn_stock
                ts.stock_offsets = tuple(intent.stock_offsets)
                old = sol.candidates
                sol.candidates = micro.candidates
                try:
                    eng, _ = ts.run(eng)
                finally:
                    sol.candidates = old
                    micro.intent = None
                leaf = eng
            r = leaf.s.result
            won_loop = bool(r and r.get("winner") == ME and r.get("reason") == "effect")
            result_reason = r.get("reason") if (r and r.get("winner") == ME) else None
            if not (reached or won_loop):
                continue
            # 再生して判断を記録する
            eng = Engine.new_game(self.rules, [deck, opp_deck], s, 0)
            log = leaf.log
            i, ok = 0, True
            intent_name = "setup"
            while True:
                d = eng.advance()
                if d is None or eng.s.result:
                    break
                if i >= len(log):
                    ok = False
                    break
                entry = log[i]
                i += 1
                if d["player"] == ME and eng.s.active == ME:
                    intent_name = macro.plan(eng).name
                if d["player"] == ME:
                    deck_n = len(eng.s.zones["deck"][ME])
                    mana_civs = {c for cid in eng.s.zones["mana"][ME]
                                 for c in eng.cdef(cid).civs}
                    multi_hand = sum(1 for cid in eng.s.zones["hand"][ME]
                                     if len(eng.cdef(cid).civs) >= 2)
                    records.append({"kind": d["kind"], "game": s, "result": result_reason,
                                    "options": [o["key"] for o in d["options"]],
                                    "chosen": entry["keys"],
                                    "deck": deck_n, "bucket": deck_bucket(deck_n),
                                    "win_by": self.win_by, "intent": intent_name,
                                    "grave": grave_bucket(eng, ME),
                                    "mana_civs": len(mana_civs),
                                    "multi_hand": multi_hand})
                try:
                    # キーでは同名の選択肢（シールドなど）を区別できないため、
                    # ログに残っている選択肢の番号で再生する
                    if entry.get("choice") is not None:
                        eng.answer(entry["choice"])
                    else:
                        eng.answer_by_keys(entry["keys"])
                except Exception:
                    ok = False
                    break
            if ok:
                kept += 1
        return kept, records

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
