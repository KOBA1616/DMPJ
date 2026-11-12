"""「必要カードが見える所にそろう」確率の素引き値（デッキだけで決まる。サーチ・ドロー効果は数えない）。LLM・探索なし、厳密計算。

日次診断が cards 段階で止まる原因の切り分け用。観測した到達率がこの値に近ければ（knight_dmc: 実測0.38 / 計算0.382）、AIではなくデッキの引き込みの問題
（deck_fix の領分）で、ノブや評価式をいくら動かしても上がらない。計算値より大きく低ければ探索側の問題。実測が計算値より高いのはサーチ・ドローの効果（saga: 0.23 / 0.076）。
前提: 山札は一様シャッフル（マリガンなし）。山札・盾以外は全部見えるゾーンなので、手札5枚＋ドロー分の無作為な部分集合に
必要枚数が入っていれば「そろった」。ドローは先攻が T-1 回、後攻が T 回（先攻1ターン目はドローしない）。"""
from __future__ import annotations

from collections import Counter
from math import comb


def reach_prob(deck: list[str], need: dict, n_seen: int) -> float:
    """deck から無作為に n_seen 枚見たとき、need={ID: 必要枚数} をすべて満たす確率。"""
    n = len(deck)
    if not need:
        return 0.0
    if n_seen > n:
        n_seen = n
    cnt = Counter(deck)
    poly = [1]                                  # 必要カードだけの枚数分布（係数=組合せ数）
    rest = n
    for i, k in need.items():
        c = cnt.get(i, 0)
        rest -= c
        if c < k:
            return 0.0
        p = [0] * (c + 1)
        for j in range(k, c + 1):
            p[j] = comb(c, j)
        new = [0] * (len(poly) + c)
        for a, x in enumerate(poly):
            if x:
                for b, y in enumerate(p):
                    if y:
                        new[a + b] += x * y
        poly = new
    tot = sum(x * comb(rest, n_seen - s) for s, x in enumerate(poly) if x and 0 <= n_seen - s <= rest)
    return tot / comb(n, n_seen)


def cards_ceiling(deck: list[str], need: dict, turn: int, hand: int = 5) -> float:
    """turn ターン目までに need がそろう確率の上限（先攻・後攻の平均。seed の偶奇で交互に決まるため）。"""
    on_play = reach_prob(deck, need, hand + max(0, turn - 1))
    on_draw = reach_prob(deck, need, hand + turn)
    return (on_play + on_draw) / 2
