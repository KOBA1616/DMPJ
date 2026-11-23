"""語彙パイロット第341弾: each_player_keeps_one_creature（ドリフト）。

対象（pure 2件）:
- dm24bd6-003（出た時、各プレイヤーは自身のクリーチャーを
  １体ずつ選ぶ。選ばれなかったクリーチャーをすべて破壊する）
- dm23bd5-001（出た時、各プレイヤーは自身のクリーチャーを
  １体選び、残りをすべて持ち主のマナゾーンに置く）

確立形:
- 各プレイヤーの選択は choose の2回で表す。自分の分は通常の
  choose、相手の分は select の chooser: opp で相手に委ねる
  （dm23bd5-001 の partial のシールド選択と同型）。
- 「選ばれなかったすべて」は select の exclude
  （参照除外、C1 U35 で既存）で、束縛した keep_you / keep_opp
  を除いて数える。
- 003 は destroy、001 は move {to: mana, reason: put}
  （持ち主のマナゾーンはカードごとに持ち主へ向かう）。

proto: T1032（003型）/ T1033（001型の出た時条項）。

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

CRYSTAL_STATIC = {
    "kind": "static",
    "affects": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}},
    "if": {"cmp": [{"count": {"zone": "mana", "owner": "you",
                              "filter": {"face_down": True}}},
                    ">=", 4]},
    "mod": {"grant": ["blocker", "speed_attacker", "slayer"]},
}

def _choose_keep(as_name, owner, chooser=None):
    sel = {"zone": "bz", "owner": owner,
           "filter": {"types": ["creature"]}, "count": 1}
    if chooser:
        sel["chooser"] = chooser
    return {"op": "choose", "select": sel, "as": as_name}


def _rest_select():
    return {"zone": "bz", "owner": "any",
            "filter": {"types": ["creature"]}, "count": "all",
            "exclude": [{"ref": "keep_you"}, {"ref": "keep_opp"}]}


CIP_DESTROY = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [
        _choose_keep("keep_you", "you"),
        _choose_keep("keep_opp", "opp", chooser="opp"),
        {"op": "destroy", "select": _rest_select()},
    ],
}]

CIP_MANA = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [
        _choose_keep("keep_you", "you"),
        _choose_keep("keep_opp", "opp", chooser="opp"),
        {"op": "move", "select": _rest_select(),
         "to": "mana", "reason": "put"},
    ],
}]

FORM_003 = [CRYSTAL_STATIC] + CIP_DESTROY
FORM_001_CIP = CIP_MANA


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    c = proto_card("T1032")
    assert c["abilities"] == FORM_003
    parse_card(c, TABLES)
    c = proto_card("T1033")
    assert c["abilities"] == FORM_001_CIP
    parse_card(c, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _pick(keys, defn):
    return next(i for i, k in enumerate(keys)
                if f":{defn}:" in k or k.endswith(f":{defn}"))


def _drive(e, plan, limit=900):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        if plan(d, _keys(d)):
            return d
    raise AssertionError("plan never stopped")


def _summon_plan(e, state, summon_key, keeps):
    """keeps: [(defn, player)] の順に choose を捌く共通プラン。"""
    def plan(d, keys):
        if state.get("summoned") and state.get("p1_charged") \
                and d["kind"] == "attack" and d.get("player") == 0:
            return True
        if state.get("summoned") and d["kind"] == "charge" \
                and d.get("player") == 1:
            state["p1_charged"] = True
        if d["kind"] == "main" and d.get("player") == 0 \
                and not state.get("summoned") \
                and summon_key in keys:
            e.answer([keys.index(summon_key)])
            state["summoned"] = True
            return False
        if d["kind"] == "choose_cards" and keeps:
            defn, player = keeps[0]
            if d.get("player") == player:
                keeps.pop(0)
                state.setdefault("choose_players", []).append(player)
                e.answer([_pick(keys, defn)])
                if not keeps:
                    state["done"] = True
                return False
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        return False
    return plan


def test_t1032_destroy_all_but_kept(rules):
    e = _build(rules,
               {"hand": ["T1032"], "bz": ["T001"],
                "mana": ["T004", "T005", "T053"] + ["T001"] * 6},
               {"bz": ["T005", "T009"]})
    state = {}
    keeps = [("T1032", 0), ("T005", 1)]
    _drive(e, _summon_plan(e, state, "play:T1032", keeps))
    assert state["choose_players"] == [0, 1]   # 相手の選択は相手がする
    assert [e.s.cards[c].defn for c in e.bz_tops(0)] == ["T1032"]
    assert [e.s.cards[c].defn for c in e.bz_tops(1)] == ["T005"]
    assert [e.s.cards[c].defn for c in e.zlist("graveyard", 0)] == ["T001"]
    assert [e.s.cards[c].defn for c in e.zlist("graveyard", 1)] == ["T009"]


def test_t1033_rest_to_mana(rules):
    e = _build(rules,
               {"hand": ["T1033"], "bz": ["T001", "T009"],
                "mana": ["T004", "T053"] + ["T001"] * 8},
               {"bz": ["T005", "T004"]})
    state = {}
    keeps = [("T1033", 0), ("T005", 1)]
    _drive(e, _summon_plan(e, state, "play:T1033", keeps))
    assert state["choose_players"] == [0, 1]   # 相手の選択は相手がする
    assert [e.s.cards[c].defn for c in e.bz_tops(0)] == ["T1033"]
    assert [e.s.cards[c].defn for c in e.bz_tops(1)] == ["T005"]
    mana0 = {e.s.cards[c].defn for c in e.zlist("mana", 0)}
    assert {"T001", "T009"} <= mana0        # 残りは持ち主のマナへ
    mana1 = {e.s.cards[c].defn for c in e.zlist("mana", 1)}
    assert "T004" in mana1                  # 相手の残りも相手のマナへ


def test_t1033_opponent_with_no_creatures(rules):
    e = _build(rules,
               {"hand": ["T1033"], "bz": ["T001"],
                "mana": ["T004", "T053"] + ["T001"] * 8},
               {})
    state = {}
    keeps = [("T1033", 0)]      # 相手は0体: choose は出ない想定
    _drive(e, _summon_plan(e, state, "play:T1033", keeps))
    assert [e.s.cards[c].defn for c in e.bz_tops(0)] == ["T1033"]
    mana0 = {e.s.cards[c].defn for c in e.zlist("mana", 0)}
    assert "T001" in mana0
