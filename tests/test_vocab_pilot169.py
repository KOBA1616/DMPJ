"""語彙パイロット第169弾: サバキZ（裁きの紋章）。

裁きの紋章＝シールドの上に表向きに置かれたカード。紋章が自分のシールドゾーンから
手札に加えられた時、手札のサバキZカードはその紋章を捨てて無料で出せる。
- 判定は移動レコードの emblem: true（トップは face_up＋下あり、下のカードは自身の
  face_up）。単独の表向きシールドは紋章ではない。
- 誘発は zone: hand の trigger。other: true で紋章が自身の場合を除く。
  解決時に {ref: event.subject, zone: hand} がまだ手札にあることを確認してから
  may → discard → play_free。
- 呪文は唱えた後、墓地に置くかわりに自分のシールド1つの上に表向きに置く
  （replace、zone: hand。シールドが無ければ置換せず墓地へ）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()

IDS = ("T333", "T334", "T335", "T336", "T337", "T338", "T339", "T340")


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)
    assert _proto_card("T333")["abilities"][0]["when"]["emblem"] is True
    assert _proto_card("T334")["abilities"][0]["when"]["subject"] == {"owner": "you", "other": True}
    assert _proto_card("T333")["abilities"][1]["kind"] == "replace"
    assert _proto_card("T338")["abilities"][0]["mod"] == {"indestructible": True}


def test_emblem_rejects_bad_forms():
    base = _proto_card("T334")
    for bad in ("yes", 1, "true"):
        bad_card = dict(base)
        bad_card["abilities"] = [dict(base["abilities"][0], when=dict(base["abilities"][0]["when"], emblem=bad))]
        with pytest.raises(DefError):
            parse_card(bad_card, TABLES)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _drive(e, play=None, yes_no="yes", max_steps=300):
    """決定が出るたびに方針どおりに答え、メイン／チャージ／攻撃の決定で落ち着いたら返す。

    play: 手札から実行するカード id の列（メイン決定で順に実行する）。
    """
    play = list(play or [])
    played = set()
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended before settling"
        keys = _keys(d)
        kind = d["kind"]
        if kind == "main" and d["player"] == 0:
            nxt = next((t for t in play if t not in played and f"play:{t}" in keys), None)
            if nxt is not None:
                played.add(nxt)
                e.answer([keys.index(f"play:{nxt}")])
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


def _defns(e, zone, player=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, player)]


def _stack_emblem(e, player, emblem_defn):
    """手札の emblem_defn をシールドのトップに表向きで重ねる（エンジンの shield_stack と同じ構造:
    紋章が新しいトップになり、旧トップとその下が紋章の下に入る）。(新しいトップ, 紋章) を返す。"""
    hand = e.zlist("hand", player)
    emb = next(c for c in hand if e.s.cards[c].defn == emblem_defn)
    lst = e.zlist("shield", player)
    top = lst[0]
    e.zlist("hand", player).remove(emb)
    lst[lst.index(top)] = emb
    c = e.s.cards[emb]
    c.zone = "shield"
    c.face_up = True
    c.top_of = -1
    c.under = [top] + list(e.s.cards[top].under)
    e.s.cards[top].top_of = emb
    e.s.cards[top].under = []
    for u in c.under[1:]:
        e.s.cards[u].top_of = emb
    return emb, emb


def _shield_top(e, player=0):
    return e.zlist("shield", player)[0]


def test_spell_goes_face_up_on_shield_after_cast(rules):
    """T333: 唱えた後、墓地ではなく自分のシールド1つの上に表向きに置かれる。"""
    e = setup(rules, {"hand": ["T333"], "mana": ["T030", "T030"]}, {})
    _drive(e, play=["T333"])
    assert "T333" not in _defns(e, "graveyard")
    top = _shield_top(e)
    assert e.s.cards[top].defn == "T333"
    assert e.s.cards[top].face_up is True
    assert e.s.cards[top].under  # 旧シールドが下にある＝束の上
    assert len(_defns(e, "hand")) == 1  # ドロー1枚


def test_spell_goes_to_graveyard_without_shields(rules):
    """T333: シールドが無ければ置換せず、墓地へ行く。"""
    e = setup(rules, {"hand": ["T333"], "mana": ["T030", "T030"], "shield": []}, {})
    _drive(e, play=["T333"])
    assert "T333" in _defns(e, "graveyard")


def test_sabaki_creature_summons_free(rules):
    """T334: 紋章が手札に入ると、紋章を捨てて無料召喚できる。"""
    e = setup(rules, {"hand": ["T334", "T335", "T336"], "mana": ["T030"]}, {})
    _stack_emblem(e, 0, "T335")
    _drive(e, play=["T336"])
    assert "T335" in _defns(e, "graveyard")  # 紋章を捨てた
    assert "T334" in [e.s.cards[c].defn for c in e.bz_tops(0)]  # 無料召喚された
    assert len(e.zlist("mana", 0)) == 1  # マナ1枚ではコスト3は払えない＝無料だった証拠


def test_sabaki_declined_keeps_cards(rules):
    """T334: 断れば、紋章もサバキZも手札に残る。"""
    e = setup(rules, {"hand": ["T334", "T335", "T336"], "mana": ["T030"]}, {})
    _stack_emblem(e, 0, "T335")
    _drive(e, play=["T336"], yes_no="no")
    assert "T334" in _defns(e, "hand")
    assert "T335" in _defns(e, "hand")
    assert "T334" not in [e.s.cards[c].defn for c in e.bz_tops(0)]


def test_sabaki_self_emblem_does_not_trigger(rules):
    """紋章がサバキZカード自身なら誘発しない（other: true）。yes と答えても捨てられない。"""
    e = setup(rules, {"hand": ["T334", "T336"], "mana": ["T030"]}, {})
    _stack_emblem(e, 0, "T334")
    _drive(e, play=["T336"], yes_no="yes")
    assert "T334" in _defns(e, "hand")
    assert "T334" not in _defns(e, "graveyard")
    assert "T334" not in [e.s.cards[c].defn for c in e.bz_tops(0)]


def test_sabaki_spell_casts_free(rules):
    """T333: 紋章が手札に入ると、紋章を捨てて呪文を無料で唱えられる（ドローする）。"""
    e = setup(rules, {"hand": ["T333", "T335", "T336"], "mana": ["T030"]}, {})
    _stack_emblem(e, 0, "T335")
    hand_before = len(_defns(e, "hand"))
    _drive(e, play=["T336"])
    assert "T335" in _defns(e, "graveyard")
    # T333 は唱えられてシールドの上へ（置換）。手札は T336 使用 -1、束 +2（T001＋T335）、
    # T335 捨て -1、T333 唱え -1、ドロー +1 で、差し引き手札は変わらない
    top = _shield_top(e)
    assert e.s.cards[top].defn == "T333"
    assert e.s.cards[top].face_up is True
    assert len(_defns(e, "hand")) == hand_before


def test_cip_puts_deck_top_face_up_on_shield(rules):
    """T337: 出た時、山札の上から1枚目を自分のシールド1つの上に表向きにして置く。"""
    e = setup(rules, {"hand": ["T337"], "mana": ["T030", "T030", "T030"]}, {})
    deck_before = len(e.zlist("deck", 0))
    _drive(e, play=["T337"])
    assert len(e.zlist("deck", 0)) == deck_before - 1
    tops = e.zlist("shield", 0)
    assert any(e.s.cards[t].face_up and e.s.cards[t].under for t in tops)


def test_break_replace_flips_face_up_cards(rules):
    """T338: 表向きカードを含むシールドがブレイクされる時、かわりに表向きカードを裏返す。"""
    e = setup(rules, {"hand": ["T340"], "mana": ["T005"]},
              {"bz": ["T338"], "hand": ["T335"]})
    top, emb = _stack_emblem(e, 1, "T335")
    hand_before = len(_defns(e, "hand", 1))
    _drive(e, play=["T340"])
    # シールドは残り、紋章は裏返った。手札は増えていない（ブレイクされていない。
    # hand_before + 1 は _drive が相手ターンのチャージまで進む間のドロー1枚分）
    assert e.s.cards[top].zone == "shield"
    assert e.s.cards[emb].face_up is False
    assert len(_defns(e, "hand", 1)) == hand_before + 1
    assert "T335" not in _defns(e, "hand", 1)


def test_indestructible_with_three_face_up(rules):
    """T338: 表向きカード3枚以上で不壊。2枚では不壊でない。"""
    e = setup(rules, {}, {"bz": ["T338"], "hand": ["T335", "T335", "T335"]})
    for _ in range(3):
        _stack_emblem(e, 1, "T335")
    cid = next(c for c in e.bz_tops(1) if e.s.cards[c].defn == "T338")
    assert e.chars_ro(cid)["indestructible"] is True
    e = setup(rules, {}, {"bz": ["T338"], "hand": ["T335", "T335"]})
    for _ in range(2):
        _stack_emblem(e, 1, "T335")
    cid = next(c for c in e.bz_tops(1) if e.s.cards[c].defn == "T338")
    assert e.chars_ro(cid)["indestructible"] is False
