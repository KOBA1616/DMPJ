"""登録簿の手順を探索の1手として使う口（dmsim.search.macro）。"""
import os

import pytest

from dmsim.search import macro
from dmsim.search.turn import TurnSearch


@pytest.fixture(scope="module")
def full_rules():
    from dmsim.cards.defs import load_rules
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        return load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old


def _entry(rules, name, seed):
    from dmsim.engine import scenario
    from dmsim.eval import loop_entry as le
    from dmsim.eval.ruler_control import _deck, _entry_spec, vary
    ls = le.load(name)
    e = scenario.build(rules, _entry_spec(vary(rules, ls, seed), _deck(ls), seed), first_player=0)
    e.advance()
    return e


def test_off_by_default(monkeypatch):
    monkeypatch.delenv("DMSIM_REGISTRY_MACRO", raising=False)
    macro.enable(None)
    assert not macro.enabled() and macro.active() == []


def test_registry_macros_load():
    ms = macro.load()
    ids = {m.id for m in ms}
    assert {"saga", "akashic"} <= ids and "drill_lock" not in ids      # holdout は照会に出ない
    assert all(m.steps and m.preds and m.core for m in ms)


def test_macro_wins_from_unseen_entry(full_rules):
    """登録に使っていないシード（9）の入口局面で、手ありの探索（予算200）が手を採ってそのターンに勝つ。"""
    e = _entry(full_rules, "akashic", 9)
    out, st = TurnSearch(0, 200).run(e)
    assert out.s.result is None or out.s.result["winner"] != 0       # 手なしでは勝てない
    ts = TurnSearch(0, 200)
    ts.macros = macro.load()
    out, st = ts.run(e)
    assert out.s.result["winner"] == 0 and st.chosen[0]["source"] == "registry"
    assert e.s.result is None                                         # 元の局面は変えない


def test_replay_discards_when_core_missing(full_rules):
    """中核の札が足りない局面では手順が続かず、手は不成立（None）。"""
    from dmsim.search.turn import candidates, charge_only_policy
    from dmsim.search.leaf_eval import Weights
    e = _entry(full_rules, "akashic", 9)
    m = next(x for x in macro.load() if x.id == "akashic")
    w = Weights()
    hand = [c for c in e.zlist("hand", 0) if e.s.cards[c].defn == "dm23bd7-035"]
    for c in hand:
        e._raw_move(c, "graveyard")
    assert macro.replay(m, e, 0, charge_only_policy, lambda x, d: candidates(x, d, w, 6)) is None
