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
