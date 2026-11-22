"""再変換ラウンド388（第353弾
trigger_when_opponent_plays_without_paying）の記録テスト。

- 新規登録2件: dm22rp2x-020 チッタ・ペロルの冠 /
  dm23rp2x-033 ゼンツー（登録形は意図した形と完全一致。
  aliases の自動記録は rejects 行ではない）。
- converted 10,330→10,332 / rejects 1,982→1,980、
  canonical 重なり0・漏れ0。pure は解消し、この gap は
  multi の dm26rp2-s011 にだけ残る。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない（第319弾以降の作法）。
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


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_round388_disposition():
    rej = _reject_rows()
    assert len(rej) == 1980
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10332
    assert not (ids & set(rej))          # canonical 重なり0
    for tid, form in (("dm22rp2x-020", FORM_020),
                      ("dm23rp2x-033", FORM_033)):
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None and c["abilities"] == form
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    pure_left = {rid for rid, r in rej.items()
                 if r.get("gaps") == [
                     "trigger_when_opponent_plays_without_paying"]}
    assert pure_left == set(), pure_left


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _drive_lacrima_entry(e):
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


def test_registered_perol_reacts(rules):
    p0, p1 = _lacrima_setup({"bz": ["dm22rp2x-020"], "hand": ["T005"]})
    e = _build(rules, p0, p1)
    _drive_lacrima_entry(e)
    assert "dm22rp2x-020" in [e.s.cards[c].defn
                              for c in e.zlist("graveyard", 0)]
    assert "T005" in [e.s.cards[c].defn for c in e.bz_tops(0)]


def test_registered_zentoo_mekurade(rules):
    p0, p1 = _lacrima_setup({"bz": ["dm23rp2x-033"],
                             "deck": ["T1062", "T1062", "T1062",
                                      "T002", "T002"]})
    e = _build(rules, p0, p1)
    _drive_lacrima_entry(e)
    assert "T1062" in [e.s.cards[c].defn for c in e.bz_tops(0)]
