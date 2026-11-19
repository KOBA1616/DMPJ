"""第235弾の登録形テスト: kizuna_comp 再変換5枚（ラウンド271）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build

IDS = ["dmrp04s-s05", "dmrp04s-007", "dmrp04s-001", "dmrp04s-s03", "dmrp04s-s09"]


def _game(p0, p1):
    rules = load_rules()
    return build(rules, {"p0": p0, "p1": p1, "filler": "T001", "seed": 1,
                         "deck_size": 20})


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def test_all_registered():
    e = _game({}, {})
    for cid in IDS:
        assert cid in e.rules.cards, cid


def test_s05_comp_uses_own_and_ally_partner():
    e = _game({"bz": ["dmrp04s-s05", "T638"]}, {"bz": ["T002"]})
    hand_before = len(e.zlist("hand", 0))
    plan = ["T638", "dmrp04s-s05"]      # 味方のドロー → 自分の破壊
    for _ in range(160):
        if "T002" in _defns(e, "graveyard", 1) and len(e.zlist("hand", 0)) == hand_before + 1:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and any(k.startswith("attack:dmrp04s-s05") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("attack:dmrp04s-s05"))])
        elif d["kind"] == "use_partner":
            if plan:
                want = plan.pop(0)
                e.answer([next(i for i, k in enumerate(keys) if want in k)])
            else:
                e.answer([])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert len(e.zlist("hand", 0)) == hand_before + 1
    assert "T002" in _defns(e, "graveyard", 1)
