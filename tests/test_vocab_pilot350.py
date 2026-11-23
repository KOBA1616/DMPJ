"""語彙パイロット第350弾: must_attack_next_turn（ドリフト）。

対象（pure 3件のうち2件）:
- dm05-014 ファントム・ベール（呪文: 相手の次のターン、
  相手の攻撃できるクリーチャーはすべて攻撃しなければならない）
- dmrp22-021 ドラヴィ圧鬼の巻（タマシード CIP: 次の自分の
  ターンのはじめまで、相手のクリーチャーは可能なら攻撃する）

形: 攻撃強制は mod の require: [attack]（turn.py が
chars の require を見て攻撃を強制する、ルール506.1b）。
期間つきの付与は op_modify＋duration の確立形（第276弾の
deny ロックと同型）で、呪文は until_next_opp_turn_end、
タマシードは until_next_own_turn_start。

dm23ex3-tr09 は対象外（バトル代替「かわりにこのクリーチャーが
バトルする」の機構が無く、全体を組めない）。

proto: T1054（014型・呪文）/ T1055（021型・タマシード）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
scenario.build を直接包む（第319弾以降の作法）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

MOD_014 = {"op": "modify",
           "select": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"]}, "count": "all"},
           "mod": {"require": ["attack"]},
           "duration": "until_next_own_turn_start"}
CIP_021 = {"kind": "trigger",
           "when": {"event": "move", "to": "bz", "subject": "self"},
           "effect": [{"op": "modify",
                       "select": {"zone": "bz", "owner": "opp",
                                  "filter": {"types": ["creature"]},
                                  "count": "all"},
                       "mod": {"require": ["attack"]},
                       "duration": "until_next_own_turn_start"}]}
SHINKA_021 = {"kind": "trigger",
              "when": {"event": "evolve_base", "subject": "self"},
              "effect": [{"op": "modify",
                          "select": {"ref": "event.top"},
                          "mod": {"gain": [{"kind": "trigger",
                                            "first_time": True,
                                            "when": {"event": "battle_win",
                                                     "subject": "self"},
                                            "effect": [{"op": "untap",
                                                        "select": {"ref": "self",
                                                                   "count": 1}}]}]},
                          "duration": "until_next_own_turn_start"}]}

FORM_021 = [CIP_021, SHINKA_021]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    c = proto_card("T1054")
    assert c["spell"] == [MOD_014]
    parse_card(c, TABLES)
    c = proto_card("T1055")
    assert c["abilities"] == FORM_021
    parse_card(c, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _play_then_opp_turn(e, play_key, state):
    """p0 の main で play_key を使い、続く p1 のターンを
    「可能なら pass」方針で進め、p0 の次の charge で止める。
    p1 の攻撃判断で pass が無かったら state に記録する。"""
    for _ in range(900):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if (d["kind"] == "charge" and d.get("player") == 0
                and state.get("played")):
            return
        if (d["kind"] == "main" and d.get("player") == 0
                and play_key in keys and not state.get("played")):
            state["played"] = True
            e.answer([keys.index(play_key)])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "attack" and d.get("player") == 1:
            if "pass" not in keys:
                state["forced_attack"] = True
            if "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                atk = [i for i, k in enumerate(keys)
                       if k.endswith(":player")]
                e.answer([atk[0] if atk else 0])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("yes")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("drive never finished")


def _opp_creatures_tapped(e):
    return {e.s.cards[c].defn: e.s.cards[c].tapped
            for c in e.bz_tops(1)}


def test_spell_forces_attacks_next_turn(rules):
    e = _build(rules, {"hand": ["T1054"], "mana": ["T053"]},
               {"bz": ["T005", "T004"]})
    shields_before = len(e.zlist("shield", 0))
    state = {}
    _play_then_opp_turn(e, "play:T1054", state)
    assert state.get("forced_attack"), "強制攻撃の判断が出なかった"
    tapped = _opp_creatures_tapped(e)
    assert all(tapped.values()), tapped          # 全員攻撃した
    assert len(e.zlist("shield", 0)) == shields_before - 3  # T005 は W・ブレイカー


def test_spell_negative_control(rules):
    # 呪文を使わなければ p1 は攻撃せずに終われる
    e = _build(rules, {"hand": ["T1054"], "mana": ["T053"]},
               {"bz": ["T005", "T004"]})
    state = {"played": True}      # play せず p1 ターンへ進める
    # p0 の main を pass で抜けるため played を自前で立てる代わりに
    # play_key を存在しないキーにして素通りさせる
    _play_then_opp_turn(e, "play:NOTHING", state)
    assert not state.get("forced_attack")
    tapped = _opp_creatures_tapped(e)
    assert not any(tapped.values()), tapped


def test_tamaseed_forces_attacks(rules):
    e = _build(rules, {"hand": ["T1055"], "mana": ["T005", "T001"]},
               {"bz": ["T005", "T004"]})
    state = {}
    _play_then_opp_turn(e, "play:T1055", state)
    assert state.get("forced_attack")
    tapped = _opp_creatures_tapped(e)
    assert all(tapped.values()), tapped
    # 期間は次の自分のターンのはじめまで: p0 のターン開始時点で
    # require は消えている
    c0 = next(c for c in e.bz_tops(1))
    assert "attack" not in e.chars_ro(c0)["require"]
