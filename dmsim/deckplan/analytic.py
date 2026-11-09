"""デッキ構成の解析的な見積もり（エンジンを回さない）。cards 段階（必要カードが見えるゾーンにそろう）の到達率を、
山札をシャッフルして先頭 n 枚（初期手札5＋その時点までのドロー）に必要カードがそろう確率で近似する。
同じ乱数（置換）を全デッキで使い回すので、デッキ間の差は対比較として安定する。数ミリ秒で数千候補を並べられる。"""
from __future__ import annotations

import random
from collections import Counter

TRIALS = 4000
N_CARDS = 9           # 4ターン時点で見える枚数の目安（初期手札5＋後攻なら4ドロー。先攻は8）


def _perms(size: int, n: int, trials: int, seed: int) -> list[list[int]]:
    rng = random.Random(seed)
    base = list(range(size))
    out = []
    for _ in range(trials):
        rng.shuffle(base)
        out.append(base[:n])
    return out


def p_cards(deck: list[str], need: dict, n: int = N_CARDS, trials: int = TRIALS, seed: int = 0) -> float:
    """山札の先頭 n 枚に need（{id: 必要枚数}）が全部そろう確率。need が空なら 0。"""
    if not need:
        return 0.0
    perms = _perms(len(deck), min(n, len(deck)), trials, seed)       # 同じ size・seed なら同じ置換（CRN）
    hit = 0
    for pos in perms:
        have = Counter(deck[i] for i in pos)
        if all(have[k] >= v for k, v in need.items()):
            hit += 1
    return hit / trials
