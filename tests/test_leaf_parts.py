import yaml
from dmsim.engine import scenario
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


def test_finish_bundle_needs_all_items_and_is_off_by_default(rules):
    from dmsim.search.leaf_parts import DRAGELION, SHAKOGAIRU, load_specs
    spec = load_specs()["saga"]
    assert spec.finish and not spec.bundles
    on = spec.with_finish(1.0)
    full = _eng(rules, {"hand": [SAGA, DRAGELION], "graveyard": [SAGA, SHAKOGAIRU]})
    part = _eng(rules, {"hand": [SAGA, DRAGELION], "graveyard": [SAGA]})
    assert parts_score(full, 0, spec) == parts_score(full, 0, spec.with_finish(0.0))
    assert parts_score(full, 0, on) - parts_score(full, 0, spec) == on.coef * on.bundles[0].weight
    assert parts_score(part, 0, on) == parts_score(part, 0, spec)   # 1つ欠ければ加点しない


def test_parts_id_for_decks():
    from dmsim.search.leaf_parts import parts_id_for_decks
    assert parts_id_for_decks(["data/decks/saga_entry.yaml"], "auto") == "saga"
    assert parts_id_for_decks(["data/decks/saga_entry.yaml"], "none") is None
    assert parts_id_for_decks(["data/decks/saga_entry.yaml"], "knight_dmc") == "knight_dmc"
    assert parts_id_for_decks(None, "auto") is None and parts_id_for_decks(["a", "b"], "auto") is None


def test_auto_finish_for_combos_without_handwritten_bundles(rules):
    from dmsim.search.leaf_parts import AUTO_FINISH_MAX, auto_finish, load_specs
    specs = load_specs()
    assert all(s.finish for k, s in specs.items() if k in ("tenmon", "akashic", "knight_dmc"))
    assert specs["saga"].finish[0].items[0][0] == "hand"      # 手書きがあればそれを使う
    a = auto_finish({"parts": [{"id": f"x{i}", "role": "core"} for i in range(9)] + [{"id": "s", "role": "support"}]})
    assert len(a[0].items) == AUTO_FINISH_MAX and all(z == "hand|bz" for z, _, _ in a[0].items)
    assert auto_finish({"parts": [{"id": "x", "role": "core"}]}) == ()   # 1種だけなら束にならない


def test_auto_finish_bundle_scores_only_when_all_present(rules):
    from dmsim.search.leaf_parts import Bundle
    spec = PartsSpec((), finish=(Bundle((("hand|bz", "T001", 1), ("hand|bz", "T004", 1)), 5.0),)).with_finish()
    both = _eng(rules, {"hand": ["T001"], "bz": ["T004"]})
    one = _eng(rules, {"hand": ["T001"]})
    assert parts_score(both, 0, spec) == 5.0 and parts_score(one, 0, spec) == 0.0


def test_heavy_parts_are_derived_from_combo_definition():
    from dmsim.autofix.batch import default_need
    from dmsim.search.leaf_parts import HEAVY_CORE_DEFAULT, heavy_ids
    combos = {c["id"]: c for c in yaml.safe_load(open("data/known_combos/combos.yaml", encoding="utf-8"))["combos"]}
    # core が少ないコンボは全部、多いコンボは loopspec か先頭から絞る（天門の core 9種が全部 cards の必要カードにならない）
    assert len(heavy_ids(combos["knight_dmc"])) == 2
    ten = heavy_ids(combos["tenmon"])
    assert ten and len(ten) < 9 and "dmx12b-031" in ten
    aka = heavy_ids(combos["akashic"])
    from dmsim.search.leaf_parts import canon
    assert aka == [canon(p["id"]) for p in combos["akashic"]["parts"][:HEAVY_CORE_DEFAULT]]   # 収録IDの違うカードはエンジン側IDに読み替える
    for k in ("tenmon", "akashic", "knight_dmc"):
        need = default_need(combos[k])
        assert need and len(need) < len([p for p in combos[k]["parts"] if p.get("role") == "core"]) or k == "knight_dmc"
    assert set(default_need(combos["saga"]))    # 手書きのコンボは従来どおり
