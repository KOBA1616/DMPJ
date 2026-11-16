"""語彙パイロット第168弾: フォートE（召喚時にマナの指定種族をタップしていたら能力を得る）。

フォートEは「このクリーチャーをバトルゾーンに出した時、＜種族＞を自分のマナゾーンで
タップしてこのクリーチャーを召喚していた場合、このクリーチャーは次の能力を得る」。
得る能力は、得た時点の出た時誘発（その出た時に誘発する）・常在型のどちらもあり、
1枚に2条項あるものもある。実装は O・ドライブ（第47弾）と同じ作法:

- 召喚時の支払い（通常支払い＋バズレンダ追加＋O・ドライブ追加タップ）でタップした
  マナを Card.summon_tapped に種族のスナップショットつきで刻む（ハイパーエナジーで
  タップしたバトルゾーンのクリーチャーはマナではないので含めない）。ゾーン移動で消え、
  移動イベントに載せて出し直す（odrive と同じ）。
- 能力フラグ fort_e: {races: [...], as?: 変数名} を core.abilities() でゲートする。
  「タップした〜のいずれかよりパワーが小さい」は、as で束ねたタップ済みマナに
  power_of（複数参照で最大値）を当て、power_le: {sum: [power_of, -1]} で書く。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()

IDS = ("T324", "T325", "T326", "T327", "T328", "T329", "T330", "T331", "T332")


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)
    assert _proto_card("T324")["abilities"][0]["fort_e"] == {"races": ["ドラゴン"]}
    assert _proto_card("T325")["abilities"][0]["fort_e"] == {"races": ["ドラゴン"]}
    assert _proto_card("T326")["abilities"][0]["fort_e"] == {"races": ["ドラゴン"], "as": "tapped"}
    assert _proto_card("T327")["abilities"][1]["fort_e"] == {"races": ["ヒューマノイド"]}
    assert _proto_card("T328")["abilities"][0]["fort_e"] == {"races": ["ドラゴン"]}


def test_fort_e_rejects_bad_forms():
    base = {"id": "TX", "name": "x", "types": ["creature"], "civs": ["fire"], "cost": 2,
            "power": 2000, "races": ["テスト"], "text": "x",
            "abilities": [{"kind": "trigger", "when": {"event": "move", "subject": "self", "to": "bz"},
                           "fort_e": {"races": ["ドラゴン"]}, "effect": [{"op": "draw", "player": "you", "count": 1}]}]}
    parse_card(base, TABLES)
    for bad in (True, {"races": []}, {"races": "ドラゴン"}, {"races": [123]},
                {"races": ["ドラゴン"], "as": 1}, {"races": ["ドラゴン"], "other": 1}):
        bad_card = dict(base)
        bad_card["abilities"] = [dict(base["abilities"][0], fort_e=bad)]
        with pytest.raises(DefError):
            parse_card(bad_card, TABLES)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _play(e, tid, max_steps=200):
    """メインで tid を実行し、解決が落ち着くまで進める。"""
    chosen = False
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None
        keys = _keys(d)
        if d["kind"] == "main" and d["player"] == 0 and not chosen:
            if f"play:{tid}" in keys:
                chosen = True
                e.answer([keys.index(f"play:{tid}")])
                continue
        if chosen and d["kind"] in ("charge", "main", "attack"):
            return
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")] if "no" in keys else [0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("play did not settle")


def _play_then_attack_options(e, tid, max_steps=200):
    """手札の tid を召喚してから攻撃ステップの選択肢を返す。"""
    played = False
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None
        keys = _keys(d)
        if d["kind"] == "attack" and d["player"] == 0:
            assert played
            return keys
        if d["kind"] == "main" and d["player"] == 0 and not played and f"play:{tid}" in keys:
            played = True
            e.answer([keys.index(f"play:{tid}")])
            continue
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")] if "no" in keys else [0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
    raise AssertionError("attack step not reached")


def _hand(e, player=0):
    return e.zlist("hand", player)


def _opp_bz_defns(e):
    return [e.s.cards[c].defn for c in e.bz_tops(1)]


def test_fort_e_trigger_draws_only_with_dragon_mana(rules):
    """T324: ドラゴンをタップして召喚→出た時ドロー。ドラゴン以外だけ→引かない。"""
    e = setup(rules, {"hand": ["T324"], "mana": ["T329", "T330"]}, {})
    _play(e, "T324")
    assert len(_hand(e)) == 1  # 召喚で手札0→得た誘発で1枚引く
    e = setup(rules, {"hand": ["T324"], "mana": ["T331", "T331"]}, {})
    _play(e, "T324")
    assert len(_hand(e)) == 0


def test_fort_e_static_grants_speed_attacker_only_with_dragon_mana(rules):
    """T325: ドラゴンをタップして召喚→そのターン攻撃できる。ドラゴン以外だけ→召喚酔い。"""
    e = setup(rules, {"bz": ["T005"], "hand": ["T325"], "mana": ["T329", "T330"]}, {})
    keys = _play_then_attack_options(e, "T325")
    assert "attack:T325:player" in keys
    e = setup(rules, {"bz": ["T005"], "hand": ["T325"], "mana": ["T331", "T331"]}, {})
    keys = _play_then_attack_options(e, "T325")
    assert "attack:T325:player" not in keys
    assert "attack:T005:player" in keys


def test_fort_e_as_binding_uses_max_power(rules):
    """T326: タップしたドラゴン（3000と5000）のいずれかより小さい＝5000未満を破壊する。

    相手3000は最小値3000より小さくないが最大値5000より小さいので、破壊できれば
    最大値で見ていることの判別になる。相手5000は最大値と同値なので破壊できない。
    """
    e = setup(rules, {"hand": ["T326"], "mana": ["T329", "T330"]}, {"bz": ["T329"]})
    _play(e, "T326")
    assert "T329" not in _opp_bz_defns(e)  # 相手の3000が破壊された
    e = setup(rules, {"hand": ["T326"], "mana": ["T329", "T330"]}, {"bz": ["T330"]})
    _play(e, "T326")
    assert "T330" in _opp_bz_defns(e)  # 相手の5000は残る
    e = setup(rules, {"hand": ["T326"], "mana": ["T331", "T331"]}, {"bz": ["T329"]})
    _play(e, "T326")
    assert "T329" in _opp_bz_defns(e)  # ドラゴンをタップしていなければ誘発自体が出ない


def test_fort_e_two_clauses_are_independent(rules):
    """T327: ドラゴン条項（ドロー）とヒューマノイド条項（破壊）は別々に判定される。"""
    # ドラゴンだけ→ドローのみ（相手の2000は残る）
    e = setup(rules, {"hand": ["T327"], "mana": ["T329", "T330"]}, {"bz": ["T331"]})
    _play(e, "T327")
    assert len(_hand(e)) == 1
    assert "T331" in _opp_bz_defns(e)
    # ヒューマノイドだけ→破壊のみ（引かない）
    e = setup(rules, {"hand": ["T327"], "mana": ["T332", "T332"]}, {"bz": ["T331"]})
    _play(e, "T327")
    assert len(_hand(e)) == 0
    assert "T331" not in _opp_bz_defns(e)
    # 両方→両方とも発火する
    e = setup(rules, {"hand": ["T327"], "mana": ["T329", "T332"]}, {"bz": ["T331"]})
    _play(e, "T327")
    assert len(_hand(e)) == 1
    assert "T331" not in _opp_bz_defns(e)


def test_fort_e_evolution_summon(rules):
    """T328: 進化召喚でも、ドラゴンをタップして召喚すれば出た時ドローが得られる。"""
    e = setup(rules, {"bz": ["T331"], "hand": ["T328"], "mana": ["T329", "T330", "T331"]}, {})
    _play(e, "T328")
    assert len(_hand(e)) == 1
    assert any(e.s.cards[c].defn == "T328" for c in e.bz_tops(0))
    e = setup(rules, {"bz": ["T331"], "hand": ["T328"], "mana": ["T331", "T331", "T331"]}, {})
    _play(e, "T328")
    assert len(_hand(e)) == 0


def test_fort_e_record_cleared_on_leaving_bz(rules):
    """召喚時の記録はゾーン移動で消える（_raw_move のクリア。odrive と同じ作法）。"""
    e = setup(rules, {"hand": ["T324"], "mana": ["T329", "T330"]}, {})
    _play(e, "T324")
    cid = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T324")
    assert e.s.cards[cid].summon_tapped  # 出た直後は記録がある
    assert e.s.cards[cid].zone == "bz"
    e._raw_move(cid, "hand")
    assert e.s.cards[cid].summon_tapped == []
    assert e.s.cards[cid].zone == "hand"
