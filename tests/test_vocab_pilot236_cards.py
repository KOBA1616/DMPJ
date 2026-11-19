"""第236弾の登録形テスト: 超無限進化再変換（ラウンド272）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build

IDS = ["dm24ex3-or5", "dm34-001", "dm34-006", "dm34-030"]


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
    # dmartkiwami01-002 は dm24ex3-or5 の別刷りとして aliases に畳まれている
    src = e.rules.cards["dm24ex3-or5"].source
    src = src if isinstance(src, dict) else vars(src)
    assert "dmartkiwami01-002" in (src.get("aliases") or [])


def test_or5_cip_discards_all_opponent_hand():
    # デーモン・コマンド3体の上に進化 → 出た時、相手は手札をすべて捨てる
    e = _game({"bz": ["dm22ex2-061"] * 3, "hand": ["dm24ex3-or5"],
               "mana": ["T050", "T030", "T002", "T551", "T001",
                        "T050", "T030", "T002"]},
              {"hand": ["T001", "T001", "T001"]})
    opp_hand_before = len(e.zlist("hand", 1))
    assert opp_hand_before >= 3
    for _ in range(160):
        if "dm24ex3-or5" in _defns(e, "bz", 0) and len(e.zlist("hand", 1)) == 0:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:dm24ex3-or5") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:dm24ex3-or5"))])
        elif d["kind"] == "choose_evo_source":
            e.answer(list(range(d["max"])))     # 3体すべて重ねる
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "dm24ex3-or5" in _defns(e, "bz", 0)
    assert len(e.zlist("hand", 1)) == 0
