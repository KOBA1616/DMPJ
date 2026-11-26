"""closedsets（サイクル＋前提閉集合の候補生成）のテスト。

統合テストは対照カードだけに絞った小さいグラフで、正準束のグラフに
サガ自己回帰・XENARCH 傍受・アカシック回転対が現れることと、
健全性ゲートの対照トレースが閉集合に届くことを確認する。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)   # 実カード全体で読む

import pytest  # noqa: E402

from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.discovery import closedsets as CS  # noqa: E402

CONTROL_CARDS = {   # 正準 ID で指定する（アカシック3 の正準は dm25ex2-cho005）
    "dm22ex2-021", "dm22rp2x-004",                       # サガ / XENARCH
    "dm25ex2-cho005", "dm23bd7-035", "dm24ex1-038", "dm25sp1-003",  # アカシック
    "dmrp08-s01",                                        # ゼブルエ
}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


@pytest.fixture(scope="module")
def graph(rules):
    return CS.build_graph(rules, only_cards=CONTROL_CARDS)


def test_is_test_card():
    assert CS.is_test_card("T375")
    assert CS.is_test_card("T001")
    assert not CS.is_test_card("dm22ex2-021")
    assert not CS.is_test_card("")


def test_graph_has_saga_self_loop(graph):
    saga = [i for i in graph.nodes if graph.meta[i]["card"] == "dm22ex2-021"]
    assert saga, "サガの束がノードに無い"
    assert any(graph.has_edge(i, i) for i in saga), "サガの自己回帰の辺が無い"


def test_graph_has_xenarch_intercept_edge(graph):
    saga = [i for i in graph.nodes if graph.meta[i]["card"] == "dm22ex2-021"]
    xen = [i for i in graph.nodes if graph.meta[i]["card"] == "dm22rp2x-004"]
    assert xen, "XENARCH の束がノードに無い"
    assert any(graph.has_edge(a, b) for a in saga for b in xen), \
        "サガ→XENARCH の傍受の辺が無い"


def test_graph_has_akashic_rotation_pair(graph):
    orz = [i for i in graph.nodes if graph.meta[i]["card"] == "dm23bd7-035"]
    holy = [i for i in graph.nodes if graph.meta[i]["card"] == "dm25sp1-003"]
    assert orz and holy
    assert any(graph.has_edge(a, b) for a in orz for b in holy)
    assert any(graph.has_edge(a, b) for a in holy for b in orz)


def test_akashic_enabler_present(graph):
    # 無料化の static はアカシック3 自身が持つ（核の札自身のイネーブラ）。
    # 種は正準 ID（dm23ex2-009 の正準は dm25ex2-cho005）で表す
    ens = [e for e in graph.enablers if e["card"] == "dm25ex2-cho005"]
    assert ens and ens[0]["kind"] == "free"


def test_cores_include_saga(graph):
    cores, _ = CS.enumerate_cores(graph)
    assert any(c["cards"] == ["dm22ex2-021"] for c in cores)


def test_trace_saga_xenarch_closed(graph, rules):
    ctrl = {"label": "saga+xenarch",
            "cards": {"dm22ex2-021", "dm22rp2x-004"}}
    d = CS.trace_control(graph, rules, ctrl)
    assert d["witness"] is not None, d
    roles = {b["role"] for b in d["witness"]["bundles"]}
    assert "output_conversion" in roles
    idxs = [b["i"] for b in d["witness"]["bundles"]
            if graph.meta[b["i"]]["origin"] != "static"]
    assert CS.premise_closed(graph, idxs)


def test_trace_akashic_passes_funnel(graph, rules):
    ctrl = {"label": "akashic",
            "cards": {"dm23ex2-009", "dm23bd7-035", "dm24ex1-038", "dmrp12-s01"}}
    d = CS.trace_control(graph, rules, ctrl)
    assert d["witness"] is not None, d
    assert d["stage"] == "pass", d["witness"]
    f = d["witness"]["features"]
    assert f["effective_mana"] == 0          # アカシック3 の無料化が届く
    assert f["closed"]


def test_trace_akashic_zebrue_closed(graph, rules):
    ctrl = {"label": "akashic+zebrue",
            "cards": {"dm23ex2-009", "dm23bd7-035", "dm24ex1-038", "dmrp08-s01"},
            # 最小コアはウォカンナを除く3種（v3 判定の確定結果）
            "core": {"dm23ex2-009", "dm23bd7-035", "dmrp08-s01"}}
    d = CS.trace_control(graph, rules, ctrl)
    assert d["witness"] is not None, d
    assert d["stage"] == "pass", d["witness"]


def test_draw_feeds_distinguishes_drawer():
    from dmsim.engine import zone_graph as Z
    mine = Z.Move("deck", "hand", draw=True, blind=True, owner="you")
    theirs = Z.Move("deck", "hand", draw=True, blind=True, owner="opp")
    assert Z.draw_feeds(mine, Z.Premise("draw", player="you"))
    assert not Z.draw_feeds(theirs, Z.Premise("draw", player="you"))
    assert Z.draw_feeds(theirs, Z.Premise("draw", player="opp"))
    assert not Z.draw_feeds(mine, Z.Premise("draw", player="opp"))
    # ターン開始ドロー限定の前提は効果のドローでは満たせない
    assert not Z.draw_feeds(mine, Z.Premise("draw", player="you", draw_gated=True))
