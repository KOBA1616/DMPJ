"""ブートストラップ信頼区間と同一シードの対比較（固定の改善幅は置かない）。"""
from __future__ import annotations

import random


def boot_ci(xs: list[float], n_boot: int = 2000, alpha: float = 0.05, seed: int = 0) -> tuple[float, float, float]:
    """平均と (1-alpha) の百分位ブートストラップ区間。"""
    if not xs:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)
    n = len(xs)
    means = sorted(sum(xs[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    return sum(xs) / n, means[int(n_boot * alpha / 2)], means[min(n_boot - 1, int(n_boot * (1 - alpha / 2)))]


def paired_diff(a: list[float], b: list[float], n_boot: int = 2000, alpha: float = 0.05, seed: int = 0) -> dict:
    """同一シードの対 (a_i, b_i) の差 a-b。区間が0を含まなければ有意。効果量(d)も併記。"""
    if len(a) != len(b):
        raise ValueError("対比較は同じシード集合で行う（長さ不一致）")
    d = [x - y for x, y in zip(a, b)]
    mean, lo, hi = boot_ci(d, n_boot, alpha, seed)
    n = len(d)
    sd = (sum((x - mean) ** 2 for x in d) / (n - 1)) ** 0.5 if n > 1 else 0.0
    return {"n": n, "diff": mean, "ci": [lo, hi], "significant": not (lo <= 0.0 <= hi),
            "effect_size": (mean / sd) if sd > 0 else 0.0}
