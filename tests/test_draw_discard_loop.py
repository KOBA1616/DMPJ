"""「引いて捨てる」型のループ証明書（docs/saga-loop-miss-20261113.md 案 A）。"""
import dataclasses

import pytest

from dmsim.engine import scenario
from dmsim.engine.core import IllegalAnswer
from dmsim.engine.loop import WILD_HAND, fast_forward, is_burn, replay_keys, verify, wild_keys
from dmsim.eval import loop_entry as le, ruler_control as rc
import dmsim.search.turn as T


def test_wild_keys_only_abstracts_cards_outside_hand_keys():
    assert wild_keys(["hand:a:0", "hand:b:0", "graveyard:b:0", "yes"], {"a"}) == ["hand:a:0", WILD_HAND, "graveyard:b:0", "yes"]


def test_burn_needs_hand_not_shrinking():
    # 手札を出し続けるだけ（手札が減る）の連続プレイは山札削りのループに数えない
    assert is_burn({"deck:0": -1, "graveyard:0": 1}, 0)
    assert not is_burn({"deck:0": -1, "hand:0": -1, "graveyard:0": 2}, 0)
    assert not is_burn({"deck:0": -1, "deck:1": -1}, 0)   # 相手に効くものは別の経路（kill）で扱う


@pytest.fixture(scope="module")
def rules():
    import os
    from dmsim.cards.defs import load_rules
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        return load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old


@pytest.fixture(scope="module")
def saga0(rules):
    r = rules
    ls = le.load("saga")
    v = rc.vary(r, ls, 0)
    return scenario.build(r, rc._entry_spec(v, rc._deck(ls), 0), first_player=0)


def _first_cert(eng, draw_discard=True):
    found = []
    ts = T.TurnSearch(0, 200)
    ts.draw_discard = draw_discard
    orig = T.TurnSearch._stocks

    def spy(self, e, cert):
        found.append((e.clone(), cert))
        return orig(self, e, cert)
    T.TurnSearch._stocks = spy
    try:
        leaf, st = ts.run(eng)
    finally:
        T.TurnSearch._stocks = orig
    return leaf, st, found


def test_saga_entry_becomes_wild_burn_certificate(saga0):
    leaf, st, found = _first_cert(saga0)
    assert leaf.s.result and leaf.s.result["winner"] == 0
    assert st.chosen and st.chosen[0]["kind"] == "burn" and st.chosen[0]["wild"]
    e, cert = found[0]
    assert cert.wild and any(WILD_HAND in k for k in cert.actions)
    # 入口時点の手札の札は抽象キーにしない（捨て先にならない）
    assert not any(k.startswith("hand:") and k != WILD_HAND and k.split(":")[1] not in cert.hand_keys
                   for ks in cert.actions for k in ks)
    assert verify(e, dataclasses.replace(cert, verified=0, notes=[]), times=2).verified == 2


def test_wild_replay_never_discards_hand_keys_cards(saga0):
    _, _, found = _first_cert(saga0)
    e, cert = found[0]
    e = e.clone()
    keep = sorted(e.s.cards[c].defn for c in e.s.zones["hand"][0] if e.s.cards[c].defn in cert.hand_keys)
    fast_forward(e, cert, 3)
    assert sorted(e.s.cards[c].defn for c in e.s.zones["hand"][0] if e.s.cards[c].defn in cert.hand_keys) == keep


def test_fast_forward_rejects_divergence(saga0):
    _, _, found = _first_cert(saga0)
    e, cert = found[0]
    bad = dataclasses.replace(cert, delta={"deck:0": -2})
    with pytest.raises(IllegalAnswer):
        fast_forward(e.clone(), bad, 2)


def test_replay_keys_raises_when_only_hand_keys_cards(saga0):
    _, _, found = _first_cert(saga0)
    e, cert = found[0]
    e = e.clone()
    while (d := e.advance()) is not None:
        if any(o["key"].startswith("hand:") for o in d["options"]):
            allk = {o["key"].split(":")[1] for o in d["options"] if o["key"].startswith("hand:")}
            with pytest.raises(IllegalAnswer):
                replay_keys(e, [WILD_HAND], allk)
            return
        e.answer(T.candidates(e, d, T.Weights(), cap=1)[0])


def test_switch_off_restores_old_behaviour(saga0):
    _, st, _ = _first_cert(saga0, draw_discard=False)
    assert all(not lp.get("wild") for lp in st.chosen)


def test_repeat_first_orders_previous_choice_first(saga0):
    """案 E: 同じ種類の決定で前に選んだ意味キーが今の選択肢にあれば、その候補を先頭へ（カード名は見ない）。"""
    ts = T.TurnSearch(0, 1)
    ts._root_log = 0
    e = saga0.clone()
    d = {"kind": "choose_cards", "player": 0, "options": [{"key": "a"}, {"key": "b"}]}
    e.log.append({"p": 0, "kind": "choose_cards", "choice": [1], "keys": ["b"]})
    assert ts._repeat_order(e, d, [[0], [1]]) == [[1], [0]]
    e.log.append({"p": 0, "kind": "choose_cards", "choice": [0], "keys": ["zzz"]})   # 今の選択肢に無いキーの決定は飛ばす
    assert ts._repeat_order(e, d, [[0], [1]]) == [[1], [0]]

