"""中核を固定して基盤を選ぶ（dmsim.discovery.basebuild）。"""
import os

import pytest

from dmsim.discovery import basebuild as B


@pytest.fixture(scope="module")
def full_rules():
    from dmsim.cards.defs import load_rules
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        rules = load_rules()
        RAW.update(B._raw_cards(rules))   # converted.yaml も読む生データ（環境変数は外したままにしない: 他のモジュールへ漏れる）
        return rules
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old


RAW: dict = {}


SAGA = {"dm22ex2-021": 4, "dmrp03-s03": 4}


@pytest.mark.slow
def test_candidates_are_mechanical(full_rules):
    cands = B.candidates(full_rules, SAGA, RAW)
    civs = B.core_civs(full_rules, SAGA)
    ids = [i for v in cands.values() for i in v]
    assert ids and all(not B._test(i) and i not in SAGA for i in ids)
    assert all(set(full_rules.cards[i].civs) <= civs and full_rules.cards[i].cost <= B.MAX_COST for i in ids)
    assert all(len(v) <= B.PER_ROLE for v in cands.values())


def test_base_deck_and_swap(full_rules):
    fill = B.fillers(full_rules, SAGA, RAW)
    assert fill and all(full_rules.cards[f].is_creature() and not full_rules.cards[f].abilities for f in fill)
    d = B.base_deck(SAGA, fill)
    assert len(d) == 40 and d.count("dm22ex2-021") == 4
    d2 = B._swap(d, fill, "X")
    assert len(d2) == 40 and d2.count("X") == 4 and d2.count("dm22ex2-021") == 4


def test_score_prefers_entry_and_early():
    a = [{"entry_turn": 4, "cards_turn": 3}]
    b = [{"entry_turn": None, "cards_turn": 3}]
    c = [{"entry_turn": None, "cards_turn": 6}]
    assert B.score(a, 6) > B.score(b, 6) > B.score(c, 6) > B.score([{"entry_turn": None, "cards_turn": None}], 6)


def test_fillers_are_vanilla_creatures_and_skip_missing_effect(full_rules):
    from dmsim.discovery import basebuild as B
    rules = full_rules
    core = {"dm22ex2-021": 4, "dmrp03-s03": 4}
    for i in B.fillers(rules, core, RAW):
        c = rules.cards[i]
        assert c.is_creature() and not B.missing_effect(c)
    for ids in B.candidates(rules, core, RAW).values():
        assert not any(B.missing_effect(rules.cards[i]) for i in ids)


def test_missing_effect_flags_empty_spell_side():
    from types import SimpleNamespace as N
    from dmsim.discovery import basebuild as B
    sp = N(types=["spell"], spell=[], sst_spell=[], stp_spell=[], abilities=[], faces=[], keywords=[], text="x")
    assert B.missing_effect(sp)
    sp.spell = [{"op": "draw", "count": 1}]
    assert not B.missing_effect(sp)
