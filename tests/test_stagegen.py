from dmsim.discovery.loopspec import LoopSpec
from dmsim.plan.macro import MacroPlanner
from dmsim.plan.stagegen import stages_from_leaf_parts, stages_from_loopspec


def test_loopspec_chain_is_cumulative_and_drops_deck():
    ls = LoopSpec.from_json(open("data/loops/tenmon_initial.json", encoding="utf-8").read())
    st = stages_from_loopspec(ls)
    assert st and all("deck" not in s["target"] for s in st)
    for a, b in zip(st, st[1:]):    # 累積: 前の段の条件は次の段にも含まれる
        assert all(b["target"].get(z, {}).get(i, 0) >= n for z, v in a["target"].items() for i, n in v.items())
    assert "shield" in st[-1]["target"] and "bz" in st[-1]["target"]


def test_leaf_parts_chain_for_saga():
    import yaml
    c = next(x for x in yaml.safe_load(open("data/known_combos/combos.yaml", encoding="utf-8"))["combos"] if x["id"] == "saga")
    st = stages_from_leaf_parts(c["leaf_parts"])
    assert len(st) >= 4 and st[0]["target"].get("hand")
    assert MacroPlanner([s["target"] for s in st]).stages


def test_akashic_stages_are_met_by_verified_min_board(monkeypatch):
    """アカシックの段階目標は、エンジンで検証済みの最小盤面（akashic_loop_min）で最終段まで満たされる。部品表が最小盤面からずれたら落ちる。"""
    import pytest
    import yaml
    from dmsim.defs import load_rules
    from dmsim.discovery.reachsearch import board_met
    from dmsim.scenario import build

    monkeypatch.delenv("DMSIM_SKIP_CONVERTED", raising=False)    # オルゼキア・NoN は converted.yaml にある
    rules = load_rules()
    if "dm23bd7-035" not in rules.cards:
        pytest.skip("converted cards not loaded")
    c = next(x for x in yaml.safe_load(open("data/known_combos/combos.yaml", encoding="utf-8"))["combos"] if x["id"] == "akashic")
    assert c["status"] == "verified"
    st = stages_from_leaf_parts(c["leaf_parts"])
    assert len(st) == 4
    spec = yaml.safe_load(open("tools/eval_specs/akashic_loop_min.yaml", encoding="utf-8"))
    e = build(rules, spec)
    assert board_met(e, 0, st[-1]["target"])
    assert yaml.safe_load(open("data/eval/stages/akashic.generated.yaml", encoding="utf-8"))["stages"] == st
