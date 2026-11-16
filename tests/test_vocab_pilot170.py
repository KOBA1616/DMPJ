"""語彙パイロット第170弾: crossed_state（クロスギアがクロスされている状態）。

クロスギア本体の仕組み（crossed 参照・affects: crossed・303.3）は第22弾で
既にある。本弾は「クロスされている状態」を条件・数え・選択で扱う語彙:
- フィルタ crossed（ギアがクロスされているか）/ crossed_ge / crossed_le /
  crossed_name（その名前のギアがクロスされているか）
- セレクタ crossed_to（そのクリーチャーにクロスされているギア）/
  host_of（そのギアをクロスしているクリーチャー）
- 式 {crossed_count: <ref>}（クロスされていたギアの数。破壊された時の LKI 参照にも当たる）
- 式の参照名 crossed（このギアをクロスしているクリーチャー。cost_of / power_of / races_of 用）
- mod breaks_add の辞書形 {amount, count}（ギア1枚につき、さらに1枚ブレイクする）
- 新 op uncross（クロスを外す。ギアはバトルゾーンに残る）
- 起動コスト {tap: {ref: crossed}}（このギアをクロスしているクリーチャーをタップする）
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()

IDS = tuple(f"T{n}" for n in range(341, 357))


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)
    assert _proto_card("T341")["abilities"][0]["mod"] == {"deny": ["attack_player"]}
    assert _proto_card("T343")["abilities"][0]["mod"] == {"power": {"amount": 1000, "count": {"crossed_to": "self"}}}
    assert _proto_card("T356")["abilities"][0]["mod"] == {"breaks_add": {"amount": 1, "count": {"crossed_to": "self"}}}
    assert _proto_card("T348")["free_if"] == {"exists": {"zone": "bz", "owner": "any", "filter": {"crossed": True}}}
    assert _proto_card("T354")["abilities"][0]["cost"] == {"tap": {"ref": "crossed"}}


def test_bad_forms_rejected():
    base = _proto_card("T341")
    bad = dict(base)
    bad["abilities"] = [dict(base["abilities"][0], **{"if": {"exists": {"ref": "self", "filter": {"crossed": "yes"}}}})]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad = dict(base)
    bad["abilities"] = [dict(base["abilities"][0], **{"if": {"exists": {"ref": "self", "filter": {"crossed_name": 5}}}})]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    t353 = _proto_card("T353")
    bad = dict(t353)
    bad["abilities"] = [dict(t353["abilities"][0],
                             effect=[{"op": "draw", "count": {"crossed_count": {"ref": 1}}}])]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    t351 = _proto_card("T351")
    bad = dict(t351)
    bad["abilities"] = [dict(t351["abilities"][0], effect=[{"op": "uncross"}])]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    t356 = _proto_card("T356")
    bad = dict(t356)
    bad["abilities"] = [dict(t356["abilities"][0], mod={"breaks_add": {"amount": "1", "count": {"crossed_to": "self"}}})]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _cross(e, gear_defn, host_defn, player=0):
    """gear_defn のギアを host_defn のクリーチャーにクロスさせる（直接の紐付け）。"""
    e.s.cards[_bz(e, player, gear_defn)].crossed = e.s.ref(_bz(e, player, host_defn))


def _drive(e, play=None, yes_no="yes", max_steps=300):
    """決定が出るたびに方針どおりに答え、メイン／チャージ／攻撃の決定で落ち着いたら返す。"""
    play = list(play or [])
    played = set()
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended before settling"
        keys = _keys(d)
        kind = d["kind"]
        if kind == "main" and d["player"] == 0:
            nxt = next((t for t in play if t not in played
                        and any(k == f"play:{t}" or k.startswith(f"play:{t}:") for k in keys)), None)
            if nxt is not None:
                played.add(nxt)
                e.answer([next(i for i, k in enumerate(keys)
                              if k == f"play:{nxt}" or k.startswith(f"play:{nxt}:"))])
                continue
            if played or not play:
                return
        if played and kind in ("charge", "attack"):
            return
        if kind == "pay_mana":
            e.answer([0])
        elif kind in ("choose_cards", "choose_shields"):
            e.answer(list(range(d["min"])))
        elif kind == "choose_replacement":
            e.answer([0])
        elif kind == "yes_no":
            e.answer([keys.index(yes_no)])
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("did not settle")


def _to_attack(e):
    d = e.advance()
    while d["kind"] in ("charge", "main"):
        e.answer([_keys(d).index("pass")])
        d = e.advance()
    assert d["kind"] == "attack", d["kind"]
    return d


def _settle(e, max_steps=120):
    """yes_no には yes で答え、それ以外は [0] で答えて、charge / main / attack まで進める。"""
    for _ in range(max_steps):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main", "attack"):
            return d
        if d["kind"] == "yes_no":
            e.answer([_keys(d).index("yes")])
        else:
            e.answer([0])
    raise AssertionError("did not settle")


def test_no_gear_cannot_attack_player(rules):
    """T341: ギアが無ければプレイヤーを攻撃できない。ギアをクロスすれば攻撃できる。"""
    e = setup(rules, {"bz": ["T341"]}, {"bz": ["T001"]})
    e.s.cards[_bz(e, 0, "T341")].entered_turn = -1
    assert "attack:T341:player" not in [o["key"] for o in e._attack_options(0)]
    e = setup(rules, {"bz": ["T341", "T343"]}, {"bz": ["T001"]})
    e.s.cards[_bz(e, 0, "T341")].entered_turn = -1
    _cross(e, "T343", "T341")
    assert "attack:T341:player" in [o["key"] for o in e._attack_options(0)]


def test_tapped_source_grants_extra_break(rules):
    """T342: 自分がタップされている時だけ、クロスしている自分のクリーチャーがさらに1枚ブレイクする。"""
    e = setup(rules, {"bz": ["T001", "T342", "T343"]}, {})
    _cross(e, "T343", "T001")
    assert e.chars(_bz(e, 0, "T001"))["breaks"] == 1
    e.s.cards[_bz(e, 0, "T342")].tapped = True
    assert e.chars(_bz(e, 0, "T001"))["breaks"] == 2
    assert e.chars(_bz(e, 0, "T342"))["breaks"] == 1  # T342 自身はクロスされていないので対象外


def test_power_per_crossed_gear(rules):
    """T343: クロスしたクリーチャーのパワーは、クロスされているギア1枚につき+1000。"""
    e = setup(rules, {"bz": ["T001", "T343", "T349"]}, {})
    c = _bz(e, 0, "T001")
    assert e.chars(c)["power"] == 2000
    _cross(e, "T343", "T001")
    assert e.chars(c)["power"] == 3000  # T343 の +1000（T349 はまだクロスされていないので +1000 は無い）
    _cross(e, "T349", "T001")
    assert e.chars(c)["power"] == 5000  # T343 が2枚分 +2000、T349 が同種族へ +1000


def test_named_gear_pair_bonus(rules):
    """T344/T345: もう一方の名前のギアもクロスされていれば、追加のボーナスが付く。"""
    e = setup(rules, {"bz": ["T001", "T344"]}, {"bz": ["T001"]})
    _cross(e, "T344", "T001")
    c = _bz(e, 0, "T001")
    assert e.chars(c)["power"] == 6000 and "blocker" in e.chars(c)["keywords"]
    assert e.chars(c)["breaks"] == 1
    e = setup(rules, {"bz": ["T001", "T344", "T345"]}, {"bz": ["T001"]})
    _cross(e, "T344", "T001")
    _cross(e, "T345", "T001")
    c = _bz(e, 0, "T001")
    assert e.chars(c)["power"] == 14000  # +4000 +8000
    assert "double_breaker" in e.chars(c)["keywords"]
    assert e.chars(c)["breaks"] == 4  # W・ブレイカー2 + さらに2枚
    blocker = _bz(e, 1, "T001")
    assert e.permits(c, "be_blocked", blocker) is False  # 自分よりパワーが小さいクリーチャーにブロックされない
    e = setup(rules, {"bz": ["T001", "T344"]}, {"bz": ["T001"]})
    _cross(e, "T344", "T001")
    assert e.permits(_bz(e, 0, "T001"), "be_blocked", _bz(e, 1, "T001")) is True  # T345 が無ければブロックできる


def test_spell_destroys_crossed_creatures(rules):
    """T346: クロスギアをクロスしているクリーチャーだけをすべて破壊する。"""
    e = setup(rules, {"bz": ["T001", "T339", "T343"], "hand": ["T346"],
                     "mana": ["T354"] * 5}, {})
    _cross(e, "T343", "T001")
    _drive(e, play=["T346"])
    assert "T001" in [e.s.cards[c].defn for c in e.zlist("graveyard", 0)]
    assert "T339" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    assert "T343" in [e.s.cards[c].defn for c in e.bz_tops(0)]  # ギアはバトルゾーンに残る


def test_spell_moves_creature_and_gears_to_mana(rules):
    """T347: 相手のクリーチャーとそれにクロスされているギアをすべて持ち主のマナゾーンに置く。"""
    e = setup(rules, {"hand": ["T347"], "mana": ["T001"] * 6},
              {"bz": ["T001", "T343", "T349"]})
    _cross(e, "T343", "T001", player=1)
    _cross(e, "T349", "T001", player=1)
    _drive(e, play=["T347"])
    assert "T001" in [e.s.cards[c].defn for c in e.zlist("mana", 1)]
    assert "T343" in [e.s.cards[c].defn for c in e.zlist("mana", 1)]
    assert "T349" in [e.s.cards[c].defn for c in e.zlist("mana", 1)]


def test_g_zero_free_if_crossed_exists(rules):
    """T348: クロスしているクリーチャーがいれば無料召喚でき、クロスしているクリーチャー全て+1000。"""
    e = setup(rules, {"bz": ["T001", "T343"], "hand": ["T348"]}, {})
    _cross(e, "T343", "T001")
    _drive(e, play=["T348"])
    assert "T348" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    assert e.chars(_bz(e, 0, "T001"))["power"] == 4000  # T343 の +1000 と T348 の +1000
    # マナが無く無料条件も無ければ、出せる選択肢にそもそも出ない（main 自体が自動スキップされるため直接照会する）
    e = setup(rules, {"hand": ["T348"]}, {})
    assert "play:T348:free" not in [o["key"] for o in e._play_options(0)]
    assert "play:T348" not in [o["key"] for o in e._play_options(0)]


def test_same_race_bonus_and_attack_draw(rules):
    """T349: クロスしたクリーチャーと同じ種族のクリーチャー全て+1000。その種族が攻撃する時1枚引く。"""
    e = setup(rules, {"bz": ["T001", "T001", "T349"]}, {})
    _cross(e, "T349", "T001")
    tops = e.bz_tops(0)
    assert all(e.chars(c)["power"] == 3000 for c in tops if e.s.cards[c].defn == "T001")
    # 同種族（テスト）の攻撃でドローする
    e = setup(rules, {"bz": ["T001", "T001", "T349"], "hand": ["T001"]}, {})
    _cross(e, "T349", "T001")
    for c in e.bz_tops(0):
        if e.s.cards[c].defn == "T001":
            e.s.cards[c].entered_turn = -1
    hand_before = len(e.zlist("hand", 0))
    d = _to_attack(e)
    keys = _keys(d)
    atk = next(k for k in keys if k.startswith("attack:T001:player"))
    e.answer([keys.index(atk)])
    _settle(e)
    assert len(e.zlist("hand", 0)) == hand_before + 1
    # 別種族（メタリカ）の攻撃では引けない
    e = setup(rules, {"bz": ["T001", "T339", "T349"], "hand": ["T001"]}, {})
    _cross(e, "T349", "T001")
    e.s.cards[_bz(e, 0, "T339")].entered_turn = -1
    hand_before = len(e.zlist("hand", 0))
    d = _to_attack(e)
    keys = _keys(d)
    atk = next(k for k in keys if k.startswith("attack:T339:player"))
    e.answer([keys.index(atk)])
    _settle(e)
    assert len(e.zlist("hand", 0)) == hand_before


def test_can_attack_untapped_crossed_creature(rules):
    """T350: クロスギアをクロスされたタップされていないクリーチャーを攻撃できる。"""
    e = setup(rules, {"bz": ["T350"]}, {"bz": ["T001", "T339", "T343"]})
    e.s.cards[_bz(e, 0, "T350")].entered_turn = -1
    _cross(e, "T343", "T001", player=1)
    opts = e._attack_options(0)
    assert "attack:T350:T001" in [o["key"] for o in opts]
    assert "attack:T350:T339" not in [o["key"] for o in opts]  # クロスされていないタップ無しは攻撃できない


def test_cip_uncrosses_all_gears(rules):
    """T351: 出た時、クロスしてあるギアをすべて外す。ギアはバトルゾーンに残る。"""
    e = setup(rules, {"bz": ["T001", "T343", "T349"], "hand": ["T351"],
                     "mana": ["T354"] * 5}, {})
    _cross(e, "T343", "T001")
    _cross(e, "T349", "T001")
    _drive(e, play=["T351"])
    assert e.s.cards[_bz(e, 0, "T343")].crossed is None
    assert e.s.cards[_bz(e, 0, "T349")].crossed is None
    assert "T343" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    assert e.chars(_bz(e, 0, "T001"))["power"] == 2000  # ボーナスが消えている


def test_no_leave_with_four_gears(rules):
    """T352: ギアが4つ以上クロスされていれば離れない。3つでは離れる。"""
    e = setup(rules, {"bz": ["T352", "T343", "T344", "T345", "T349"]}, {})
    for g in ("T343", "T344", "T345", "T349"):
        _cross(e, g, "T352")
    c = _bz(e, 0, "T352")
    e._push(e.ev_task({"ev": "move", "subject": e.s.ref(c), "to": "graveyard", "reason": "destroy"}))
    e.advance()
    assert e.s.cards[c].zone == "bz"
    e = setup(rules, {"bz": ["T352", "T343", "T344", "T345"]}, {})
    for g in ("T343", "T344", "T345"):
        _cross(e, g, "T352")
    c = _bz(e, 0, "T352")
    e._push(e.ev_task({"ev": "move", "subject": e.s.ref(c), "to": "graveyard", "reason": "destroy"}))
    e.advance()
    assert e.s.cards[c].zone == "graveyard"


def _destroy_and_answer_may(e, c):
    e._push(e.ev_task({"ev": "move", "subject": e.s.ref(c), "to": "graveyard", "reason": "destroy"}))
    for _ in range(60):
        d = e.advance()
        if d is None:
            break
        if d["kind"] == "yes_no":
            e.answer([_keys(d).index("yes")])
            continue
        if d["kind"] in ("charge", "main", "attack"):
            break
        e.answer([0])


def test_destroy_draws_crossed_count(rules):
    """T353: 破壊された時、クロスされていたギアの数と同じ枚数引く。"""
    e = setup(rules, {"bz": ["T353", "T343", "T349"], "hand": ["T001"]}, {})
    _cross(e, "T343", "T353")
    _cross(e, "T349", "T353")
    hand_before = len(e.zlist("hand", 0))
    _destroy_and_answer_may(e, _bz(e, 0, "T353"))
    assert len(e.zlist("hand", 0)) == hand_before + 2
    e = setup(rules, {"bz": ["T353"], "hand": ["T001"]}, {})
    hand_before = len(e.zlist("hand", 0))
    _destroy_and_answer_may(e, _bz(e, 0, "T353"))
    assert len(e.zlist("hand", 0)) == hand_before  # ギア0枚なら0枚


def test_activate_taps_crossed_creature(rules):
    """T354: クロスしたクリーチャーをタップして起動し、そのパワー以下のクリーチャーをすべて破壊する。
    起動コストはクロスしたクリーチャーのタップ（タップ済み・クロス無しでは選択肢が出ない）。"""
    e = setup(rules, {"bz": ["T001", "T354"]}, {"bz": ["T001", "T350"]})
    _cross(e, "T354", "T001")
    e.s.cards[_bz(e, 0, "T001")].entered_turn = -1
    d = _to_attack(e)
    keys = _keys(d)
    act = next(k for k in keys if k.startswith("activate:T354"))
    e.answer([keys.index(act)])
    _settle(e)
    assert "T001" in [e.s.cards[c].defn for c in e.zlist("graveyard", 0)]  # クロスした自身もパワー2000以下で破壊
    assert "T001" in [e.s.cards[c].defn for c in e.zlist("graveyard", 1)]
    assert "T350" in [e.s.cards[c].defn for c in e.bz_tops(1)]  # パワー6000は残る
    # クロスしたクリーチャーが攻撃できない（召喚酔い）と起動選択肢が出ない（攻撃できることがコストの前提）
    e = setup(rules, {"bz": ["T001", "T354"]}, {"bz": ["T001"]})
    _cross(e, "T354", "T001")
    e.s.cards[_bz(e, 0, "T001")].entered_turn = e.s.turn
    d = _to_attack(e)
    assert not any(k.startswith("activate:T354") for k in _keys(d))
    # クロスしていないと起動選択肢が出ない
    e = setup(rules, {"bz": ["T001", "T354"]}, {"bz": ["T001"]})
    e.s.cards[_bz(e, 0, "T001")].entered_turn = -1
    d = _to_attack(e)
    assert not any(k.startswith("activate:T354") for k in _keys(d))


def test_spell_removes_gear_and_maybe_host(rules):
    """T355: 相手のギアを墓地に置き、それをクロスしていたクリーチャーがパワー2000以下なら破壊する。"""
    e = setup(rules, {"hand": ["T355"], "mana": ["T341"] * 4},
              {"bz": ["T001", "T343"]})
    _cross(e, "T343", "T001", player=1)
    _drive(e, play=["T355"])
    assert "T343" in [e.s.cards[c].defn for c in e.zlist("graveyard", 1)]
    assert "T001" in [e.s.cards[c].defn for c in e.zlist("graveyard", 1)]
    e = setup(rules, {"hand": ["T355"], "mana": ["T341"] * 4},
              {"bz": ["T350", "T343"]})
    _cross(e, "T343", "T350", player=1)
    _drive(e, play=["T355"])
    assert "T343" in [e.s.cards[c].defn for c in e.zlist("graveyard", 1)]
    assert "T350" in [e.s.cards[c].defn for c in e.bz_tops(1)]  # パワー6000は残る


def test_breaks_add_per_gear(rules):
    """T356: クロスされたギア1枚につき、さらに1枚ブレイクする。"""
    e = setup(rules, {"bz": ["T356", "T343", "T349"]}, {})
    c = _bz(e, 0, "T356")
    assert e.chars(c)["breaks"] == 1
    _cross(e, "T343", "T356")
    assert e.chars(c)["breaks"] == 2
    _cross(e, "T349", "T356")
    assert e.chars(c)["breaks"] == 3
