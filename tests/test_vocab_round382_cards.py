"""再変換ラウンド382（第347弾 up_to_cost_reduction）の記録テスト。

- 新規登録2件: dmbd02-014 西南の超人 / dm39-018 大地幻獣
  ガガマル（登録形は意図した形と完全一致）。
- converted 10,317→10,319 / rejects 1,996→1,994、
  canonical 重なり0・漏れ0。
- dm23rp4x-tf03 は対象外（partial が完全に空）。reopen で
  一旦外れた行を原文どおり復帰させた（HEAD とバイト単位で
  一致することを確認済み）。up_to_cost_reduction の行は
  この1件だけ残る。

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

COST_014 = {
    "kind": "static",
    "affects": {"zone": "hand", "owner": "you",
                "filter": {"races": ["ジャイアント"]}},
    "mod": {"cost": -2},
}
SABER_014 = {
    "kind": "replace", "optional": True,
    "when": {"event": "move", "to": "graveyard", "reason": "destroy",
             "subject": {"owner": "you",
                         "filter": {"races": ["ジャイアント"]},
                         "other": True}},
    "instead": [{"op": "destroy", "select": {"ref": "self", "count": 1}}],
}
COST_018 = {
    "kind": "static",
    "affects": {"zone": "mana", "owner": "you",
                "filter": {"types": ["creature"],
                           "keyword": "summon_from_mana"}},
    "mod": {"cost": -2, "cost_min": 1},
}
FORM_014 = [COST_014, SABER_014]
FORM_018 = [COST_018]


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


def test_round382_disposition():
    rej = _reject_rows()
    assert len(rej) == 1994
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10319
    assert not (ids & set(rej))          # canonical 重なり0
    for tid, form in (("dmbd02-014", FORM_014),
                      ("dm39-018", FORM_018)):
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None and c["abilities"] == form
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    left = {rid for rid, r in rej.items()
            if "up_to_cost_reduction" in (r.get("gaps") or [])}
    assert left == {"dm23rp4x-tf03"}, left   # 対象外の1件だけ残る


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _drive_to_main(e, player=0, limit=300):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] == "main" and d.get("player") == player:
            return d, _keys(d)
        if "pass" in _keys(d):
            e.answer([_keys(d).index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("main never came")


def test_registered_seinan_discount(rules):
    e = _build(rules, {"bz": ["dmbd02-014"], "hand": ["T356"],
                       "mana": ["T001"] * 5}, {})
    d, keys = _drive_to_main(e)
    assert "play:T356" in keys            # ジャイアント 7-2=5


def test_registered_gagamaru_discount(rules):
    e = _build(rules, {"bz": ["dm39-018"],
                       "mana": ["T086", "T001"]}, {})
    d, keys = _drive_to_main(e)
    assert "play:T086:msum" in keys       # マナ爆誕 2-2→下限1
    e2 = _build(rules, {"bz": ["dm39-018"],
                        "mana": ["T730", "T001", "T001", "T001"]}, {})
    cid = next(c for c in e2.zlist("mana", 0)
               if e2.s.cards[c].defn == "T730")
    assert e2.chars_ro(cid)["pay_cost"] == 3   # 5-2=3
