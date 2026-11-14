"""ループの入口の開始局面（dmsim.eval.loop_entry）。docs/combo-ruler-design.md §6 タスク1。"""
from collections import Counter

import pytest

from dmsim.eval import loop_entry as L


@pytest.fixture(scope="module")
def rules():
    """実カード（converted.yaml 含む）が要る。他のテストへ影響しないよう環境変数を戻す。"""
    import os
    from dmsim.cards.defs import load_rules
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        return load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old


def test_entries_exist():
    assert {"saga", "akashic"} <= set(L.names())


@pytest.mark.parametrize("name", ["saga", "akashic"])
def test_entry_is_realistic(rules, name):
    ls = L.load(name)
    spec = L.entry_spec(ls, 0)
    mine = [c for ids in spec["p0"].values() for c in ids]
    assert Counter(mine) == Counter(L.deck_of(ls))              # 自分の札は実デッキの40枚ちょうど（ダミー・水増しなし）
    assert not any(c.startswith("T") for c in mine)
    for sd in range(3):
        e = L.build(rules, ls, sd)
        s = e.s
        assert not L.unmet(e, ls)                                # 入口 M を満たす
        assert len(s.zones["shield"][1]) == 5 and len(s.zones["deck"][1]) == 27
        assert len(s.zones["mana"][0]) <= 5
        assert sum(len(s.zones[z][0]) for z in ("bz", "hand", "mana", "shield", "graveyard", "deck")) == 40


def test_akashic_wins_by_loop(rules):
    r = L.measure(rules, "akashic", [0], max_turn=1)[0]
    assert (r["kill_turn"], r["kind"], r["origin"]) == (1, "loop_deck_out", "loop")


def test_saga_wins_by_shakogairu(rules):
    r = L.measure(rules, "saga_v1", [0], max_turn=1)[0]   # 旧い入口（シャコガイルが場）からは1ターンで勝つ
    assert (r["kill_turn"], r["kind"]) == (1, "effect")
