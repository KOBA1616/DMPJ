"""第237弾の登録形テスト: エクストラEXライフ再変換（ラウンド273）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build

IDS = ["dm26ex4-012", "dm26ex4-019", "dm26rp3-s007"]


def _game(p0, p1):
    rules = load_rules()
    return build(rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                         "deck_size": 20})


def test_all_registered():
    e = _game({}, {})
    for cid in IDS:
        assert cid in e.rules.cards, cid
    # 別刷りは aliases に畳まれている
    for canon, alias in (("dm26ex4-012", "dm26ex4-sec009"),
                         ("dm26ex4-019", "dm26ex4-sec020"),
                         ("dm26rp3-s007", "dm26rp3-sec008")):
        src = e.rules.cards[canon].source
        src = src if isinstance(src, dict) else vars(src)
        assert alias in (src.get("aliases") or []), (canon, alias)


def test_s007_links_two_shields_and_grants_them_strigger():
    e = _game({"hand": ["dm26rp3-s007"],
               "mana": ["T030", "T030", "T050", "T050", "T030", "T050", "T030"]}, {})
    shields0 = len(e.zlist("shield", 0))
    for _ in range(120):
        top = next((c for c in e.zlist("bz", 0)
                    if e.s.cards[c].defn == "dm26rp3-s007"), None)
        if top is not None:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:dm26rp3-s007") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:dm26rp3-s007"))])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert top is not None
    ref = e.s.ref(top)
    linked = [c for c in e.zlist("shield", 0)
              if e.s.cards[c].exlife_of is not None
              and list(e.s.cards[c].exlife_of) == list(ref)]
    assert len(e.zlist("shield", 0)) == shields0 + 2
    assert len(linked) == 2
    # 自身の常在能力で、紐付いたシールドに S・トリガーが付いている
    assert all("s_trigger" in e.chars_ro(c)["keywords"] for c in linked)
