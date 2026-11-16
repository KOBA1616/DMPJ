"""語彙パイロット第166弾: shield_force（シールド・フォース）。

出す時に自分のシールドを1枚選んでもよい（op sforce_link が選んだシールドに
sforce_of = 自分への参照を刻む）。そのシールドがシールドゾーンにある間、
カードの sforce 印つき能力（常在・誘発を問わない）が機能する
（core.abilities のゲート + core._sforce_active）。
"""
from pathlib import Path

import yaml
from conftest import setup

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in ("T310", "T311", "T312", "T313"):
        card = parse_card(_proto_card(cid), TABLES)
        kinds = [(a["kind"], bool(a.get("sforce"))) for a in card.abilities]
        assert ("trigger", False) in kinds          # 出す時の選択は印なし
        assert any(f for _, f in kinds if f)        # 得る能力には sforce 印


def _summon(e, tid, link="first", max_steps=400):
    """手札から tid を召喚し、シールド・フォースの選択まで処理して落ち着かせる。
    link='first' は先頭のシールドを、'none' は選ばないことを選ぶ。"""
    played = False
    for _ in range(max_steps):
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and not played and f"play:{tid}" in keys:
            played = True
            e.answer([keys.index(f"play:{tid}")])
            continue
        if played and (d["player"] != 0 or d["kind"] == "attack"):
            return   # 召喚した側のメインが終わった = 選択まで解決済み
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_cards":
            e.answer([0] if link == "first" else [])
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")] if "no" in keys else [0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def _cid(e, player, defn):
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _linked_shield(e, player):
    return [c for c in e.zlist("shield", player) if e.s.cards[c].sforce_of is not None]


def test_link_grants_power_and_breaker_until_shield_leaves(rules):
    e = setup(rules, {"hand": ["T311"], "mana": ["T277"] * 4}, {})
    _summon(e, "T311", link="first")
    me = _cid(e, 0, "T311")
    linked = _linked_shield(e, 0)
    assert len(linked) == 1 and list(e.s.cards[linked[0]].sforce_of) == list(e.s.ref(me))
    ch = e.chars(me)
    assert ch["power"] == 5000 and "double_breaker" in ch["keywords"]
    e._raw_move(linked[0], "graveyard")   # 紐付いたシールドがシールドゾーンを離れる
    ch = e.chars(me)
    assert ch["power"] == 2000 and "double_breaker" not in ch["keywords"]


def test_decline_link_grants_nothing(rules):
    e = setup(rules, {"hand": ["T310"], "mana": ["T030"] * 5}, {})
    _summon(e, "T310", link="none")
    me = _cid(e, 0, "T310")
    assert _linked_shield(e, 0) == []
    assert "blocker" not in e.chars(me)["keywords"]


def test_link_grants_blocker(rules):
    e = setup(rules, {"hand": ["T310"], "mana": ["T030"] * 5}, {})
    _summon(e, "T310", link="first")
    me = _cid(e, 0, "T310")
    assert "blocker" in e.chars(me)["keywords"]


def test_no_shields_means_no_choice_and_no_grant(rules):
    e = setup(rules, {"hand": ["T310"], "mana": ["T030"] * 5, "shield": []}, {})
    _summon(e, "T310", link="first")
    me = _cid(e, 0, "T310")
    assert "blocker" not in e.chars(me)["keywords"]


def _block_hand_delta(rules, link):
    """T312 でブロックし、次の自ターンのチャージ判断時点までの手札増減を返す。
    ターン開始ドロー（+1）が常に入るので、誘発ドローがあると +2 になる。"""
    e = setup(rules, {"hand": ["T312"], "mana": ["T287"] * 3}, {"bz": ["T005"]})
    _summon(e, "T312", link=link)
    hand_at_block = None
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended before block resolved"
        keys = [o["key"] for o in d["options"]]
        if hand_at_block is not None and d["kind"] == "charge" and d["player"] == 0:
            return len(e.zlist("hand", 0)) - hand_at_block
        if d["kind"] == "attack" and d["player"] == 1 and "attack:T005:player" in keys:
            e.answer([keys.index("attack:T005:player")])
        elif d["kind"] == "block" and d["player"] == 0:
            bkey = next((k for k in keys if "T312" in k), None)
            assert bkey is not None, keys
            hand_at_block = len(e.zlist("hand", 0))
            e.answer([keys.index(bkey)])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "pay_mana":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("block decision never offered")


def test_granted_trigger_draws_on_block(rules):
    e = setup(rules, {"hand": ["T312"], "mana": ["T287"] * 3}, {"bz": ["T005"]})
    _summon(e, "T312", link="first")
    me = _cid(e, 0, "T312")
    assert any(a.get("sforce") for a in e.fdef(me).abilities)
    assert [a for _, a in e.abilities(me, "trigger") if a.get("sforce")]
    # 紐付けあり: ターンドロー+1 と誘発ドロー+1 で +2。紐付けなし（対照）: +1 のみ
    assert _block_hand_delta(rules, "first") == 2
    assert _block_hand_delta(rules, "none") == 1


def test_no_leave_and_blocker_while_linked(rules):
    e = setup(rules, {"hand": ["T313"], "mana": ["T030"] * 7}, {})
    _summon(e, "T313", link="first")
    me = _cid(e, 0, "T313")
    ch = e.chars(me)
    assert "blocker" in ch["keywords"] and ch["no_leave"]
    linked = _linked_shield(e, 0)
    e._raw_move(linked[0], "graveyard")
    ch = e.chars(me)
    assert "blocker" not in ch["keywords"] and not ch["no_leave"]
