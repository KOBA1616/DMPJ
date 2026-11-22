"""再変換ラウンド383（第348弾 invasion_zero）の記録テスト。

- 新規登録3件: dmbd21-018 ZEROの侵略 ブラックアウト /
  dmd35-011 ZEROの暴走 デッドリー・ハイウェイ /
  promoy15-035 禁断の月 ドキンダムーン（登録形は意図した
  形と完全一致）。
- converted 10,319→10,322 / rejects 1,994→1,991、
  canonical 重なり0・漏れ0。
- invasion_zero は multi の dm24ex3-tf13 にだけ残る。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない（第319弾以降の作法）。
無償登場は fixture 呪文 T1049 でターン中に起こす（誘発の if は
収集時に評価されるため、ターン終わりの誘発同士は見合えない）。
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


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_round383_disposition():
    rej = _reject_rows()
    assert len(rej) == 1991
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10322
    assert not (ids & set(rej))          # canonical 重なり0
    for tid, form in (("dmbd21-018", FORM_018),
                      ("dmd35-011", FORM_011),
                      ("promoy15-035", FORM_035)):
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None and c["abilities"] == form
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    left = {rid for rid, r in rej.items()
            if "invasion_zero" in (r.get("gaps") or [])}
    assert left == {"dm24ex3-tf13"}, left


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _opp_unpaid_turn(e, state):
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "yes_no" and d.get("player") == 0:
            state["zero_asked"] = True
            e.answer([keys.index("yes")])
            continue
        if d["kind"] == "charge" and d.get("player") == 0:
            state["p0_charges"] = state.get("p0_charges", 0) + 1
            if state["p0_charges"] >= 2:
                return
        if d["kind"] == "main" and d.get("player") == 1 \
                and "play:T1049" in keys:
            e.answer([keys.index("play:T1049")])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "choose_cards" and d.get("player") == 1:
            pick = [i for i, o in enumerate(d["options"])
                    if o["key"].startswith("hand:T005")]
            e.answer(pick[:1] if pick else list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def test_registered_blackout_zero(rules):
    e = _build(rules, {"hand": ["dmbd21-018"]},
               {"hand": ["T1049", "T005"], "mana": ["T001"]})
    state = {}
    _opp_unpaid_turn(e, state)
    assert state.get("zero_asked")
    assert "dmbd21-018" in [e.s.cards[c].defn for c in e.bz_tops(0)]


def test_registered_highway_zero(rules):
    e = _build(rules, {"hand": ["dmd35-011"]},
               {"hand": ["T1049", "T005"], "mana": ["T001"]})
    state = {}
    _opp_unpaid_turn(e, state)
    assert state.get("zero_asked")
    assert "dmd35-011" in [e.s.cards[c].defn for c in e.bz_tops(0)]
