"""第234弾の登録形テスト: tamaseed_evolution_cost_reduction 再変換5件（ラウンド270）。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build

IDS = ["dmrp21-10b", "dmrp22-001", "dmsd20-006", "dmrp22-069"]


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
    # promoy21-005 は dmsd20-006 の別刷りとして aliases に畳まれている
    c = e.rules.cards["dmsd20-006"]
    src = c.source if isinstance(c.source, dict) else vars(c.source)
    assert "promoy21-005" in (src.get("aliases") or [])


def test_069_grants_evo_reduce():
    e = _game({"bz": ["dmrp22-069"]}, {})
    cid = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "dmrp22-069")
    assert e.chars_ro(cid)["evo_reduce"] == 2


def test_006_attack_modal_shieldizes_opponent():
    e = _game({"bz": ["dmsd20-006"]}, {"bz": ["T002"]})
    shields_before = len(e.zlist("shield", 1))
    for _ in range(80):
        if len(e.zlist("shield", 1)) == shields_before + 1:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and any(k.startswith("attack:dmsd20-006") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("attack:dmsd20-006"))])
        elif d["kind"] == "choose_mode":
            e.answer([0])      # モード1: 相手のコスト4以下をシールド化
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert len(e.zlist("shield", 1)) == shields_before + 1
    assert "T002" in _defns(e, "shield", 1)
