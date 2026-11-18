"""第229弾の登録形テスト: bio_k 再変換5枚（ラウンド265）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build

IDS = ["dm23-005", "dm23-028", "dm23-037", "dm23-s01", "dmx11-076"]


def _game(p0, p1):
    rules = load_rules()
    return build(rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                         "deck_size": 20})


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _drive(e, attacker, done, max_steps=160):
    for _ in range(max_steps):
        if done(e):
            return
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack":
            ak = f"attack:{attacker}:player"
            e.answer([keys.index(ak)] if ak in keys else [keys.index("pass")])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif d["kind"] == "choose_breaker":
            bk = next((k for k in keys if k == "breaks:2"), None)
            e.answer([keys.index(bk)] if bk else [0])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "choose_cards":
            pk = next((i for i, k in enumerate(keys) if "T615" in k), None)
            e.answer([pk] if pk is not None else list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("did not finish")


def test_all_registered():
    e = _game({}, {})
    for cid in IDS:
        assert cid in e.rules.cards, cid


def test_028_grant_makes_two_breaks():
    e = _game({"bz": ["T614"], "hand": ["dm23-028"]}, {})
    before = len(e.zlist("shield", 1))
    _drive(e, "T614", lambda e: len(e.zlist("shield", 1)) == before - 2)
    assert "dm23-028" in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 1)) == before - 2


def test_005_search_same_name():
    e = _game({"bz": ["T613"], "hand": ["dm23-005"], "deck": ["T615"]}, {})
    _drive(e, "T613", lambda e: "T615" in _defns(e, "hand", 0))
    assert "T615" in _defns(e, "hand", 0)     # 攻撃クリーチャー（T613）と同名の T615
    assert "dm23-005" in _defns(e, "graveyard", 0)
