import pytest

from dmsim.plan.macro import MacroPlanner
from dmsim.plan.stagegen import graph_from_items, graph_from_leaf_parts, stages_from_leaf_parts
from dmsim.plan.stagegraph import Node, StageGraph, merge_targets, search_target


def _g():
    return StageGraph.from_stage_dicts([
        {"id": "a", "target": {"hand": {"x": 1}}},
        {"id": "b", "target": {"hand": {"y": 1}}, "requires": []},          # a と並列
        {"id": "c", "target": {"bz": {"z": 1}}, "requires": ["a", "b"]},
    ])


def test_chain_files_stay_chains():
    g = StageGraph.from_stage_dicts([{"target": {"hand": {"x": 1}}}, {"target": {"hand": {"x": 2}}}])
    assert g.is_chain() and [n.id for n in g.nodes] == ["s0", "s1"]
    assert g.ready(set())[0].id == "s0" and g.ready({"s0"})[0].id == "s1"


def test_parallel_and_prerequisites():
    g = _g()
    assert not g.is_chain()
    assert {n.id for n in g.ready(set())} == {"a", "b"}          # 順序は決めない
    assert [n.id for n in g.ready({"a"})] == ["b"]
    assert [n.id for n in g.ready({"a", "b"})] == ["c"]
    assert [n.id for n in g.nodes][-1] == "c"                     # 前提が先に来る


def test_alternatives_any_of():
    g = StageGraph([Node("a", {}), Node("b", {}), Node("c", {}, (("a", "b"),))])
    assert "c" not in {n.id for n in g.ready(set())}
    assert "c" in {n.id for n in g.ready({"b"})}


def test_cycle_and_unknown_requirement_rejected():
    with pytest.raises(ValueError):
        StageGraph([Node("a", {}, ("b",)), Node("b", {}, ("a",))])
    with pytest.raises(ValueError):
        StageGraph([Node("a", {}, ("zz",))])


def test_search_target_adds_done_stages():
    g = _g()
    tg = search_target(g, g.by_id()["c"], {"a", "b"})
    assert tg == merge_targets(merge_targets({"bz": {"z": 1}}, {"hand": {"x": 1}}), {"hand": {"y": 1}})


def test_graph_from_items_parallel_within_zone():
    g = graph_from_items([("hand", "p", 1), ("hand", "q", 2), ("bz", "f", 1)])
    by = g.by_id()
    assert by["hand:px1"].requires == () and by["hand:qx2"].requires == ()
    assert set(by["bz:fx1"].requires) == {"hand:px1", "hand:qx2"}


def test_leaf_parts_graph_matches_chain_targets():
    import yaml
    c = next(x for x in yaml.safe_load(open("data/known_combos/combos.yaml", encoding="utf-8"))["combos"] if x["id"] == "akashic")
    g = graph_from_leaf_parts(c["leaf_parts"])
    chain = stages_from_leaf_parts(c["leaf_parts"])
    assert len(g.nodes) == len(chain)
    final = {}
    for n in g.nodes:
        final = merge_targets(final, n.target)
    assert final == chain[-1]["target"]                          # 全部を合わせた最終盤面は鎖の最後の段と同じ


def test_planner_picks_ready_stage_in_graph(rules):
    from dmsim.engine import Engine
    e = Engine.new_game(rules, [["T001"] * 40, ["T001"] * 40], 1, first_player=0)
    g = StageGraph([Node("a", {"hand": {"NO_SUCH": 1}}), Node("b", {"hand": {"T001": 1}}), Node("c", {"hand": {"T001": 1}}, ("a", "b"))])
    mp = MacroPlanner(g)
    p = mp.plan(e, 0)
    assert mp.progress(e, 0) == 1              # b だけ済み（並列）。c は前提 a が未達
    assert p.idx == 1 and p.stages[p.idx] == {"hand": {"NO_SUCH": 1}} and p.intent == "chain"


def test_reach_graph_chain_and_parallel(rules):
    from dmsim.discovery.reachsearch import reach_graph
    from dmsim.engine import Engine

    def game():
        return Engine.new_game(rules, [["T001"] * 40, ["T001"] * 40], 1, first_player=0)
    kw = dict(width=10, max_depth=30, max_turn=3)
    # 鎖: 従来の reach_chain と同じ結果（order に段の id が付く）
    chain = StageGraph.from_chain([{"mana": {"T001": 1}}, {"mana": {"T001": 2}}])
    r = reach_graph(game(), chain, 0, **kw)
    assert r["stages"] == 2 and r["order"] == ["s0", "s1"]
    # 並列 + 前提: a と b はどちらから取ってもよく、c は a・b の後
    g = StageGraph([Node("a", {"mana": {"T001": 1}}), Node("b", {"mana": {"T001": 2}}), Node("c", {"mana": {"T001": 3}}, ("a", "b"))])
    r = reach_graph(game(), g, 0, width=10, max_depth=30, max_turn=6)
    assert r["stages"] == 3 and r["order"][-1] == "c" and set(r["order"][:2]) == {"a", "b"}


def test_reach_graph_skips_stages_met_at_start(rules):
    from dmsim.discovery.reachsearch import reach_graph
    from dmsim.engine import Engine
    e = Engine.new_game(rules, [["T001"] * 40, ["T001"] * 40], 1, first_player=0)
    g = StageGraph([Node("a", {"hand": {"T001": 1}}), Node("b", {"mana": {"T001": 1}}, ("a",)), Node("c", {"hand": {"T001": 1}}, ())])
    r = reach_graph(e, g, 0, width=10, max_depth=30, max_turn=3)
    assert r["order"][0] != "a" and "a" not in r["order"]       # 開始の手札で済んでいる段は数えない


def test_combo_sequence_plan_loads_as_graph(tmp_path):
    from dmsim.plan.macro import load_plan_graph
    from dmsim.plan.spec import PlanSpec, dump_jsonl
    plan = PlanSpec(kind="combo_sequence", params={
        "stages": [{"id": "a", "target": {"hand": {"x": 1}}}, {"id": "b", "target": {"hand": {"y": 1}}, "requires": []},
                   {"id": "c", "target": {"bz": {"z": 1}}, "requires": ["a", "b"]}],
        "goal": {"shield": {"*": 10}}})
    g = load_plan_graph(plan)
    assert not g.is_chain() and {n.id for n in g.ready(set())} == {"a", "b"}
    assert g.by_id()["goal"].requires == ("c",)            # 出口は最後の段（他の段の前提になっていない c）の後
    f = tmp_path / "p.jsonl"
    dump_jsonl([plan], f)
    assert [n.id for n in load_plan_graph(f).nodes] == [n.id for n in g.nodes]    # 記録形式（JSONL）を経由しても同じ


def test_plan_without_stages_uses_minimal_board():
    from dmsim.discovery.loopspec import Pred
    from dmsim.plan.macro import load_plan_graph
    from dmsim.plan.spec import PlanSpec
    plan = PlanSpec(kind="loop", minimal=[Pred(owner=0, match={"name": "p"}, n=1, op=">=", zone="hand", zones=()),
                                         Pred(owner=0, match={"name": "f"}, n=1, op=">=", zone="bz", zones=())])
    g = load_plan_graph(plan)
    assert [n.id for n in g.nodes] == ["hand:px1", "bz:fx1"] and g.by_id()["bz:fx1"].requires == ("hand:px1",)
