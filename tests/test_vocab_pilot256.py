"""第256弾: not_reason（召喚以外の方法で出た時にだけ誘発する）。"""
from tests.conftest import setup
from dmsim.cards.defs import load_rules


def _drive(e, stop, limit=400, may_yes=True):
    for _ in range(limit):
        if stop(e):
            return True
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if any(k.startswith("play:") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:"))])
        elif d["kind"] == "yes_no":
            e.answer([0] if may_yes else [1])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return stop(e)


def test_normal_summon_does_not_trigger():
    # 相手が通常召喚したクリーチャーは戻らない
    e = setup(load_rules(), {"bz": ["T692"]},
              {"hand": ["T001"], "mana": ["T007", "T007"]})
    _drive(e, lambda e: any(e.s.cards[c].defn == "T001" for c in e.zlist("bz", 1)))
    _drive(e, lambda e: e.s.active == 0)
    assert any(e.s.cards[c].defn == "T001" for c in e.zlist("bz", 1))   # 場に残っている


def test_put_entry_triggers_bounce():
    # 相手が呪文で「出した」クリーチャーは手札に戻る
    e = setup(load_rules(), {"bz": ["T692"]},
              {"hand": ["T693", "T001"], "mana": ["T010", "T010", "T010"]})
    ok = _drive(e, lambda e: any(e.s.cards[c].defn == "T693" for c in e.zlist("graveyard", 1)))
    assert ok, "呪文が唱えられていない"
    _drive(e, lambda e: e.s.active == 0)
    assert not any(e.s.cards[c].defn == "T001" for c in e.zlist("bz", 1))   # 場に残っていない
    assert any(e.s.cards[c].defn == "T001" for c in e.zlist("hand", 1))     # 手札に戻った
