"""3枚組の探索（dmsim/discovery/triples.py）: 部品の収集と勝ち手段の付け足しで、既知のサガ＋シャコガイルに届くこと（2026-11-14）。"""
import os

import pytest


@pytest.fixture(scope="module")
def env():
    from dmsim.cards.defs import load_rules
    from dmsim.discovery import triples as X
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        rules = load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old
    return rules, X.by_card_of(rules)


def test_saga_single_and_shakogairu_attached(env):
    from dmsim.discovery import triples as X
    from dmsim.eval import loop_entry as le
    rules, by = env
    core = le.core_ids(le.load("saga"))
    bases, _ = X.collect(rules, by, pairs=False)
    hit = [b for b in bases if b.cards[0] in core]
    assert hit, "サガ単体のループ（別のコピー同士の蘇生）が部品に入る"
    assert hit[0].gains.get(("you", "deck"), 0) < 0
    tr = X.attach(rules, by, hit, per_base=20)
    assert any(set(t.cards()) <= set(core) | {t.win} and t.win in core for t in tr), "勝ち手段の索引から中核の残り（特殊勝利）を引く"


def test_entry_spec_places_parts(env):
    from dmsim.discovery import triples as X
    rules, _ = env
    from dmsim.eval import loop_entry as le
    core = le.core_ids(le.load("saga"))
    deck = X.deck_of(rules, core)
    sp = X.entry_spec(rules, deck, core[:1], 3, 1)
    p0 = sp["p0"]
    assert len(p0["mana"]) == 3 and len(p0["shield"]) == 5 and len(p0["hand"]) + len(p0["bz"]) >= 5
    assert sum(len(v) for v in p0.values()) == 40
