"""組の寄与（取り除き試験、docs/combo-ruler-design.md §27、2026-11-14）。

組あり（with）と、組をつなぎ札に置き換えた対照（without）を同じシードの対で測り、差を組の値とする。
型（ループ型・リソース型・攻撃型）によらない共通の形: 1局ごとの数値（0/1 の勝ち、リソースの差、段の到達など）を
シードの対で並べて渡すだけ。値は順位づけに使い、足切りはしない。
"""
from __future__ import annotations

import math
from collections import Counter


def remove_pair(deck: list[str], pair, fill: str | None = None) -> list[str]:
    """組の札をつなぎ札に置き換えたデッキ。fill を省くとデッキで最も多い組以外の札。"""
    pair = set(pair)
    if fill is None:
        fill = next((x for x, _ in Counter(deck).most_common() if x not in pair), None)
    if fill is None:
        raise ValueError("置き換えるつなぎ札がない")
    return [fill if x in pair else x for x in deck]


def paired(with_vals: dict, without_vals: dict) -> dict:
    """シード -> 値 の2つの表から、共通のシードで差を取る。
    戻り値: n, mean_with, mean_without, diff（平均の差）, sd（対の差の標準偏差）, ci95（正規近似）,
    better / worse / tie（組ありが上回った・下回った・同じ対の数）。"""
    seeds = sorted(set(with_vals) & set(without_vals), key=str)
    d = [float(with_vals[s]) - float(without_vals[s]) for s in seeds]
    n = len(d)
    if n == 0:
        return {"n": 0, "mean_with": None, "mean_without": None, "diff": None, "sd": None, "ci95": None,
                "better": 0, "worse": 0, "tie": 0}
    m = sum(d) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in d) / (n - 1)) if n > 1 else 0.0
    h = 1.96 * sd / math.sqrt(n)
    return {"n": n, "mean_with": round(sum(float(with_vals[s]) for s in seeds) / n, 4),
            "mean_without": round(sum(float(without_vals[s]) for s in seeds) / n, 4),
            "diff": round(m, 4), "sd": round(sd, 4), "ci95": (round(m - h, 4), round(m + h, 4)),
            "better": sum(1 for x in d if x > 0), "worse": sum(1 for x in d if x < 0), "tie": sum(1 for x in d if x == 0)}


def by_seed(rows, value) -> dict:
    """1局の行のリストから シード -> value(行) の表。"""
    return {r["seed"]: value(r) for r in rows}
