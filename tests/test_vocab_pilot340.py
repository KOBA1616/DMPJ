"""語彙パイロット第340弾: enters_tapped_opponent（ドリフト）。

対象（pure 2件）:
- dmc52-007 聖霊王エルフェウス（相手クリーチャーはタップされた
  状態でバトルゾーンに出る）
- dm24bd6-006 偽りの希望 修羅丸「終斗」（各ターン、はじめて
  相手のクリーチャーが出る時、そのクリーチャーはタップして出る）

確立形:
- 無条件形は第339弾の static {affects: {zone: bz, owner: opp,
  filter: {types: [creature]}}, mod: {grant: [enters_tapped]}}。
- 「各ターン、はじめて」は first_time 誘発で表す:
  {kind: trigger, first_time: true, when: {event: move, to: bz,
  subject: {owner: opp, filter: {types: [creature]}}},
  effect: [tap {select: {ref: event.subject}}]}。
  first_time は出来事の通し番号で数えるため、「出て離れた後の
  2体目」を数え違えない。常在型の count ゲート
  （entered_this_turn == 0）は、出るカード自身が評価時点で
  既に数えられていて常に閉じてしまうため使えない（実測）。

proto: T1030（エルフェウス型）/ T1031（修羅丸型）。

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

FORM_007 = [
    {"kind": "static",
     "affects": {"zone": "bz", "owner": "opp",
                 "filter": {"types": ["creature"]}},
     "mod": {"grant": ["enters_tapped"]}},
]

FORM_006 = [
    {"kind": "trigger", "first_time": True,
     "when": {"event": "move", "to": "bz",
              "subject": {"owner": "opp",
                          "filter": {"types": ["creature"]}}},
     "effect": [{"op": "tap", "select": {"ref": "event.subject"}}]},
]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    c = proto_card("T1030")
    assert c["abilities"] == FORM_007
    assert c["evolve_from"] == {"race_has": "エンジェル・コマンド"}
    parse_card(c, TABLES)
    c = proto_card("T1031")
    assert c["abilities"] == FORM_006
    parse_card(c, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz_card(e, p, defn):
    return next(c for c in e.bz_tops(p)
                if e.s.cards[c].defn == defn)


def _drive(e, plan, limit=900):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        if plan(d, _keys(d)):
            return d
    raise AssertionError("plan never stopped")


def test_t1030_opponent_creatures_enter_tapped(rules):
    e = _build(rules, {"bz": ["T1030"]},
               {"hand": ["T005"], "mana": ["T005", "T001", "T001"]})
    state = {"played": False}

    def plan(d, keys):
        if state["played"] and d["kind"] == "charge" \
                and d.get("player") == 0:
            return True
        if d["kind"] == "main" and d.get("player") == 1 \
                and not state["played"] and "play:T005" in keys:
            e.answer([keys.index("play:T005")])
            state["played"] = True
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
    assert e.s.cards[_bz_card(e, 1, "T005")].tapped is True


def test_t1031_only_first_entry_each_turn(rules):
    e = _build(rules, {"bz": ["T1031"]},
               {"hand": ["T005", "T009", "T004", "T003"],
                "mana": ["T005", "T009", "T004", "T001", "T001"]})
    state = {"p1turns": 0, "phase": 1, "played": set()}

    def plan(d, keys):
        if d["kind"] == "charge" and d.get("player") == 1:
            state["p1turns"] += 1
            tgt = "charge:T003" if state["p1turns"] == 2 else None
            if tgt and tgt in keys:
                e.answer([keys.index(tgt)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
            return False
        if d["kind"] == "charge" and d.get("player") == 0:
            if state["phase"] == 1 and state["p1turns"] == 1 \
                    and {"T005", "T009"} <= state["played"]:
                return True        # 1ターン目の結果を観測
            if state["phase"] == 2 and state["p1turns"] == 2 \
                    and "T004" in state["played"]:
                return True        # 2ターン目の結果を観測
            if "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
            return False
        if d["kind"] == "main" and d.get("player") == 1:
            for tgt in ("T005", "T009", "T004"):
                key = f"play:{tgt}"
                if key in keys and tgt not in state["played"]:
                    e.answer([keys.index(key)])
                    state["played"].add(tgt)
                    return False
        if d["kind"] == "pay_mana":
            # 水マナ（T009）を残す支払いを優先する
            keep = [i for i, k in enumerate(keys) if "T009" not in k]
            e.answer(keep[:d["min"]] if keep
                     else list(range(d["min"])))
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        return False

    _drive(e, plan)
    # 1体目はタップして出る、2体目はタップしない
    assert e.s.cards[_bz_card(e, 1, "T005")].tapped is True
    assert e.s.cards[_bz_card(e, 1, "T009")].tapped is False
    state["phase"] = 2
    _drive(e, plan)
    # 次のターンでは再び1体目がタップして出る
    assert e.s.cards[_bz_card(e, 1, "T004")].tapped is True
