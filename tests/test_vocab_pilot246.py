"""第246弾: when の cause.defn — 特定カードの能力で破壊される時の置換（instead: [] でとどまる）。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def _game(gears):
    e = setup(_rules(), {"bz": ["T655"] + gears}, {"bz": ["T667"]})
    host = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T655")
    for g in gears:
        gc = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == g)
        e.s.cards[gc].crossed = e.s.ref(host)
    return e, host


def _attack_and_settle(e, host):
    tgt = next(c for c in e.zlist("bz", 1) if e.s.cards[c].defn == "T667")
    for _ in range(200):
        if tgt in e.zlist("graveyard", 1) and (host in e.zlist("bz", 0) or host in e.zlist("graveyard", 0)):
            return
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        atk = next((i for i, k in enumerate(keys) if k == "attack:T655:player"), None)
        if atk is not None:
            e.answer([atk])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))


def test_host_survives_named_destroy_with_both_gears():
    e, host = _game(["T665", "T666"])
    _attack_and_settle(e, host)
    tgt = next(c for c in e.zlist("bz", 1) + e.zlist("graveyard", 1) if e.s.cards[c].defn == "T667")
    assert tgt in e.zlist("graveyard", 1)   # 相手の小兵は破壊された
    assert host in e.zlist("bz", 0)         # ホストは置換でとどまる


def test_host_destroyed_without_protective_gear():
    e, host = _game(["T666"])
    _attack_and_settle(e, host)
    assert host in e.zlist("graveyard", 0)  # T665 が無いので通常どおり破壊される
