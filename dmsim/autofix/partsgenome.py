"""評価式（部品表の重み）の進化。遺伝子=部品ごとの重み倍率のタプル（1.0 が既定、0.25〜4）。
ノブ(coef/gy_mult)は全体の倍率だが、こちらは部品1つずつの重みを動かすので「この札だけ軽く／重く」が表せる。
文法は固定（重みの倍率のみ）。式の形そのものを変える遺伝的プログラミングは未実装（効果が見えてから）。"""
from __future__ import annotations

import random
from dataclasses import replace

LO, HI = 0.25, 4.0


def neutral(spec) -> tuple[float, ...]:
    return (1.0,) * len(spec.parts)


def apply(spec, mults):
    """部品表に倍率を掛けた新しい PartsSpec（長さが違う＝部品表が変わった時は無視して元のまま）。"""
    if not mults or len(mults) != len(spec.parts):
        return spec
    return replace(spec, parts=tuple(replace(p, weight=p.weight * m) for p, m in zip(spec.parts, mults)))


def mutate(mults, rng: random.Random, n_change: int = 1) -> tuple[float, ...]:
    out = list(mults)
    for i in rng.sample(range(len(out)), min(n_change, len(out))):
        out[i] = round(min(HI, max(LO, out[i] * 2.0 ** rng.uniform(-1.0, 1.0))), 3)
    return tuple(out)


def load_specs_evolved(store_path: str = "data/autofix/parts.yaml") -> dict:
    """load_specs() に、進化で採用した重み倍率（store_path）を掛けたもの。無ければ素の部品表。"""
    from pathlib import Path

    import yaml

    from ..search.leaf_parts import load_specs
    specs = load_specs()
    p = Path(store_path)
    st = (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}
    from .partdiscovery import apply_store
    ed = {}
    q = Path(store_path).with_name("parts_edits.yaml")
    if q.exists():
        ed = yaml.safe_load(q.read_text(encoding="utf-8")) or {}
    # 追加・削除を先に反映（部品の並びが変わるので、重み倍率は編集後の長さと合う時だけ掛かる）
    return {k: apply(apply_store(v, ed.get(k)), tuple(st[k])) if k in st else apply_store(v, ed.get(k)) for k, v in specs.items()}
