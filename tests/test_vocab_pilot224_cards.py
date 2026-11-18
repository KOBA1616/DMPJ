"""第224弾の登録形テスト: cross_gear_effect 再変換6枚（ラウンド260）。

converted.yaml の実カードで、ホストへの付与と攻撃誘発を確認する。
クロス状態は第170弾のテストと同様に状態へ直接設定する。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build

IDS = ["dmex16-041", "dmex17-107", "dmex17-cho07", "dmex17-w15",
       "dmpcd02-a11", "dmpcd02-a13"]


def _game(p0, p1):
    rules = load_rules()
    return build(rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                         "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _cid(e, p, defn, zone="bz"):
    return next(c for c in e.zlist(zone, p) if e.s.cards[c].defn == defn)


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _cross(e, gear, host, p=0):
    e.s.cards[_cid(e, p, gear)].crossed = e.s.ref(_cid(e, p, host))


def _attack_with(e, host_defn, picks=2, stop_when=None):
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        if stop_when is not None and stop_when(e):
            return
        keys = _keys(d)
        kind = d["kind"]
        atk = f"attack:{host_defn}:player"
        if kind == "attack" and atk in keys:
            e.answer([keys.index(atk)])
            continue
        if e.s.turn > 1:
            return
        if kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif kind == "choose_cards":
            e.answer(list(range(min(d["max"], picks))))
        elif kind == "choose_shields":
            e.answer(list(range(d["min"])))
        elif kind == "yes_no":
            e.answer([0])
        elif kind.startswith("declare"):
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("did not settle")


def test_all_registered(rules=None):
    e = _game({}, {})
    for cid in IDS:
        assert cid in e.rules.cards, cid


def test_041_host_grant_and_attack_trigger():
    e = _game({"bz": ["T002", "dmex16-041"]}, {"bz": ["T060"]})
    _cross(e, "dmex16-041", "T002")
    ch = e.chars(_cid(e, 0, "T002"))
    assert ch["power"] == 10000 and "powered_breaker" in ch["keywords"]
    _attack_with(e, "T002")
    assert "T060" in _defns(e, "graveyard", 1)
    assert len(_defns(e, "shield", 1)) == 2        # 効果ブレイク1＋攻撃ブレイク2


def test_cho07_breaks_add_and_mana_burn():
    e = _game({"bz": ["T201", "dmex17-cho07"]}, {"mana": ["T001", "T001", "T001"]})
    _cross(e, "dmex17-cho07", "T201")
    ch = e.chars(_cid(e, 0, "T201"))
    assert ch["power"] == 11000 and ch["breaks"] == 2
    _attack_with(e, "T201")
    assert len(_defns(e, "mana", 1)) == 1
    assert len(_defns(e, "graveyard", 1)) == 2
    assert len(_defns(e, "shield", 1)) == 3


def test_w15_blocker_and_random_discard():
    e = _game({"bz": ["T002", "dmex17-w15"]}, {"hand": ["T001", "T002", "T006"]})
    _cross(e, "dmex17-w15", "T002")
    ch = e.chars(_cid(e, 0, "T002"))
    assert ch["power"] == 5000 and "blocker" in ch["keywords"]
    _attack_with(e, "T002", stop_when=lambda e: len(_defns(e, "graveyard", 1)) == 1)
    assert len(_defns(e, "hand", 1)) == 2
    assert len(_defns(e, "graveyard", 1)) == 1


def test_a11_attack_draw_and_a13_mana_put():
    e = _game({"bz": ["T002", "dmpcd02-a11"]}, {})
    _cross(e, "dmpcd02-a11", "T002")
    _attack_with(e, "T002")
    assert len(_defns(e, "hand", 0)) == 1
    e = _game({"bz": ["T002", "dmpcd02-a13"]}, {})
    _cross(e, "dmpcd02-a13", "T002")
    _attack_with(e, "T002")
    assert len(_defns(e, "mana", 0)) == 1


def test_107_g_zero_generate_and_host_plus():
    e = _game({"bz": ["T002"], "hand": ["dmex17-107"]}, {})
    for _ in range(60):
        d = e.advance()
        assert d is not None
        keys = _keys(d)
        if d["kind"] == "main":
            play = next((k for k in keys if k.startswith("play:dmex17-107")), None)
            assert play is not None and play.endswith(":free"), keys   # G・ゼロの無料選択肢
            e.answer([keys.index(play)])
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    for _ in range(60):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "attack"):
            break
        keys = _keys(d)
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "dmex17-107" in _defns(e, "bz", 0)
    _cross(e, "dmex17-107", "T002")
    assert e.chars(_cid(e, 0, "T002"))["power"] == 1500   # ホスト+500
