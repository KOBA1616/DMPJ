"""束の正準化（dmsim.engine.bundle_canon）のテスト（2026-11-26 語彙統合）。

合格条件の固定:
- 陽性対照（サガ自己回帰、サガ+XENARCH 傍受、アカシック4種、新規エンジン
  11件の核）が束として表現できる
- '?' の移動は理由付きの除外としてカバレッジに全件数えられる
- loop_cond は正準への委譲で、束・移動に注釈（when / once / conds）が付く
"""
import pytest

from dmsim.engine import bundle_canon as BC
from dmsim.engine import zone_graph as Z


# ---------------------------------------------------------------- 単体（rules 不要）

def test_premise_new_events():
    # tap 等のイベントも前提になる（従来は落ちていた 685 件の一部）
    p = BC.premise_of({"when": {"event": "tap", "subject": "self"}, "zone": "bz"})
    assert p is not None and p.kind == "tap"
    p = BC.premise_of({"when": {"event": "attack_end"}, "zone": "bz"})
    assert p is not None and p.kind == "attack_end"


def test_premise_move_without_to():
    # 行き先の無い move は「離れる」前提として残る
    p = BC.premise_of({"when": {"event": "move", "from": "bz",
                                "subject": "self"}, "zone": "graveyard"})
    assert p is not None and p.kind == "move" and p.to is None


def test_premise_summon_opponent_kept():
    # 相手が出した時の誘発も落とさない（主体が無ければ owner=opp で受ける）
    p = BC.premise_of({"when": {"event": "summon", "player": "opp"},
                       "zone": "bz"})
    assert p is not None and p.kind == "move" and p.to == "bz"
    assert p.subject == {"owner": "opp"}


def test_moves_binding_resolution():
    # move の as で束縛した札を、後続の ref で動かすと束縛先が移動元になる
    ops = [{"op": "move", "select": {"zone": "deck", "from_top": True},
            "to": "hand", "as": "x"},
           {"op": "move", "select": {"ref": "x"}, "to": "graveyard"}]
    ms = BC.moves_of(ops)
    assert [(m.src, m.dst) for m in ms] == [("deck", "hand"),
                                            ("hand", "graveyard")]
    assert all(m.src != "?" for m in ms)


def test_moves_special_selector():
    # under_of はバトルゾーンの下のカード
    ops = [{"op": "move", "select": {"under_of": "self"}, "to": "graveyard"}]
    ms = BC.moves_of(ops)
    assert ms[0].src == "bz"


def test_moves_unbound_ref_counted():
    cov = BC.Coverage()
    ops = [{"op": "move", "select": {"ref": "paid"}, "to": "graveyard"}]
    ms = BC.moves_of(ops, cov=cov)
    assert ms[0].src == "?"
    assert cov.qmark["ref_never_bound"] == 1
    assert cov.qmark_ref_names["paid"] == 1


def test_play_free_spell_filter_goes_graveyard():
    # 唱える対象が呪文だけなら、解決後の置き場所は墓地（resolve_to の既定）
    ops = [{"op": "play_free",
            "select": {"zone": "hand", "filter": {"types": ["spell"]}}}]
    ms = BC.moves_of(ops)
    assert (ms[0].src, ms[0].dst) == ("hand", "graveyard")
    ops = [{"op": "play_free",
            "select": {"zone": "hand", "filter": {"types": ["creature"]}}}]
    assert BC.moves_of(ops)[0].dst == "bz"


def test_registry_derived_from_op_args():
    # 子 op リストは OP_ARGS から生成される（凍結した対応表ではない）
    assert "modes" in BC.CHILD_KEYS["modal"]
    assert "effect" in BC.CHILD_KEYS["delayed_trigger"]
    assert "tap" in BC.PREMISE_EVENTS and "break" in BC.PREMISE_EVENTS


# ---------------------------------------------------------------- 全カード（対照）

@pytest.fixture(scope="module")
def built():
    # 対照カードには converted.yaml 由来のものが含まれるため、conftest の
    # DMSIM_SKIP_CONVERTED を読み込みの間だけ外す（test_ai.py と同じ作法）
    import os
    from dmsim.cards.defs import load_rules
    saved = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        rules = load_rules()
    finally:
        if saved is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = saved
    cov = BC.Coverage()
    bundles = BC.bundles(rules, cov)
    by_card = {}
    for b in bundles:
        by_card.setdefault(b.card, []).append(b)
    return rules, cov, by_card


def _rid(rules, cid):
    return rules.cards[cid].id


def _interceptor(rules, by_card, cid):
    # 傍受配線の判定は structsig の正準分類を使う
    from dmsim.discovery import structsig as SS
    for b in by_card.get(_rid(rules, cid), []):
        if SS.interceptor_kind(b) is not None:
            return b
    return None


def test_saga_selfloop(built):
    rules, _, by_card = built
    saga = by_card[_rid(rules, "dm22ex2-021")]
    assert any(b.prem and b.prem.kind == "move" and b.prem.to == "bz"
               and b.prem.subject == "self" and Z.feeds(b, b, rules) >= 1
               for b in saga)


def test_xenarch_interceptor_fed_by_saga(built):
    rules, _, by_card = built
    xen = _interceptor(rules, by_card, "dm22rp2x-004")
    assert xen is not None
    saga = by_card[_rid(rules, "dm22ex2-021")]
    assert any(Z.feeds(b, xen, rules) >= 1 for b in saga)


def test_akashic_static_and_rotation(built):
    rules, _, by_card = built
    aka = by_card[_rid(rules, "dm23ex2-009")]
    assert any(b.origin == "static"
               and "cast_free" in str((b.ann.get("static") or {}).get("mod"))
               for b in aka)
    orz = by_card[_rid(rules, "dm23bd7-035")]
    holy = by_card[_rid(rules, "dmrp12-s01")]
    assert any(Z.feeds(a, b, rules) >= 1 and Z.feeds(b, a, rules) >= 1
               for a in orz for b in holy)


def test_new_engine_partners(built):
    rules, _, by_card = built
    for cid in ("dmrp19-066", "dmrp20-068", "dmd05-009", "dmr11-029",
                "dmr13-091", "dmrp04s-077", "dmrp19-046"):
        assert _interceptor(rules, by_card, cid) is not None, cid
    for cid in ("dm26ex3-047", "dm26ex3-081", "dmrp13-016", "dmrp08-s01"):
        assert by_card.get(_rid(rules, cid)), cid


def test_reason_annotation(built):
    rules, _, by_card = built
    for cid in ("dm15-012", "promoy11-045"):
        assert any((b.ann or {}).get("reason") == "destroy"
                   for b in by_card[_rid(rules, cid)]), cid


def test_qmark_all_accounted(built):
    _, cov, _ = built
    rep = cov.report()
    # '?' の移動は全件、理由別カウンタの合計と一致する（黙って落ちない）
    assert rep["qmark_moves"] == sum(rep["qmark_reasons"].values())
    # 統合前（loop_cond 独自解釈）の 1,994 件から減っている
    assert rep["qmark_moves"] < 1994


def test_loop_cond_delegates_with_annotations(built):
    rules, _, _ = built
    from dmsim.discovery import loop_cond as C
    bs = C.bundles(rules)
    assert len(bs) == len(BC.bundles(rules))
    for b in bs:
        assert hasattr(b, "when") and hasattr(b, "once")
        for m in b.moves:
            assert hasattr(m, "conds")


# ---------------------------------------------------------------- 束縛の解決（課題6）

def _srcs(ops, **kw):
    return [(m.src, m.dst) for m in BC.moves_of(ops, **kw)]


def test_choose_binding_zone_list():
    # choose の zone がリストでも束縛は残る（置き場所はそのリスト）
    ops = [{"op": "choose", "select": {"zone": ["graveyard", "mana"]}, "as": "p"},
           {"op": "move", "select": {"ref": "p"}, "to": "bz"}]
    ms = BC.moves_of(ops)
    assert ms[0].src == ["graveyard", "mana"]


def test_choose_binding_from_ref_chain():
    # pile から選び直した hit は pile と同じ場所（山札）にいる
    ops = [{"op": "choose", "select": {"zone": "deck", "from_top": 3}, "as": "pile"},
           {"op": "choose", "select": {"ref": "pile", "count": "all"}, "as": "hit"},
           {"op": "move", "select": {"ref": "hit"}, "to": "graveyard"}]
    cov = BC.Coverage()
    ms = BC.moves_of(ops, cov=cov)
    assert [(m.src, m.dst) for m in ms] == [("deck", "graveyard")]
    assert not cov.qmark


def test_choose_binding_event_ref():
    prem = Z.Premise("move", to="graveyard")
    ops = [{"op": "choose", "select": {"ref": "event.subject"}, "as": "dead"},
           {"op": "move", "select": {"ref": "dead"}, "to": "bz"}]
    ms = BC.moves_of(ops, prem=prem)
    assert ms[0].src == "graveyard"


def test_repeat_as_follows_over():
    ops = [{"op": "choose", "select": {"zone": "deck", "from_top": 3}, "as": "casts"},
           {"op": "repeat", "over": "casts", "as": "it",
            "body": [{"op": "move", "select": {"ref": "it"}, "to": "bz"}]}]
    assert _srcs(ops) == [("deck", "bz")]


def test_crossed_ref_is_battle_zone():
    ops = [{"op": "move", "select": {"ref": "crossed"}, "to": "shield"}]
    assert _srcs(ops) == [("bz", "shield")]


def test_never_bound_ref_separated():
    # どこにも束縛が無い名前は原文データの欠陥として別理由で数える
    cov = BC.Coverage()
    BC.moves_of([{"op": "move", "select": {"ref": "ghost"}, "to": "hand"}], cov=cov)
    assert cov.qmark["ref_never_bound"] == 1 and "ref_unbound" not in cov.qmark


def test_full_rules_ref_holes_closed(built):
    # 全カードで '?' は原文データ欠陥（ref_never_bound）以外残らない
    _, cov, _ = built
    rep = cov.report()
    assert rep["qmark_reasons"].get("ref_unbound", 0) == 0
    assert rep["qmark_reasons"].get("ref_event_unresolved", 0) == 0
    assert rep["qmark_moves"] <= 10
