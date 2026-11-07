from dmsim import scenario
from dmsim.search import FairTurnSearch
from dmsim.search.leaf_parts import SAGA, SAGA_SPEC, Part, PartsSpec, make_value_fn, parts_score


def _eng(rules, p0):
    e = scenario.build(rules, {"p0": p0, "p1": {}, "filler": "T001", "seed": 1, "deck_size": 20, "deck_left": None})
    assert e.advance() is not None
    return e


def test_saga_in_graveyard_scores_above_hand(rules):
    hand = _eng(rules, {"hand": [SAGA, "T001"], "mana": ["T004"] * 4})
    grave = _eng(rules, {"hand": ["T001"], "graveyard": [SAGA], "mana": ["T004"] * 4})
    assert parts_score(grave, 0, SAGA_SPEC) > parts_score(hand, 0, SAGA_SPEC) > 0


def test_creature_count_capped_by_need(rules):
    spec = PartsSpec((Part("graveyard", (), 2, 1.0),))
    two = _eng(rules, {"hand": ["T001"], "graveyard": ["T001"] * 2})
    four = _eng(rules, {"hand": ["T001"], "graveyard": ["T001"] * 4})
    assert parts_score(two, 0, spec) == parts_score(four, 0, spec) == 2.0


def test_value_fn_reaches_search(rules):
    calls = []
    inner = make_value_fn(SAGA_SPEC)

    def vf(eng, me):
        calls.append(1)
        return inner(eng, me)
    e = _eng(rules, {"hand": ["T001", "T073"], "mana": ["T004"] * 4})
    FairTurnSearch(0, budget=20, n_det=2, seed=1, value_fn=vf).run(e)
    assert calls


def test_saga_spec_comes_from_known_combos():
    from dmsim.search.leaf_parts import DRAGELION, SHAKOGAIRU, load_specs
    assert SAGA_SPEC.coef == 10.0
    assert any(p.zone == "graveyard" and p.ids == (SHAKOGAIRU,) for p in SAGA_SPEC.parts)
    assert any(p.zone == "hand" and p.ids == (DRAGELION,) for p in SAGA_SPEC.parts)
    assert set(load_specs()) >= {"saga", "tenmon", "knight_dmc", "akashic"}


def test_default_spec_from_core_parts(rules):
    from dmsim.search.leaf_parts import spec_from_combo
    combo = {"id": "x", "parts": [{"id": "T001", "name": "a", "role": "core"}, {"id": "T073", "name": "b", "role": "support"},
                                  {"name": "id無し", "role": "core"}]}
    spec = spec_from_combo(combo)               # leaf_parts なし → id のある core 部品だけから導出
    assert {i for p in spec.parts for i in p.ids} == {"T001"}
    held = _eng(rules, {"hand": ["T001", "T073"]})
    none = _eng(rules, {"hand": ["T073", "T073"]})
    assert parts_score(held, 0, spec) > parts_score(none, 0, spec) == 0


def test_holdout_split_is_selectable():
    from dmsim.search.leaf_parts import load_specs
    assert "drill_lock" not in load_specs(split="tuning")
    assert "drill_lock" in load_specs(split="holdout")
