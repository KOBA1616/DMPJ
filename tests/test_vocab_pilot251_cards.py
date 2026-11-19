"""第251弾の登録形: attack_cancel 4件 + エイリアス1件（ラウンド285）。"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card
from dmsim.scenario import build

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)


def _converted(cid):
    import yaml
    for c in yaml.safe_load(open(CONVERTED))["cards"]:
        if c["id"] == cid:
            return c
    raise KeyError(cid)


def test_registered_forms():
    for cid in ("dmd03-005", "dmsd01-010", "dm26ex4-010", "dmrp12-078"):
        parse_card(copy.deepcopy(_converted(cid)), TABLES)
    c10 = _converted("dm26ex4-010")
    assert "dm26ex4-sec007" in (c10["source"].get("aliases") or [])

    def _has_op(x, name):
        if isinstance(x, dict):
            return x.get("op") == name or any(_has_op(v, name) for v in x.values())
        if isinstance(x, list):
            return any(_has_op(v, name) for v in x)
        return False

    trig = [a for a in c10["abilities"] if a["kind"] == "trigger" and _has_op(a.get("effect"), "cancel_attack")]
    assert trig and trig[0].get("once_per_turn") is True


def _cid(e, defn, player):
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def test_registered_shinobi_cancels():
    rules = load_rules()
    e = build(rules, {"p0": {"bz": ["T002"]},
                      "p1": {"bz": ["dm26ex4-010"], "hand": ["T001"], "deck": ["T001"] * 12},
                      "filler": "T001", "seed": 1, "deck_size": 20})
    atk = _cid(e, "T002", 0)
    sh0 = len(e.zlist("shield", 1))
    for _ in range(400):
        if e.s.cards[atk].tapped and len(e.zlist("graveyard", 1)) == 1:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        a = next((i for i, k in enumerate(keys) if k.startswith("attack:")), None)
        if a is not None:
            e.answer([a])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert len(e.zlist("graveyard", 1)) == 1         # 手札を捨てた
    assert len(e.zlist("shield", 1)) == sh0          # 攻撃は中止され、ブレイクなし


def test_registered_jtornado_decline_cancels():
    rules = load_rules()
    e = build(rules, {"p0": {"bz": ["dmrp12-078", "dmsd01-010"]},
                      "p1": {"deck": ["T001"] * 12},
                      "filler": "T001", "seed": 1, "deck_size": 20})
    sh0 = len(e.zlist("shield", 1))
    atk = _cid(e, "dmrp12-078", 0)
    for _ in range(400):
        if e.s.cards[atk].tapped:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        a = next((i for i, k in enumerate(keys) if k.startswith("attack:dmrp12-078")), None)
        if a is not None:
            e.answer([a])
        elif d["kind"] == "yes_no":
            e.answer([1])                            # Jトルネードしない
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    # 攻撃は宣言された（タップ）が、中止されてブレイクは起きていない。
    # シールド枚数はこの後も変わらないことを数ステップ確認する
    for _ in range(60):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif d["kind"] == "yes_no":
            e.answer([1])
        else:
            e.answer(list(range(d.get("min", 0))))
        if e.s.turn > 1:
            break
    assert len(e.zlist("shield", 1)) == sh0
