import random
from dmsim.autofix import partdiscovery as PD
from dmsim.autofix.tune import evolve
from dmsim.search.leaf_parts import Part, PartsSpec

SPEC = PartsSpec(parts=(Part("graveyard", ("A",), 1, 2.0), Part("hand", ("B",), 1, 2.0)))


def mk(n=12):
    """勝ち局は手札に X がある。B は勝敗と無関係。"""
    kill, final = [], []
    for i in range(n):
        win = i % 2 == 0
        kill.append(3 if win else None)
        final.append({"hand": {"X": 1, "B": 1} if win else {"B": 1}, "graveyard": {"A": 1}})
    return {"kill": kill, "final": final}


def test_discover_add_and_drop():
    c = PD.discover(mk(), SPEC)
    assert any(x["op"] == "add" and x["id"] == "X" and x["zone"] == "hand" for x in c)
    assert not any(x["op"] == "add" and x["id"] in ("A", "B") for x in c)        # 既存の部品は足さない
    assert any(x["op"] == "drop" and x["key"] == "graveyard:A" for x in c)      # 勝敗と無関係(差0)の部品は外す候補


def test_too_few_games_no_candidates():
    assert PD.discover({"kill": [3, None], "final": [{}, {}]}, SPEC) == []


def test_apply_and_store_roundtrip():
    c = PD.discover(mk(), SPEC)
    g = frozenset(range(len(c)))
    s2 = PD.apply_edits(SPEC, c, g)
    assert ("hand", ("X",)) in [(p.zone, p.ids) for p in s2.parts] and all(p.ids != ("A",) for p in s2.parts)
    assert PD.apply_store(SPEC, PD.to_store(c, g)).parts == s2.parts


def test_evolve_picks_useful_edit():
    c = [{"op": "add", "zone": "hand", "id": "X"}, {"op": "add", "zone": "hand", "id": "Z"}]

    def fake(g, seeds):
        good = 0 in g
        return {"kill": [(2 if good else 4) + round(((s * 7919) % 13) / 13) for s in seeds]}
    g, h = evolve(fake, frozenset(), lambda x, r: PD.mutate_genes(x, r, 2), lambda x: {"g": sorted(x)},
                  list(range(40)), list(range(100, 140)), generations=6, lam=4)
    assert 0 in g


def test_fallback_by_opp_shield_when_no_wins():
    m = mk()
    m["kill"] = [None] * 12
    m["opp_shield"] = [1 if i % 2 == 0 else 5 for i in range(12)]
    assert any(x["op"] == "add" and x["id"] == "X" for x in PD.discover(m, SPEC))
