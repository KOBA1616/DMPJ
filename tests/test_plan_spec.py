import pytest

from dmsim.discovery.loopspec import LoopSpec, Pred, Route
from dmsim.plan import PlanSpec, from_loopspec, register_role, to_loopspec


def _ls():
    return LoopSpec(name="t", kind="reroll", minimal=[Pred(0, {"name": "x"}, zone="battle")],
                    goal=[Pred(0, {"types": ["spell"]}, zones=("hand", "grave"))], hazards=["attack"],
                    routes=[Route("cast", {"name": "x"}, cost=3, civs=("water",))], limit=5, source={"seed": 1})


def test_loopspec_roundtrip():
    ls = _ls()
    ps = from_loopspec(ls)
    assert to_loopspec(PlanSpec.from_json(ps.to_json())).to_json() == ls.to_json()


def test_plan_id_ignores_source_and_order():
    a = from_loopspec(_ls())
    b = from_loopspec(_ls())
    b.source = {"seed": 99}
    assert a.plan_id == b.plan_id


def test_unknown_fields_preserved():
    d = from_loopspec(_ls()).to_dict()
    d["future_field"] = {"a": 1}
    assert PlanSpec.from_dict(d).to_dict()["extra"] == {"future_field": {"a": 1}}


def test_registration_checks():
    with pytest.raises(ValueError):
        PlanSpec(kind="nope")
    with pytest.raises(ValueError):
        PlanSpec(kind="loop", roles=("nope",))
    with pytest.raises(ValueError):
        register_role("x", progress="", compare="c", test="t")
    with pytest.raises(ValueError):
        PlanSpec.from_dict({"kind": "loop", "schema_version": 9})


def test_plan_id_set_semantics_and_stability():
    a = from_loopspec(_ls())
    b = from_loopspec(_ls())
    b.hazards = list(reversed(b.hazards))
    b.goal[0] = Pred(0, {"types": ["spell"]}, zones=("grave", "hand"))
    assert a.plan_id == b.plan_id
    assert len(a.plan_id) == 16
    c = from_loopspec(_ls())
    c.params["limit"] = 6
    assert a.plan_id != c.plan_id


def test_v0_migration_and_canonical_json():
    from dmsim.plan import SCHEMA_VERSION
    d = from_loopspec(_ls()).to_dict()
    d["schema_version"] = 0
    ps = PlanSpec.from_dict(d)
    assert ps.schema_version == SCHEMA_VERSION
    j = ps.to_json()
    assert PlanSpec.from_json(j).to_json() == j


def test_jsonl_roundtrip_and_validation(tmp_path):
    from dmsim.plan import dump_jsonl, load_jsonl
    ps = [from_loopspec(_ls())]
    f = tmp_path / "p.jsonl"
    dump_jsonl(ps, f)
    assert [p.plan_id for p in load_jsonl(f)] == [p.plan_id for p in ps]
    with pytest.raises(ValueError):
        PlanSpec(kind="loop", minimal=[Pred(0, {}, op="~")])
