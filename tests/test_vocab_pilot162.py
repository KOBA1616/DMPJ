"""語彙パイロット第162弾: extremal_power_selection（パワーが一番小さい／大きいクリーチャー）。

「パワーが一番小さい／大きいクリーチャーを選ぶ」は、セレクタの新キー
extremal: min_power / max_power で表す。候補（zone / owner / filter で絞った後）の
中で現在パワーが最小／最大のものだけが残る。同点はすべて候補に残り、どちらを
選ぶかは chooser の選択に委ねられる（dm31-046「2体以上ある場合、自分が選ぶ」、
「相手は自身の〜を1体選ぶ」は chooser: opp）。count: all なら同点のすべてが対象
（「一番大きいクリーチャーをすべて破壊する」）。
extremal はゾーン経路のセレクタ専用（ref / under_of 等とは併用不可）。
"""
from pathlib import Path

import yaml
from conftest import setup, answer

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in ("T295", "T296", "T297"):
        parse_card(_proto_card(cid), TABLES)
    t295 = parse_card(_proto_card("T295"), TABLES)
    sel = t295.abilities[0]["effect"][0]["select"]
    assert sel["extremal"] == "min_power"


def test_invalid_extremal():
    base = {"id": "test-ext-bad", "name": "試験極値獣不良", "types": ["creature"],
            "civs": ["fire"], "cost": 4, "power": 3000,
            "source": {"official": "test-ext-bad", "review": "pending"}}
    trig = {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"}, "effect": []}
    for bad_sel in ({"zone": "bz", "owner": "opp", "extremal": "min_cost", "count": 1},
                    {"ref": "self", "extremal": "min_power", "count": 1}):
        card = {**base, "abilities": [{**trig, "effect": [{"op": "destroy", "select": bad_sel}]}]}
        try:
            parse_card(card, TABLES)
            raise AssertionError(f"should have raised: {bad_sel}")
        except Exception as e:
            assert "extremal" in str(e)


def _drive(e, stop, max_steps=400):
    """stop(d) を満たす決定まで既定回答で進める。"""
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if stop(d):
            return d
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["kind"] == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("stop decision not reached")


def _cid_ctrl(e, player, defn, nth=0):
    return [c for c in e.zlist("bz", player)
            if e.s.cards[c].defn == defn and e.s.cards[c].controller == player][nth]


def _zone(e, cid):
    return e.s.cards[cid].zone


def _play_and_resolve(e, defn):
    answer(e, "charge", "pass")
    answer(e, "main", f"play:{defn}")
    _drive(e, lambda d: d["kind"] == "attack" and d["player"] == 0)


def test_min_power_unique(rules):
    """最小パワーが1体だけなら、その1体が破壊される（T295）。"""
    e = setup(rules, {"hand": ["T295"], "mana": ["T005", "T001", "T001", "T001"]},
              {"bz": ["T001", "T004", "T293"]})
    small = _cid_ctrl(e, 1, "T001")
    mid = _cid_ctrl(e, 1, "T004")
    big = _cid_ctrl(e, 1, "T293")
    _play_and_resolve(e, "T295")
    assert _zone(e, small) == "graveyard"
    assert _zone(e, mid) == "bz" and _zone(e, big) == "bz"


def test_min_power_tie_offers_only_tied(rules):
    """最小パワーが同点2体なら、選択肢はその2体だけ（大きい方は選べない）。"""
    e = setup(rules, {"hand": ["T295"], "mana": ["T005", "T001", "T001", "T001"]},
              {"bz": ["T001", "T001", "T004"]})
    tied = {_cid_ctrl(e, 1, "T001", 0), _cid_ctrl(e, 1, "T001", 1)}
    big = _cid_ctrl(e, 1, "T004")
    answer(e, "charge", "pass")
    answer(e, "main", "play:T295")
    offered = None
    for _ in range(200):
        d = e.advance()
        assert d is not None
        if d["kind"] == "choose_cards":
            offered = {o["cid"] for o in d["options"]}
            e.answer([0])
            break
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert offered == tied, offered
    _drive(e, lambda d: d["kind"] == "attack" and d["player"] == 0)
    assert sum(1 for c in tied if _zone(e, c) == "graveyard") == 1
    assert _zone(e, big) == "bz"


def test_max_power_all(rules):
    """最大パワーのすべてが破壊される（T296、count: all）。"""
    e = setup(rules, {"hand": ["T296"], "mana": ["T293", "T001", "T001", "T001", "T001"]},
              {"bz": ["T293", "T293", "T001"]})
    big1 = _cid_ctrl(e, 1, "T293", 0)
    big2 = _cid_ctrl(e, 1, "T293", 1)
    small = _cid_ctrl(e, 1, "T001")
    _play_and_resolve(e, "T296")
    assert _zone(e, big1) == "graveyard" and _zone(e, big2) == "graveyard"
    assert _zone(e, small) == "bz"


def test_min_tapped_freeze(rules):
    """タップされている中での最小を選び、次の相手ターンにアンタップさせない（T297）。"""
    e = setup(rules, {"hand": ["T297"], "mana": ["T004", "T001", "T001"]},
              {"bz": ["T001", "T005", "T293"]})
    small = _cid_ctrl(e, 1, "T001")
    mid = _cid_ctrl(e, 1, "T005")
    e.s.cards[small].tapped = True
    e.s.cards[mid].tapped = True
    answer(e, "charge", "pass")
    answer(e, "main", "play:T297")
    # CIP は候補が1体に絞られるため判断なしで解決し、そのまま相手ターンへ進む。
    # 相手のターンのはじめ: 選ばれた最小の T001 はアンタップせず、選ばれなかった
    # T005 はアンタップする（どちらが選ばれたかはこの対比で分かる）
    _drive(e, lambda d: d["player"] == 1 and d["kind"] in ("main", "attack"))
    assert e.s.cards[small].tapped is True
    assert e.s.cards[mid].tapped is False
