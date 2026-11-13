"""相手の抵抗の段階（物差し タスク11）。0 は従来どおり、1 は盾に実在の S・トリガーが入る。"""
from collections import Counter

from dmsim.search.opponent import RESIST_COPIES, RESIST_TRIGGERS, resistance


def test_level0_is_legacy():
    model, deck = resistance(0)
    assert model is None and deck == ["T001"] * 40


def test_level1_has_real_triggers():
    model, deck = resistance(1)
    assert model.strigger and model.block and model.play == "none"
    c = Counter(deck)
    assert len(deck) == 40 and sum(c[t] for t in RESIST_TRIGGERS) == RESIST_COPIES


def test_level1_cards_are_strigger(rules_real=None):
    from dmsim.cards.defs import load_rules
    r = load_rules()
    for t in RESIST_TRIGGERS:
        assert "s_trigger" in r.cards[t].keywords, t
