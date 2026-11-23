"""語彙パイロット第344弾: used_this_turn_condition（ドリフト）。

対象（pure 2件）:
- dmrp21-053 頂上演者 スケプティック（このターン、自分が
  タマシードを使うか呪文を唱えていなければ、このクリーチャーは
  攻撃できない）
- dm22rp1-002 ラクリマ・クロウラー（各ターンの終わりに、
  自分がそのターン中、コスト５以上の呪文またはコスト５以上の
  タマシードを使っていたら、このクリーチャーを手札から
  出してもよい）

「使った」は used_count 式で数える（唱えた呪文＋via: generate
で実行したタマシード等の履歴。印刷特性のスナップショットで
照合する。バンドC1 U19 で既存）:
- 053: static {affects: self, if: {cmp: [{used_count:
  {owner: you, filter: {types: [spell, tamaseed]}}}, "==", 0]},
  mod: {deny: [attack_player, attack_creature]}}
  （「攻撃できない」は許可語彙の attack_player /
  attack_creature の両方を deny する）
- 002: 手札誘発 {kind: trigger, zone: hand, when:
  {event: turn_end}, if: {cmp: [{used_count: {owner: you,
  filter: {types: [spell, tamaseed], cost_ge: 5}}}, ">=", 1]},
  effect: [may [move {ref: self} to: bz reason: put]]}
  （「出す」は召喚ではない。第329弾の作法）

proto: T1037（053型）/ T1038（002型、カード全体）。

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

STATIC_053 = {
    "kind": "static", "affects": "self",
    "if": {"cmp": [{"used_count": {"owner": "you",
                                   "filter": {"types": ["spell",
                                                        "tamaseed"]}}},
                    "==", 0]},
    "mod": {"deny": ["attack_player", "attack_creature"]},
}

JUSTDIVER_002 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "modify", "select": {"ref": "self"},
                "mod": {"deny": ["be_chosen", "be_attacked"]},
                "duration": "until_next_own_turn_start"}],
}
CIVIL_002 = {
    "kind": "trigger",
    "when": {"event": "attack", "subject": "self"},
    "if": {"cmp": [{"count": {"zone": "bz", "owner": "you",
                              "filter": {"civs": ["water"],
                                         "types": ["creature",
                                                   "tamaseed"]}}},
                    ">=", 3]},
    "effect": [{"op": "may", "body": [{"op": "draw", "count": 2}]}],
}
HAND_END_002 = {
    "kind": "trigger", "zone": "hand",
    "when": {"event": "turn_end"},
    "if": {"cmp": [{"used_count": {"owner": "you",
                                   "filter": {"types": ["spell",
                                                        "tamaseed"],
                                              "cost_ge": 5}}},
                    ">=", 1]},
    "effect": [{"op": "may",
                "body": [{"op": "move", "select": {"ref": "self"},
                          "to": "bz", "reason": "put"}]}],
}

FORM_053 = [STATIC_053]
FORM_002 = [JUSTDIVER_002, CIVIL_002, HAND_END_002]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    c = proto_card("T1037")
    assert c["abilities"] == FORM_053
    parse_card(c, TABLES)
    c = proto_card("T1038")
    assert c["abilities"] == FORM_002
    parse_card(c, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _drive(e, plan, limit=900):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        if plan(d, _keys(d)):
            return d
    raise AssertionError("plan never stopped")


def test_t1037_cannot_attack_until_used(rules):
    e = _build(rules, {"bz": ["T1037", "T005"], "hand": ["T003"],
                       "mana": ["T009", "T001"]},
               {})
    state = {"attacks_seen": 0, "cast": False, "snap": []}

    def plan(d, keys):
        if d["kind"] == "attack" and d.get("player") == 0:
            state["attacks_seen"] += 1
            state["snap"].append(list(keys))
            if state["attacks_seen"] == 2:
                return True
            e.answer([keys.index("pass")])
            return False
        if d["kind"] == "main" and d.get("player") == 0 \
                and state["attacks_seen"] == 1 \
                and not state["cast"] and "play:T003" in keys:
            e.answer([keys.index("play:T003")])
            state["cast"] = True
            return False
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        return False

    _drive(e, plan)
    first, second = state["snap"]
    assert "attack:T005:player" in first
    assert not any(k.startswith("attack:T1037") for k in first)
    assert "attack:T1037:player" in second   # 唱えた後は攻撃できる


def test_t1038_comes_out_when_used(rules):
    e = _build(rules, {"hand": ["T1038", "T241"],
                       "mana": ["T009", "T001", "T001", "T001", "T001"]},
               {})
    state = {"cast": False, "may_seen": False}

    def plan(d, keys):
        if state["may_seen"] and d["kind"] == "charge" \
                and d.get("player") == 1:
            return True
        if d["kind"] == "main" and d.get("player") == 0 \
                and not state["cast"] and "play:T241" in keys:
            e.answer([keys.index("play:T241")])
            state["cast"] = True
            return False
        if d["kind"] == "yes_no" and d.get("player") == 0:
            state["may_seen"] = True
            e.answer([keys.index("yes")])
            return False
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        return False

    _drive(e, plan)
    assert state["may_seen"] is True
    assert "T1038" in [e.s.cards[c].defn for c in e.bz_tops(0)]


def test_t1038_stays_when_not_used(rules):
    e = _build(rules, {"hand": ["T1038"], "mana": ["T001"]}, {})
    state = {"may_seen": False}

    def plan(d, keys):
        if d["kind"] == "charge" and d.get("player") == 1:
            return True
        if d["kind"] == "yes_no" and d.get("player") == 0:
            state["may_seen"] = True
            e.answer([keys.index("no")])
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        return False

    _drive(e, plan)
    assert state["may_seen"] is False
    assert "T1038" in [e.s.cards[c].defn for c in e.zlist("hand", 0)]
