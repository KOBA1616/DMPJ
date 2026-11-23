"""語彙パイロット第353弾: trigger_when_opponent_plays_without_paying
（ドリフト）。

対象（pure 2件すべて）:
- dm22rp2x-020 チッタ・ペロルの冠（タマシード: 相手のターン中、
  相手のクリーチャー/タマシードがコストを支払わずに出た時、
  自壊→1ドロー→火コスト5以下を手札から出してよい）
- dm23rp2x-033 ゼンツー（各ターンに一度、相手がコストを
  支払わずにエレメントを出した時、マジック・メクレイド5）

形: 「支払わずに出た」は第345弾の when の unpaid: true。
「各ターンに一度」は trigger の once_per_turn: true。
メクレイドは既存 op {op: mekurade, filter, cost_le}
（dm25ex1-078 のサイバー・メクレイド5と同型、filter は
race_has）。「破壊してもよい。そうしたら〜」は全体を
1つの may に包む（引くのは任意でなく、出してよいだけ任意）。

proto: T1060（020型）/ T1061（033型）/ T1062（検証用）。

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

TRIG_020 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "opp",
                         "filter": {"types": ["creature", "tamaseed"]}},
             "unpaid": True},
    "if": {"is_turn": "opp"},
    "effect": [
        {"op": "may", "body": [
            {"op": "destroy", "select": {"ref": "self"}},
            {"op": "draw", "count": 1},
            {"op": "may", "body": [
                {"op": "choose",
                 "select": {"zone": "hand", "owner": "you",
                            "filter": {"types": ["creature"],
                                       "civs": ["fire"], "cost_le": 5},
                            "count": 1},
                 "as": "pc"},
                {"op": "move", "select": {"ref": "pc"},
                 "to": "bz", "reason": "put"},
            ]},
        ]},
    ],
}
TRIG_033 = {
    "kind": "trigger", "once_per_turn": True,
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "opp"}, "unpaid": True},
    "effect": [{"op": "may", "body": [
        {"op": "mekurade",
         "filter": {"race_has": "マジック"}, "cost_le": 5}]}],
}

FORM_020 = [TRIG_020]
FORM_033 = [TRIG_033]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    c = proto_card("T1060")
    assert c["abilities"] == FORM_020
    parse_card(c, TABLES)
    c = proto_card("T1061")
    assert c["abilities"] == FORM_033
    parse_card(c, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _drive_lacrima_entry(e):
    """p1 のラクリマ・クロウラー（dm22rp1-002）がターン終わりに
    無償で出るまで進め、続く p0 の2回目の charge で止める。
    p1 は呪文 T241 を唱え、誘発にはすべて yes と答える。"""
    p0_charges = 0
    for _ in range(900):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "charge" and d.get("player") == 0:
            p0_charges += 1
            if p0_charges >= 2:
                return
        if (d["kind"] == "main" and d.get("player") == 1
                and "play:T241" in keys):
            e.answer([keys.index("play:T241")])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("yes")])
        elif d["kind"] == "choose_cards":
            pick = [i for i, k in enumerate(keys) if "T1062" in k]
            e.answer(pick[:1] if pick else list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("drive never finished")


def _lacrima_setup(p0_extra):
    p0 = {"mana": ["T001"]}
    p0.update(p0_extra)
    p1 = {"hand": ["dm22rp1-002", "T241"],
          "mana": ["T009", "T009", "T009", "T009", "T009"]}
    return p0, p1


def test_tamaseed_reacts_to_unpaid_entry(rules):
    p0, p1 = _lacrima_setup({"bz": ["T1060"], "hand": ["T005"]})
    e = _build(rules, p0, p1)
    _drive_lacrima_entry(e)
    # タマシードは自壊し、火クリーチャーが手札から出た
    assert "T1060" in [e.s.cards[c].defn for c in e.zlist("graveyard", 0)]
    assert "T005" in [e.s.cards[c].defn for c in e.bz_tops(0)]


def test_mekurade_on_unpaid_entry(rules):
    p0, p1 = _lacrima_setup({"bz": ["T1061"],
                             "deck": ["T1062", "T1062", "T1062",
                                      "T002", "T002"]})
    e = _build(rules, p0, p1)
    _drive_lacrima_entry(e)
    # メクレイドで見たマジック（T1062）が場に出た
    assert "T1062" in [e.s.cards[c].defn for c in e.bz_tops(0)]
