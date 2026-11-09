import random
from dmsim.autofix import partsgenome as PG
from dmsim.autofix.tune import evolve
from dmsim.search.leaf_parts import load_specs


def test_apply_and_mutate():
    spec = next(iter(load_specs().values()))
    g = PG.neutral(spec)
    assert PG.apply(spec, g) == spec
    assert PG.apply(spec, (1.0,)) in (spec,) or len(spec.parts) == 1       # 長さ違いは無視
    rng = random.Random(0)
    for _ in range(100):
        g = PG.mutate(g, rng)
        assert all(PG.LO <= x <= PG.HI for x in g)
    w = PG.apply(spec, (2.0,) * len(spec.parts))
    assert all(a.weight == b.weight * 2 for a, b in zip(w.parts, spec.parts))


def test_evolve_generic_vector():
    def fake(g, seeds):
        q = abs(g[0] - 2.0)
        return {"kill": [2 + round(q * 2 + ((s * 7919) % 13) / 13 * 0.6) for s in seeds]}
    g, h = evolve(fake, (1.0, 1.0), PG.mutate, lambda x: {"m": list(x)}, list(range(60)), list(range(100, 160)), generations=10, lam=6)
    assert abs(g[0] - 2.0) <= 1.0 and any(e["verdict"] == "accept" for e in h)
