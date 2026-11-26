"""語彙パイロット第355弾: trigger_when_ally_is_blocked（ドリフト）。

センサス（rejects 1,978件を取り直し。同期後 HEAD）: pure は
範囲外の大物が大半（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 / duelist_link 20 /
outside_game 12 / pandora_shift 4）で、残りは pure 1〜4件の
小家族が多数。評価済み却下（does_not_untap 等）は再提案しない。
範囲内・未評価で最小の trigger_when_ally_is_blocked
（pure 1件、multi にも現れない）を選定した:
dm21-048 肝っ玉メリー「自分のビークル・ビーがブロックされた時、
バトルの後、ブロックしたクリーチャーを破壊する」。

結論はドリフト（追加語彙なし）。部品はすべて確立済み:
- block レコードの attacker 照合は第320弾で確立。第三者の
  観測形 {attacker: {owner: you}} は dm19-s02 の登録先例
  （第280弾）があり、filter を重ねて種族で絞る。
- 「バトルの後」は第319弾の delayed_trigger
  {when: {event: attack_end, subject: <同じ攻撃クリーチャー>},
  duration: during_attack}。during_attack のため、この攻撃の
  attack_end だけに一致し、別の攻撃へ漏れない。
- 破壊対象は発火レコードの event.target（attack_end の
  target はブロックしたクリーチャー。第319弾の記録）。

proto T1066（メリー型）/ T1067（ビークル・ビー）/
T1068（バトルに勝つブロッカー）/ T1069（対照の非ビークル・ビー）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
scenario.build を直接包む（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

_VB = {"owner": "you", "filter": {"race_has": "ビークル・ビー"}}
TRIGGER = {"kind": "trigger",
           "when": {"event": "block", "attacker": _VB},
           "effect": [{"op": "delayed_trigger",
                       "when": {"event": "attack_end", "subject": _VB},
                       "duration": "during_attack",
                       "effect": [{"op": "destroy",
                                   "select": {"ref": "event.target"}}]}]}
FORM = [TRIGGER]

# parse 後は destroy マクロが move（to: graveyard, reason: destroy）
# に展開される。parse 比較は展開形で行う。
PARSED_TRIGGER = copy.deepcopy(TRIGGER)
PARSED_TRIGGER["effect"][0]["effect"] = [
    {"op": "move", "select": {"ref": "event.target"},
     "to": "graveyard", "reason": "destroy"}]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1066")
    assert c["abilities"] == FORM
    d = parse_card(copy.deepcopy(c), TABLES)
    assert PARSED_TRIGGER in d.abilities


def test_form_raw_parse():
    d = parse_card({"id": "TX355", "name": "x",
                    "types": ["creature"], "civs": ["fire"],
                    "cost": 5, "power": 4000,
                    "abilities": [copy.deepcopy(TRIGGER)]}, TABLES)
    assert PARSED_TRIGGER in d.abilities


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive_attack(e, attacker, block):
    """attacker でプレイヤーを攻撃する。block=True なら相手の
    ブロッカー（T1068）でブロックする。攻撃したターンの
    2つ先のターンまで進めて状態を返す。"""
    state = {"attacked": False, "attack_turn": None}
    for _ in range(1500):
        if state["attacked"] and e.s.turn >= state["attack_turn"] + 2:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack":
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and not state["attacked"]:
                state["attacked"] = True
                state["attack_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            hit = [i for i, k in enumerate(keys)
                   if block and k.startswith("bz:T1068:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return state


def test_blocker_destroyed_after_battle(rules):
    """ビークル・ビー（3000）が大ブロッカー（4500）にブロックされ
    バトルに負けた後、ブロックしたクリーチャーが破壊される。"""
    e = _build(rules, {"bz": ["T1066", "T1067"]}, {"bz": ["T1068"]})
    st = _drive_attack(e, "T1067", block=True)
    assert st["attacked"]
    assert "T1067" in _defns(e, "graveyard", 0)      # バトル敗北
    assert "T1068" in _defns(e, "graveyard", 1)      # バトルの後に破壊
    assert "T1068" not in _defns(e, "bz", 1)
    assert "T1066" in _defns(e, "bz", 0)             # 観測者は残る


def test_no_trigger_for_non_vehicle_bee(rules):
    """ビークル・ビーでないクリーチャーがブロックされても
    ブロッカーは破壊されない（バトルに勝って場に残る）。"""
    e = _build(rules, {"bz": ["T1066", "T1069"]}, {"bz": ["T1068"]})
    st = _drive_attack(e, "T1069", block=True)
    assert st["attacked"]
    assert "T1069" in _defns(e, "graveyard", 0)
    assert "T1068" in _defns(e, "bz", 1)
    assert "T1068" not in _defns(e, "graveyard", 1)


def test_no_block_no_destroy(rules):
    """ブロックされなければ何も破壊されない。"""
    e = _build(rules, {"bz": ["T1066", "T1067"]}, {"bz": ["T1068"]})
    st = _drive_attack(e, "T1067", block=False)
    assert st["attacked"]
    assert "T1067" in _defns(e, "bz", 0)
    assert "T1068" in _defns(e, "bz", 1)
    assert "T1068" not in _defns(e, "graveyard", 1)
