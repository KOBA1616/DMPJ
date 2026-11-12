"""局面精度: ターン終了時の局面（探索の葉）の評価 evaluate とその重み Weights（S3、P0-3 で solitaire.py から分割）。"""
from __future__ import annotations

from dataclasses import dataclass

from ..engine import Engine

WIN = 1e9


@dataclass
class Weights:
    """ターン終了時の局面の評価の重み。キル率を見ながら調整する前提の素朴な値。"""
    shield: float = 100.0       # 相手のシールド1枚につき減点
    threat: float = 40.0        # 次のターンに攻撃できる打点（ブレイク数、シールド+1 まで）
    mana: float = 10.0
    hand: float = 4.0
    board: float = 2.0
    opp_deck: float = 3.0       # 相手の山札を削った枚数
    deck_danger: float = 60.0   # 自分の山札が少ない時の減点（自分の山札切れ対策）
    max_mana: int = 8           # これ以上はチャージしない（貪欲方策）
    stock_cap: int = 8          # 相手に効かない資源ループ（ドロー等）を1度にストックする最大周回数
    deck_keep: int = 8          # 資源ループでも自分の山札はこの枚数より減らさない
    goal_card: float = 200.0    # 自分の場に常在の勝利条件（kind: state）を持つカードがある
    goal_dist: float = 40.0     # その条件（「N枚以上」）まで足りない枚数1つにつき減点
    lookahead: int = 0          # 1以上なら、各決定の候補をその先 N 手の貪欲な評価で並べ替える（0 は従来どおり）



def goal_distance(eng: Engine, me: int) -> tuple[int, int]:
    """(場にある常在の勝利条件を持つカードの数, その条件「数 >= N」まで足りない枚数の最小)。条件が数の比較でなければ距離は見ない。"""
    n_cards, best = 0, None
    for c in eng.bz_tops(me):
        if eng.s.cards[c].controller != me:
            continue
        for _, ab in eng.abilities(c, "state"):
            if any(o.get("op") == "win" and o.get("player", "you") == "you" for o in ab["effect"]):
                n_cards += 1
                cm = ab["if"].get("cmp")
                if cm and cm[1] == ">=" and isinstance(cm[2], int) and isinstance(cm[0], dict) and "count" in cm[0]:
                    env = {"you": me, "self": eng.s.ref(c)}
                    gap = max(0, cm[2] - eng.eval_expr(cm[0], env))
                    best = gap if best is None else min(best, gap)
    return n_cards, (best if best is not None else 0)


def evaluate(eng: Engine, me: int, w: Weights) -> float:
    s = eng.s
    opp = 1 - me
    if s.result is not None:
        if s.result["winner"] == me:
            return WIN - s.result["turn"]
        if s.result["winner"] == opp:
            return -WIN
        return -WIN / 2
    sh = len(eng.zlist("shield", opp))
    breaks = 0
    mine = eng.bz_tops(me)
    for c in mine:
        ch = eng.chars(c)
        if "creature" in ch["types"]:
            breaks += ch["breaks"]
    deck = len(eng.zlist("deck", me))
    self_keep = w.deck_keep
    gc, gd = goal_distance(eng, me)
    return (w.goal_card * gc - w.goal_dist * gd - w.shield * sh + w.threat * min(breaks, sh + 1) + w.mana * len(eng.zlist("mana", me))
            + w.hand * len(eng.zlist("hand", me)) + w.board * len(mine)
            + w.opp_deck * (40 - len(eng.zlist("deck", opp)))
            - w.deck_danger * max(0, self_keep - deck))


