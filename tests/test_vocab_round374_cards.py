"""再変換ラウンド374（第339弾 opponent_cards_enter_tapped）の記録テスト。

- 新規登録2件: dmrp21-5a グーゴル ＜XENOM.Star＞ /
  dm23ex3-006 偽りの名 スコーピオ。いずれも登録形は確立形と
  完全一致（スコーピオのターン開始誘発だけ partial の
  {subject: self} 形から実働形に修正）。
- alias 畳み込み0件（submit 時に 5a へ aliases 2件が自動記録
  されたが rejects 行ではない）・差し戻し0件。
- converted 10,301→10,303 / rejects 2,013→2,011、
  canonical 重なり0・漏れ0。opponent_cards_enter_tapped
  の行は残っていない（ファミリー解消）。

実挙動は登録カード自身で固定する（グーゴルがいる間、相手の
チャージも召喚もタップして置かれる。スコーピオは裏向き
4枚でゲートが開く）。ドライバは scenario.build の薄い包みで、
tests.conftest は import しない（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402

from tests import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

CRYSTAL4 = {"cmp": [{"count": {"zone": "mana", "owner": "you",
                               "filter": {"face_down": True}}},
                     ">=", 4]}
FORM_5A = [
    {"kind": "trigger",
     "when": {"event": "attack", "subject": "self"},
     "effect": [{"op": "discard",
                 "select": {"zone": "hand", "owner": "opp",
                            "count": 1, "chooser": "random"}}]},
    {"kind": "static", "affects": {"zone": "bz", "owner": "opp"},
     "mod": {"grant": ["enters_tapped"]}},
]
FORM_006 = [
    {"kind": "trigger",
     "when": {"event": "move", "to": "bz", "subject": "self"},
     "effect": [{"op": "may", "body": [
         {"op": "flip_down",
          "select": {"zone": "mana", "owner": "you", "count": 1}}]}]},
    {"kind": "trigger",
     "when": {"event": "turn_start"},
     "if": {"is_turn": "you"},
     "effect": [{"op": "may", "body": [
         {"op": "flip_down",
          "select": {"zone": "mana", "owner": "you", "count": 1}}]}]},
    {"kind": "static", "affects": {"zone": "bz", "owner": "opp"},
     "if": CRYSTAL4, "mod": {"grant": ["enters_tapped"]}},
    {"kind": "static", "affects": "self",
     "if": CRYSTAL4, "mod": {"grant": ["opp_mana_tapped"]}},
]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_round374_disposition():
    rej = _reject_rows()
    assert len(rej) == 2011
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10303
    assert not (ids & set(rej))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dmrp21-5a")
    assert c is not None and c["abilities"] == FORM_5A
    assert not (c.get("source") or {}).get("unsupported")
    parse_card(c, TABLES)
    c = _conv_cache.find(CONVERTED, "dm23ex3-006")
    assert c is not None and c["abilities"] == FORM_006
    assert not (c.get("source") or {}).get("unsupported")
    parse_card(c, TABLES)
    left = {rid for rid, r in rej.items()
            if "opponent_cards_enter_tapped" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _zone_card(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p)
                if e.s.cards[c].defn == defn)


def _drive(e, plan, limit=900):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        if plan(d, _keys(d)):
            return d
    raise AssertionError("plan never stopped")


def test_registered_goagol_taps_opponent_entries(rules):
    e = _build(rules, {"bz": ["dmrp21-5a"]},
               {"hand": ["T005", "T003"],
                "mana": ["T005", "T001", "T001"]})
    state = {"charged": False, "played": False}

    def plan(d, keys):
        if state["played"] and d["kind"] == "charge" \
                and d.get("player") == 0:
            return True
        if d["kind"] == "charge" and d.get("player") == 1 \
                and not state["charged"] and "charge:T003" in keys:
            e.answer([keys.index("charge:T003")])
            state["charged"] = True
            return False
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
    assert e.s.cards[_zone_card(e, "mana", 1, "T003")].tapped is True
    assert e.s.cards[_zone_card(e, "bz", 1, "T005")].tapped is True


def test_registered_scorpio_gate_opens(rules):
    e = _build(rules, {"bz": ["dm23ex3-006"],
                       "mana": ["T001", "T001", "T001", "T001"]},
               {"hand": ["T005", "T009", "T003", "T004"],
                "mana": ["T005", "T009", "T001"]})
    mana0 = list(e.zlist("mana", 0))
    for cid in mana0[:3]:
        e.s.cards[cid].face_down = True
    state = {"p1turns": 0, "p0mays": 0, "played2": False}

    def plan(d, keys):
        if d["kind"] == "charge" and d.get("player") == 1:
            state["p1turns"] += 1
            if state["p1turns"] == 1 and "charge:T003" in keys:
                e.answer([keys.index("charge:T003")])
                return False
            if state["p1turns"] == 2 and "charge:T004" in keys:
                e.answer([keys.index("charge:T004")])
                return False
        if d["kind"] == "main" and d.get("player") == 1:
            if state["p1turns"] == 1 and "play:T005" in keys:
                e.answer([keys.index("play:T005")])
                return False
            if state["p1turns"] == 2 and "play:T009" in keys:
                e.answer([keys.index("play:T009")])
                state["played2"] = True
                return False
        if state["played2"] and d["kind"] == "charge" \
                and d.get("player") == 0:
            return True
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            return False
        if d["kind"] == "yes_no" and d.get("player") == 0:
            state["p0mays"] += 1
            e.answer([keys.index("yes" if state["p0mays"] >= 2
                                 else "no")])
            return False
        if d["kind"] == "choose_cards" and d.get("player") == 0:
            idx = next(i for i, o in enumerate(d["options"])
                       if o.get("cid") == mana0[3])
            e.answer([idx])
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        return False

    _drive(e, plan)
    assert e.s.cards[_zone_card(e, "mana", 1, "T003")].tapped is False
    assert e.s.cards[_zone_card(e, "bz", 1, "T005")].tapped is False
    assert e.s.cards[_zone_card(e, "mana", 1, "T004")].tapped is True
    assert e.s.cards[_zone_card(e, "bz", 1, "T009")].tapped is True


def test_registered_goagol_attack_discards_exactly_one(rules):
    """攻撃時誘発が二重登録されていないことの固定（submit の
    dedupe は完全一致のみで、ルール変換済みの chooser: random
    付き誘発と回答の無印誘発が両方残ったため、登録後に
    重複側を除去した）。"""
    e = _build(rules, {"bz": ["dmrp21-5a"]},
               {"hand": ["T001", "T003", "T004"],
                "shield": ["T001", "T001", "T001"]})
    state = {"before": None, "at_block": None}

    def plan(d, keys):
        if d["kind"] == "attack" and d.get("player") == 0 \
                and state["before"] is None \
                and "attack:dmrp21-5a:player" in keys:
            state["before"] = len(e.zlist("hand", 1))
            e.answer([keys.index("attack:dmrp21-5a:player")])
            return False
        if d["kind"] == "choose_shields" and state["before"] is not None:
            # 攻撃時誘発はシールドブレイクの時点で解決済み。
            # ブロック可能なクリーチャーが居ないと block 決定は
            # 出ず、choose_shields が最初の観測点になる
            state["at_block"] = len(e.zlist("hand", 1))
            return True
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        return False

    _drive(e, plan)
    assert state["at_block"] == state["before"] - 1
