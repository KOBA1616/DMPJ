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
