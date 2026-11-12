"""語彙パイロット第191弾: mana_bakutan（マナ爆誕）。

「マナ爆誕N（このクリーチャーを自分のマナゾーンから、コストNを支払って召喚して
もよい）」。カード自身の能力による代替コスト召喚で、許可（summon_from_mana）の
通常コスト召喚とは別系統。

- 面フィールド `mana_bakutan: int >= 0`（0 はマナをタップせずに召喚。その場合、
  支払いに文明を含める要求も無い）。
- 選択肢はメインステップの `play:<id>:bakutan`。支払い規約は recycle（第172弾）
  と同じ cost_override 方式（固定コスト。軽減は乗らない）。進化クリーチャーは対象外。
- 「自分のマナゾーンから召喚していたら」の出た時誘発は、召喚の移動イベント
  （from: mana, reason: summon）への trigger で書ける（既存語彙）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import DefError, load_tables, parse_card

TABLES = load_tables()

IDS = ("T465", "T466", "T467", "T468")


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    assert parse_card(_proto_card("T465"), TABLES).mana_bakutan == 3
    assert parse_card(_proto_card("T466"), TABLES).mana_bakutan == 0
    assert parse_card(_proto_card("T467"), TABLES).mana_bakutan == 2
    assert parse_card(_proto_card("T468"), TABLES).mana_bakutan == 2


def test_invalid_forms():
    base = {"id": "test-mb-bad", "name": "試験爆誕不良", "types": ["creature"],
            "civs": ["nature"], "cost": 3, "power": 2000, "mana": 1,
            "source": {"official": "test-mb-bad", "review": "pending"}}
    for bad in ("3", -1, 1.5, True, {"cost": 3}, [3]):
        card = {**base, "mana_bakutan": bad}
        with pytest.raises(DefError) as e:
            parse_card(card, TABLES)
        assert "mana_bakutan" in str(e.value)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _defns(e, zone, player=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, player)]


def _drive(e, play_keys, max_steps=300):
    """決定が出るたびに方針どおりに答え、play_keys の選択肢をメイン決定で順に使い、
    使い終わってメイン／チャージ／攻撃の決定で落ち着いたら返す（第172弾と同じ）。"""
    play_keys = list(play_keys)
    played = set()
    saw_main = False
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended before settling"
        keys = _keys(d)
        kind = d["kind"]
        if kind == "main" and d["player"] == 0:
            if not saw_main:
                saw_main = True
                missing = [k for k in play_keys if k not in keys]
                assert not missing, f"main options lack {missing}: {keys}"
            nxt = next((k for k in play_keys if k not in played and k in keys), None)
            if nxt is not None:
                played.add(nxt)
                e.answer([keys.index(nxt)])
                continue
            if played or not play_keys:
                return
        if played and kind in ("charge", "attack"):
            return
        if kind == "pay_mana":
            e.answer([0])
        elif kind in ("choose_cards", "choose_shields"):
            e.answer(list(range(d["min"])))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("did not settle")


def _main_keys(e, max_steps=60):
    """最初のメイン決定（player 0）の選択肢キー一覧を返す（第172弾と同じ）。"""
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None
        if d["kind"] == "main" and d["player"] == 0:
            return _keys(d)
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("main step not reached")


def test_bakutan_summon_at_fixed_cost(rules):
    """T465（印字コスト6／爆誕3）: マナゾーンから3で召喚できる。支払いは3枚タップ。"""
    e = setup(rules, {"mana": ["T465", "T001", "T001", "T001"]}, {})
    _drive(e, ["play:T465:bakutan"])
    assert "T465" in _defns(e, "bz")
    mana = e.zlist("mana", 0)
    assert len(mana) == 3 and all(e.s.cards[c].tapped for c in mana), "コスト3を払っている"


def test_bakutan_not_offered_without_enough_mana(rules):
    """T465: 払えるマナが2枚では爆誕3の選択肢が出ない（対照）。"""
    e = setup(rules, {"hand": ["T001"], "mana": ["T465", "T001", "T001"]}, {})
    keys = _main_keys(e)
    assert "play:T001" in keys
    assert "play:T465:bakutan" not in keys


def test_bakutan_zero_cost_needs_no_mana(rules):
    """T466（爆誕0）: 他にマナが無くても選択肢が出て、タップなしで召喚できる。"""
    e = setup(rules, {"mana": ["T466"]}, {})
    keys = _main_keys(e)
    assert "play:T466:bakutan" in keys
    e2 = setup(rules, {"mana": ["T466"]}, {})
    _drive(e2, ["play:T466:bakutan"])
    assert "T466" in _defns(e2, "bz")
    assert _defns(e2, "mana") == []


def test_bakutan_needs_own_civ_in_payment(rules):
    """T468（火／爆誕2）: 自然マナだけでは文明を満たせず選択肢が出ない（対照）。
    火マナがあれば出る。"""
    e = setup(rules, {"hand": ["T001"], "mana": ["T468", "T001", "T001"]}, {})
    keys = _main_keys(e)
    assert "play:T001" in keys
    assert "play:T468:bakutan" not in keys
    e2 = setup(rules, {"mana": ["T468", "T005", "T001"]}, {})
    _drive(e2, ["play:T468:bakutan"])
    assert "T468" in _defns(e2, "bz")


def test_summoned_from_mana_trigger_draws(rules):
    """T467: マナゾーンから召喚して出た時の誘発で1枚引く。"""
    e = setup(rules, {"mana": ["T467", "T001", "T001"]}, {})
    _drive(e, ["play:T467:bakutan"])
    assert "T467" in _defns(e, "bz")
    assert len(_defns(e, "hand")) == 1, "マナから召喚したので1ドロー"


def test_summoned_from_hand_no_draw_no_bakutan(rules):
    """T467: 手札から通常召喚（コスト4）では誘発せず、爆誕の選択肢も出ない（判別）。"""
    e = setup(rules, {"hand": ["T467"], "mana": ["T001", "T001", "T001", "T001"]}, {})
    keys = _main_keys(e)
    assert "play:T467" in keys
    assert "play:T467:bakutan" not in keys
    e2 = setup(rules, {"hand": ["T467"], "mana": ["T001", "T001", "T001", "T001"]}, {})
    _drive(e2, ["play:T467"])
    assert "T467" in _defns(e2, "bz")
    assert len(_defns(e2, "hand")) == 0, "手札からの召喚では引かない"


def test_bakutan_not_offered_from_graveyard(rules):
    """T465: 墓地にある時は爆誕の選択肢が出ない（対照）。"""
    e = setup(rules, {"hand": ["T001"], "graveyard": ["T465"],
                      "mana": ["T001", "T001", "T001"]}, {})
    keys = _main_keys(e)
    assert "play:T001" in keys
    assert "play:T465:bakutan" not in keys
