"""語彙パイロット第348弾: invasion_zero（エンジン拡張＋ドリフト）。

対象（pure 3件すべて）:
- dmbd21-018 ZEROの侵略 ブラックアウト
- dmd35-011 ZEROの暴走 デッドリー・ハイウェイ（D2フィールド）
- promoy15-035 禁断の月 ドキンダムーン（D2フィールド）

侵略ZERO の形: 手札の turn_end 誘発
{kind: trigger, zone: hand, when: {event: turn_end},
 if: {all: [{is_turn: opp},
            {cmp: [{turn_count: {kind: enter_unpaid, owner: opp,
                                 filter: {types: [creature]}}},
                   ">=", 1]}]},
 effect: [may [move {ref: self} to: bz reason: put]]}

エンジン拡張: turn_count の kind: enter_unpaid は従来は
整数カウンタ（hist:enter_unpaid）だけで種類で絞れなかった。
events.py が無償登場の cid リスト（enter_unpaid:<player>）も
残し、selectors._turn_count に attack と同じ filter 方式の
分岐を足し、defs.py の検証で enter_unpaid の filter を許可した
（3点セット。整数カウンタは従来どおり併存）。

dmbd21-018 の攻撃時誘発は「自分のD2フィールドがあれば」
{exists: {zone: bz, owner: you, filter: {types: [d2_field]}}}
＋「パワーが一番大きい」select の extremal: max_power。

proto: T1046（018型）/ T1047（011型）/ T1048（035型）。

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

ZERO = {
    "kind": "trigger", "zone": "hand",
    "when": {"event": "turn_end"},
    "if": {"all": [{"is_turn": "opp"},
                   {"cmp": [{"turn_count": {"kind": "enter_unpaid",
                                            "owner": "opp",
                                            "filter": {"types": ["creature"]}}},
                            ">=", 1]}]},
    "effect": [{"op": "may",
                "body": [{"op": "move", "select": {"ref": "self"},
                          "to": "bz", "reason": "put"}]}],
}
ATK_018 = {
    "kind": "trigger",
    "when": {"event": "attack", "subject": "self"},
    "if": {"exists": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["d2_field"]}}},
    "effect": [{"op": "destroy",
                "select": {"zone": "bz", "owner": "opp",
                           "filter": {"types": ["creature"]},
                           "extremal": "max_power", "count": 1}}],
}
DSW_011 = {
    "kind": "trigger", "dswitch": True,
    "when": {"event": "turn_start", "player": "you"},
    "effect": [{"op": "may",
                "body": [{"op": "dswitch"},
                         {"op": "destroy",
                          "select": {"zone": "bz", "owner": "opp",
                                     "filter": {"types": ["creature"],
                                                "tapped": True},
                                     "count": 1}}]}],
}
CIP_035 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "mill", "owner": "you", "count": 2}],
}
DSW_035 = {
    "kind": "trigger", "dswitch": True,
    "when": {"event": "turn_start", "player": "you"},
    "effect": [{"op": "may",
                "body": [{"op": "dswitch"},
                         {"op": "move",
                          "select": {"zone": "graveyard", "owner": "you",
                                     "filter": {"race_has": "ソニック・コマンド"},
                                     "count": 1},
                          "to": "bz", "reason": "put"}]}],
}

FORM_018 = [ZERO, ATK_018]
FORM_011 = [ZERO, DSW_011]
FORM_035 = [ZERO, CIP_035, DSW_035]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    for tid, form in (("T1046", FORM_018), ("T1047", FORM_011),
                      ("T1048", FORM_035)):
        c = proto_card(tid)
        assert c["abilities"] == form, tid
        parse_card(c, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _opp_unpaid_turn(e, state):
    """相手（p1）のターン: T1049（fixture 呪文）で T005 を
    コストを支払わずに出す。p0 の ZERO 誘発の may
    （player 0 の yes_no）が出たら state に記録して yes。"""
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "yes_no" and d.get("player") == 0:
            state["zero_asked"] = True
            e.answer([keys.index("yes")])
            continue                   # 解決は後続の advance で進む
        if d["kind"] == "charge" and d.get("player") == 0:
            state["p0_charges"] = state.get("p0_charges", 0) + 1
            if state["p0_charges"] >= 2:
                return                 # p1 のターンを1回分通過した
        if d["kind"] == "main" and d.get("player") == 1 \
                and "play:T1049" in keys:
            e.answer([keys.index("play:T1049")])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "choose_cards" and d.get("player") == 1:
            pick = [i for i, o in enumerate(d["options"])
                    if o["key"].startswith("hand:T005")]
            e.answer(pick[:1] if pick else list(range(d["min"])))
            state["entered"] = True
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def _unpaid_setup():
    return {"hand": ["T1049", "T005"], "mana": ["T001"]}


def test_zero_creature_enters(rules):
    e = _build(rules, {"hand": ["T1046"]}, _unpaid_setup())
    state = {}
    _opp_unpaid_turn(e, state)
    assert state.get("zero_asked"), "侵略ZERO の may が出なかった"
    assert "T1046" in [e.s.cards[c].defn for c in e.bz_tops(0)]


def test_zero_field_enters(rules):
    e = _build(rules, {"hand": ["T1047"]}, _unpaid_setup())
    state = {}
    _opp_unpaid_turn(e, state)
    assert state.get("zero_asked")
    assert "T1047" in [e.s.cards[c].defn for c in e.bz_tops(0)]


def test_zero_not_triggered_without_unpaid(rules):
    # 相手が何も出さなければ誘発しない
    e = _build(rules, {"hand": ["T1046"]},
               {"mana": ["T009", "T004", "T001", "T001", "T001"]})
    state = {}
    _opp_unpaid_turn(e, state)
    assert not state.get("zero_asked")
    assert "T1046" not in [e.s.cards[c].defn for c in e.bz_tops(0)]


def _attack_with(e, attacker, state):
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 1:
            return
        if d["kind"] == "attack" and d.get("player") == 0 \
                and not state.get("attacked"):
            atk = [k for k in keys if k.startswith(f"attack:{attacker}:")]
            if atk:
                state["attacked"] = True
                e.answer([keys.index(atk[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def test_attack_destroys_highest_power_with_field(rules):
    e = _build(rules, {"bz": ["T1046", "T1047"]},
               {"bz": ["T005", "T1014"]})
    state = {}
    _attack_with(e, "T1046", state)
    assert state.get("attacked")
    p1_grave = [e.s.cards[c].defn for c in e.zlist("graveyard", 1)]
    assert "T1014" in p1_grave          # パワー最大が破壊される
    assert "T005" in [e.s.cards[c].defn for c in e.bz_tops(1)]


def test_attack_no_destroy_without_field(rules):
    e = _build(rules, {"bz": ["T1046"]}, {"bz": ["T005", "T1014"]})
    state = {}
    _attack_with(e, "T1046", state)
    assert state.get("attacked")
    p1_grave = [e.s.cards[c].defn for c in e.zlist("graveyard", 1)]
    assert "T1014" not in p1_grave
