"""語彙パイロット第345弾: trigger_when_opponent_plays_free（ドリフト）。

対象（pure 3件）:
- dm23rp3-025 運明！ベリアvs.キャディ（相手のターン中 +10000、
  相手のエレメントがコストを支払わずに出た時、山札の上を
  マナゾーンに置いてもよい）
- dm24bd5-008 魔力妖精バーベナ（同条件で1ドロー、その後
  そのエレメント以下のコストのクリーチャーを手札から出してもよい）
- dm24ex1-058 冥土人形ロッカ・マグナム（同条件、または相手が
  呪文を唱えた時、相手は自身のエレメントを1つ選び破壊する）

「コストを支払わずに出た」は when の unpaid: true で判定する
（第257弾で move レコードに載る。効果で出されたカードは
マナをタップせずに出ている）。相手のターン中は if {is_turn: opp}。

proto: T1039（025型）/ T1040（008型）/ T1041（058型）。
実挙動の「支払わずに出る」側は登録済み dm22rp1-002
ラクリマ・クロウラー（第344弾。コスト5呪文を唱えたターン
終わりに手札から出る）で作る。

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

STATIC_025 = {"kind": "static", "affects": "self",
              "if": {"is_turn": "opp"}, "mod": {"power": 10000}}
TRIG_025 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "opp"}, "unpaid": True},
    "if": {"is_turn": "opp"},
    "effect": [{"op": "may",
                "body": [{"op": "move",
                          "select": {"zone": "deck", "owner": "you",
                                     "from_top": 1},
                          "to": "mana", "reason": "put"}]}],
}
TRIG_008 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "opp"}, "unpaid": True},
    "if": {"is_turn": "opp"},
    "effect": [{"op": "draw", "count": 1},
               {"op": "may",
                "body": [{"op": "choose",
                          "select": {"zone": "hand", "owner": "you",
                                     "filter": {"types": ["creature"],
                                                "cost_le": {"cost_of": "event.subject"}}},
                          "as": "put_card"},
                         {"op": "move", "select": {"ref": "put_card"},
                          "to": "bz", "reason": "put"}]}],
}
_EFF_058 = [{"op": "choose",
             "select": {"zone": "bz", "owner": "opp", "count": 1,
                        "chooser": "opp"},
             "as": "victim"},
            {"op": "destroy", "select": {"ref": "victim"}}]
TRIG_058A = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "opp"}, "unpaid": True},
    "if": {"is_turn": "opp"}, "effect": _EFF_058,
}
TRIG_058B = {
    "kind": "trigger",
    "when": {"event": "cast",
             "subject": {"owner": "opp",
                         "filter": {"types": ["spell"]}}},
    "if": {"is_turn": "opp"}, "effect": _EFF_058,
}

FORM_025 = [STATIC_025, TRIG_025]
FORM_008 = [TRIG_008]
FORM_058 = [TRIG_058A, TRIG_058B]

CRAWLER = "dm22rp1-002"


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    c = proto_card("T1039")
    assert [a for a in c["abilities"]] == FORM_025
    parse_card(c, TABLES)
    c = proto_card("T1040")
    assert c["abilities"] == FORM_008
    parse_card(c, TABLES)
    c = proto_card("T1041")
    assert c["abilities"] == FORM_058
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


def _crawler_setup(e, state, on_p0_may=None, on_p1_choose=None):
    """p1 が T241 を唱え、ターン終わりにクロウラーを出す共通ドライバ。"""
    def plan(d, keys):
        if state.get("resolved") and d["kind"] == "charge" \
                and d.get("player") == 0:
            return True
        if d["kind"] == "charge" and d.get("player") == 1:
            state["p1turns"] = state.get("p1turns", 0) + 1
        if d["kind"] == "main" and d.get("player") == 1 \
                and not state.get("cast") and "play:T241" in keys:
            e.answer([keys.index("play:T241")])
            state["cast"] = True
            return False
        if d["kind"] == "yes_no" and d.get("player") == 1:
            e.answer([keys.index("yes")])   # クロウラーを出す
            return False
        if d["kind"] == "yes_no" and d.get("player") == 0:
            state["p0_mays"] = state.get("p0_mays", 0) + 1
            state["resolved"] = True
            if on_p0_may:
                on_p0_may(e, d, keys)
            else:
                e.answer([keys.index("yes")])
            return False
        if d["kind"] == "choose_cards" and d.get("player") == 1 \
                and on_p1_choose:
            state["resolved"] = True
            on_p1_choose(e, d, keys)
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


_P1 = {"hand": [CRAWLER, "T241"],
       "mana": ["T009", "T001", "T001", "T001", "T001"]}


def test_t1039_mana_boost_on_unpaid_entry(rules):
    e = _build(rules, {"bz": ["T1039"], "mana": ["T001"]}, dict(_P1))
    state = {}
    mana_before = len(e.zlist("mana", 0))
    _drive(e, _crawler_setup(e, state))
    assert state.get("p0_mays", 0) >= 1
    assert len(e.zlist("mana", 0)) == mana_before + 1


def test_t1040_draw_and_put_on_unpaid_entry(rules):
    e = _build(rules, {"bz": ["T1040"], "hand": ["T005"]}, dict(_P1))
    state = {}
    _drive(e, _crawler_setup(e, state))
    assert state.get("p0_mays", 0) >= 1
    # 自分のターン開始ドローで手札1→2、誘発で1枚引いて（2→3）、
    # T005（コスト3 <= 6）を出した（3→2）
    assert "T005" in [e.s.cards[c].defn for c in e.bz_tops(0)]
    assert len(e.zlist("hand", 0)) == 2


def test_t1041_opponent_destroys_own_on_unpaid_entry(rules):
    # 唱えた時の誘発（T004 を破壊）と、支払わずに出た時の誘発
    # （T005 を破壊）の両方を見る。候補が1体だけだと選択は
    # 自動で決まるため、相手の場には2体置く。
    e = _build(rules, {"bz": ["T1041"]},
               {**_P1, "bz": ["T004", "T005"]})
    state = {"picks": []}

    def pick(eng, d, keys):
        state["picks"].append(True)
        want = "T004" if len(state["picks"]) == 1 else "T005"
        idx = next(i for i, o in enumerate(d["options"])
                   if want in o["key"])
        eng.answer([idx])

    _drive(e, _crawler_setup(e, state, on_p1_choose=pick))
    assert len(state["picks"]) == 2
    gy = [e.s.cards[c].defn for c in e.zlist("graveyard", 1)]
    assert "T004" in gy and "T005" in gy
    assert CRAWLER in [e.s.cards[c].defn for c in e.bz_tops(1)]


def test_no_trigger_on_paid_entry(rules):
    # 通常召喚（支払って出す）では誘発しない
    e = _build(rules, {"bz": ["T1039"], "mana": ["T001"]},
               {"hand": ["T005"], "mana": ["T005", "T001", "T001"]})
    state = {"p0_mays": 0}

    def plan(d, keys):
        if d["kind"] == "charge" and d.get("player") == 0 \
                and state.get("played"):
            return True
        if d["kind"] == "main" and d.get("player") == 1 \
                and "play:T005" in keys:
            e.answer([keys.index("play:T005")])
            state["played"] = True
            return False
        if d["kind"] == "yes_no" and d.get("player") == 0:
            state["p0_mays"] += 1
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
    assert state["p0_mays"] == 0
    assert len(e.zlist("mana", 0)) == 1
