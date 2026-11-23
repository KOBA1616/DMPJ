"""再変換ラウンド387（第352弾 optional_cost_reduction_per_count）
の記録テスト。

- 新規登録2件: dm31-033 爆獣パンダ・ブーリン /
  dmbd16-007 聖霊龍騎セイント・ボルシャック
  （登録形は意図した形と完全一致。dmbd16-007 へ
  aliases 2件の自動記録は rejects 行ではない）。
- converted 10,328→10,330 / rejects 1,984→1,982、
  canonical 重なり0・漏れ0。ファミリー解消。

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

COST_033 = {"kind": "static", "zone": "hand", "affects": "self",
            "mod": {"cost": {"amount": -1,
                             "count": {"zone": "mana", "owner": "you",
                                       "filter": {"types": ["spell"]}}},
                    "cost_min": 1}}
COST_007 = {"kind": "static", "zone": "hand", "affects": "self",
            "mod": {"cost": {"amount": -1,
                             "count": {"zone": "graveyard", "owner": "you",
                                       "filter": {"any_of": [
                                           {"races": ["エンジェル・コマンド"]},
                                           {"races": ["アーマード・ドラゴン"]}]}}},
                    "cost_min": 1}}
POWER_WHEN_007 = {"kind": "static", "affects": "self",
                  "mod": {"power_when": {"amount": 4000,
                                         "when": "attacking"}}}
FORM_033 = [COST_033]
FORM_007 = [POWER_WHEN_007, COST_007]  # 登録形は submit の prepend で partial 由来が先頭


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


def test_round387_disposition():
    rej = _reject_rows()
    assert len(rej) == 1982
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10330
    assert not (ids & set(rej))          # canonical 重なり0
    for tid, form in (("dm31-033", FORM_033), ("dmbd16-007", FORM_007)):
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None and c["abilities"] == form
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    left = {rid for rid, r in rej.items()
            if "optional_cost_reduction_per_count" in (r.get("gaps") or [])}
    assert left == set(), left


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1=None):
    return scenario.build(rules, {"p0": p0, "p1": p1 or {},
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _play_options(e, target):
    p0_charges = 0
    for _ in range(300):
        d = e.advance()
        if d is None:
            return False
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "charge" and d.get("player") == 0:
            p0_charges += 1
            if p0_charges >= 2:
                return False
        if d["kind"] == "main" and d.get("player") == 0:
            return f"play:{target}" in keys
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("main never reached")


def test_registered_panda_discount(rules):
    e = _build(rules, {"hand": ["dm31-033"],
                       "mana": ["T003", "T003", "T003",
                                "T001", "T001", "T001"]})
    assert _play_options(e, "dm31-033")          # 9-3=6 で出せる
    e = _build(rules, {"hand": ["dm31-033"],
                       "mana": ["T003", "T003",
                                "T001", "T001", "T001", "T001"]})
    assert not _play_options(e, "dm31-033")      # 9-2=7 では出せない


def test_registered_saint_bolshack_discount(rules):
    e = _build(rules, {"hand": ["dmbd16-007"],
                       "mana": ["T004", "T004", "T004",
                                "T005", "T005", "T005", "T005"],
                       "graveyard": ["T156", "T156"]})
    assert _play_options(e, "dmbd16-007")        # 9-2=7 で出せる
    e = _build(rules, {"hand": ["dmbd16-007"],
                       "mana": ["T004", "T004", "T004",
                                "T005", "T005", "T005", "T005"],
                       "graveyard": ["T156"]})
    assert not _play_options(e, "dmbd16-007")    # 9-1=8 では出せない
