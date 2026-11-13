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


def test_on_by_default_and_switch(monkeypatch):
    monkeypatch.delenv("DMSIM_REGISTRY_MACRO", raising=False)
    macro.enable(None)
    assert macro.enabled() and macro.active()            # 既定有効（設計書 §19）
    monkeypatch.setenv("DMSIM_REGISTRY_MACRO", "0")
    assert not macro.enabled() and macro.active() == []


def test_ruler_measures_without_macros(full_rules, monkeypatch):
    """物差し（陽性対照・登録簿の検証）は登録簿の手を使わずに測る。"""
    from dmsim.eval import loop_entry as le, ruler_control as rc
    seen = []
    orig = macro.active
    monkeypatch.setattr(macro, "active", lambda: seen.append(macro.enabled()) or orig())
    monkeypatch.delenv("DMSIM_REGISTRY_MACRO", raising=False)
    macro.enable(None)
    rc.run_one(full_rules, le.load("saga"), 1, budget=20)
    assert seen and not any(seen)
    assert macro.enabled()                                  # 終わったら元に戻る


def test_registry_macros_load():
    ms = macro.load()
    ids = {m.id for m in ms}
    assert {"saga", "akashic"} <= ids and "drill_lock" not in ids      # holdout は照会に出ない
    assert all(m.steps and m.preds and m.core for m in ms)


def test_macro_wins_from_unseen_entry(full_rules, monkeypatch):
    """登録に使っていないシード（9）の入口局面で、手ありの探索（予算200）が手を採ってそのターンに勝つ。
    マナチャージの一般則（CHARGE_KEEP_FREE、§18）を入れると手なしでも勝てるので、ここでは切って手の効き目を見る。"""
    import dmsim.search.turn as T
    monkeypatch.setattr(T, "CHARGE_KEEP_FREE", False)
    e = _entry(full_rules, "akashic", 9)
    ts0 = TurnSearch(0, 200)
    ts0.macros = []
    out, st = ts0.run(e)
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
