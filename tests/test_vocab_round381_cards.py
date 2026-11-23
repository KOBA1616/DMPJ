"""再変換ラウンド381（第346弾 cost_may_per_count）の記録テスト。

- 新規登録2件: dmc68-002 魔光帝フェルナンドVII世 /
  dmx16-057 龍素記号Lp エクスペリオン（登録形は意図した
  形と完全一致）。
- converted 10,315→10,317 / rejects 1,998→1,996、
  canonical 重なり0・漏れ0。
- dmex17-031 は対象外（原文に他の未対応条項があるため）。
  reopen で一旦外れた行を原文どおり復帰させた（HEAD と
  バイト単位で一致することを確認済み）。cost_may_per_count
  の行はこの1件だけ残る。

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

COST_002 = {
    "kind": "static", "zone": "hand", "affects": "self",
    "mod": {"cost": {"amount": -1,
                     "count": {"zone": "graveyard", "owner": "you",
                               "filter": {"types": ["spell"]}}},
            "cost_min": 1},
}
ATK_002 = {
    "kind": "trigger",
    "when": {"event": "attack", "subject": "self"},
    "effect": [{"op": "modify",
                "select": {"zone": "bz", "owner": "opp",
                           "filter": {"types": ["creature"]},
                           "count": 1},
                "mod": {"power": {"amount": -1000,
                                  "count": {"zone": "graveyard",
                                            "owner": "you",
                                            "filter": {"types": ["spell"]}}}},
                "duration": "end_of_turn"}],
}
COST_057 = {
    "kind": "static",
    "affects": {"zone": "hand", "owner": "you",
                "filter": {"types": ["spell"], "civs": ["water"]}},
    "mod": {"cost": {"amount": -1,
                     "count": {"zone": "bz", "owner": "you",
                               "filter": {"race_has": "リキッド・ピープル"}}},
            "cost_min": 1},
}
FORM_002 = [COST_002, ATK_002]
FORM_057 = [COST_057]


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


def test_round381_disposition():
    rej = _reject_rows()
    assert len(rej) == 1996
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10317
    assert not (ids & set(rej))          # canonical 重なり0
    for tid, form in (("dmc68-002", FORM_002),
                      ("dmx16-057", FORM_057)):
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None and c["abilities"] == form
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    left = {rid for rid, r in rej.items()
            if "cost_may_per_count" in (r.get("gaps") or [])}
    assert left == {"dmex17-031"}, left   # 対象外の1件だけ残る


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


def test_registered_fernando_cost(rules):
    e = _build(rules, {"hand": ["dmc68-002"],
                       "graveyard": ["T003", "T003", "T003"],
                       "mana": ["T053", "T001", "T001", "T001",
                                "T001", "T001", "T001", "T001"]},
               {})
    d, keys = _drive_to_main(e)
    assert "play:dmc68-002" in keys       # 11-3=8 で召喚できる
    e2 = _build(rules, {"hand": ["dmc68-002"],
                        "graveyard": ["T003"] * 12,
                        "mana": ["T053"]},
                {})
    d, keys = _drive_to_main(e2)
    assert "play:dmc68-002" in keys       # 下限1でも召喚できる


def test_registered_expelion_discount(rules):
    e = _build(rules, {"bz": ["dmx16-057", "T384", "T694"],
                       "hand": ["T241"],
                       "mana": ["T009", "T001", "T001"]},
               {})
    d, keys = _drive_to_main(e)
    assert "play:T241" in keys            # 5-2=3 で唱えられる
