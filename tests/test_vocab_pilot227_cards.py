"""第227弾の登録形テスト: untap_limit 再変換5枚（ラウンド263）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build

IDS = ["dm24ex4-053", "dmex19-m32", "dmr12-007", "dmrp16-s08", "dmx20-001"]


def _game(p0, p1):
    rules = load_rules()
    return build(rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                         "deck_size": 20})


def _tap_all(e, zone, p):
    cids = [c for c in e.zlist(zone, p)
            if zone != "bz" or e.s.cards[c].controller == p]
    for c in cids:
        e.s.cards[c].tapped = True
    return cids


def _answer(e, d, play=None):
    keys = [o["key"] for o in d["options"]]
    if d["kind"] == "main" and play:
        pk = next((k for k in keys if k.startswith(play)), None)
        if pk is not None:
            e.answer([keys.index(pk)])
            return
    if d["kind"] == "pay_mana":
        e.answer(list(range(d["min"])))
    elif d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def _drive_to_untap_choice(e, cap, play=None, max_steps=200):
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] == "choose_cards" and d["player"] == 1 and d["min"] == cap \
                and d["min"] > 0:
            return d
        _answer(e, d, play=play)
    raise AssertionError("untap choice never came")


def _settle(e, cids, steps=6):
    """アンタップが適用されるまでだけ進める（次の自分のターン開始まで進めない）。"""
    for _ in range(steps):
        if any(not e.s.cards[c].tapped for c in cids):
            return
        d = e.advance()
        if d is None:
            return
        _answer(e, d)


def test_all_registered():
    e = _game({}, {})
    for cid in IDS:
        assert cid in e.rules.cards, cid


def test_dmr12_007_bz_cap():
    e = _game({"bz": ["dmr12-007"]}, {"bz": ["T002", "T060"]})
    cids = _tap_all(e, "bz", 1)
    d = _drive_to_untap_choice(e, 1)
    assert len(d["options"]) == 2
    e.answer([0])
    _settle(e, cids)
    assert sum(1 for c in cids if e.s.cards[c].tapped) == 1


def test_m32_mana_cap():
    e = _game({"bz": ["dmex19-m32"]}, {"mana": ["T001", "T002", "T030", "T050"]})
    cids = _tap_all(e, "mana", 1)
    d = _drive_to_untap_choice(e, 3)
    assert len(d["options"]) == 4
    e.answer([0, 1, 2])
    _settle(e, cids)
    assert sum(1 for c in cids if e.s.cards[c].tapped) == 1


def test_dmx20_001_revolution_gate():
    e = _game({"bz": ["dmx20-001"], "shield": ["T001", "T001"]},
              {"bz": ["T002", "T060"]})
    cids = _tap_all(e, "bz", 1)
    d = _drive_to_untap_choice(e, 1)
    e.answer([0])
    _settle(e, cids)
    assert sum(1 for c in cids if e.s.cards[c].tapped) == 1


def test_053_spell_effects_and_cap():
    e = _game({"hand": ["dm24ex4-053"],
               "mana": ["T050", "T050", "T050", "T030", "T030", "T030", "T030"]},
              {"hand": ["T002"], "bz": ["T002", "T060", "T551"],
               "mana": ["T001", "T002", "T030", "T050", "T551"]})
    mana1 = _tap_all(e, "mana", 1)
    # 呪文を唱える→解決→次の相手ターンのアンタップ選択（上限4）まで一続きに進める
    choice = None
    for _ in range(200):
        d = e.advance()
        assert d is not None
        if d["kind"] == "choose_cards" and d["player"] == 1 and d["min"] == 4:
            choice = d
            break
        _answer(e, d, play="play:dm24ex4-053")
    assert choice is not None and len(choice["options"]) == 5   # マナ5枚から4枚選ぶ
    assert len(e.zlist("hand", 1)) == 0                       # 見ないで1枚捨てさせた
    assert len(e.zlist("graveyard", 1)) == 4                  # 捨てた1枚＋自身で破壊した3体
    assert not [c for c in e.zlist("bz", 1) if e.s.cards[c].controller == 1]
    d = choice
    e.answer([0, 1, 2, 3])
    _settle(e, mana1)
    assert sum(1 for c in mana1 if e.s.cards[c].tapped) == 1
