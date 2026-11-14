"""揃うの使えるゾーン（§21）と経路札の温存（§21）、基盤選びの段の基準（§22）。"""
import os

import pytest

from dmsim.discovery import basebuild as B
from dmsim.eval import loop_entry as L
from dmsim.search import route_goal as RG
from dmsim.search import turn as TS


@pytest.fixture(scope="module")
def full_rules():
    from dmsim.cards.defs import load_rules
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        return load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old


def test_keep_hand_hook_is_off_by_default():
    assert TS.KEEP_HAND is None


def test_usable_zones_exclude_mana_unless_named(full_rules):
    rules = full_rules
    ls = L.load("saga")
    uz = L.usable_zones(rules, ls)
    for i, z in uz.items():
        assert {"hand", "bz"} <= z and "mana" not in z
    assert "graveyard" in uz["dm22ex2-021"]


def test_usable_zones_take_mana_from_route(full_rules):
    rules = full_rules
    ls = L.load("akashic_hd2")
    st = RG.load("akashic")
    named_mana = {q["match"]["name"] for s in st for q in s.preds if q.get("zone") == "mana" and "name" in q.get("match", {})}
    uz = L.usable_zones(rules, ls, st)
    for i in named_mana & set(uz):
        assert "mana" in uz[i]


def test_score_counts_stage_progress():
    rows = [{"entry_turn": None, "cards_turn": None, "stage_turn": {"4": 5}}]
    assert B.score(rows, 6) == 0
    assert B.score(rows, 6, 5) == 2 + 4 / 5


def test_roles_of_adds_recover():
    raw = {"spell": [{"op": "move", "select": {"zone": "graveyard", "owner": "you"}, "to": "hand"}], "abilities": []}
    assert "recover" in B.roles_of(raw)
