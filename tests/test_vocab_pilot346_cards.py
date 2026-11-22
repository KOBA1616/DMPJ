"""語彙パイロット第346弾の対象カード（実カード parse）。

対象は pure な cost_may_per_count 3件のうち2件で、ラウンド381で登録:
- dmc68-002 魔光帝フェルナンドVII世
- dmx16-057 龍素記号Lp エクスペリオン
（登録形は意図した形と完全一致）

dmex17-031 は対象外のまま rejects に残る（原文に
デュアル・ザンジバルとナイト・マジックの条項があるため）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
_conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from tests import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()
ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
REJECTS = ROOT / "data" / "cards" / "raw" / "rejects.jsonl"

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


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_registered():
    rows = _rows()
    assert len(rows) == 1996
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10317
    assert not (ids & set(rows))          # canonical 重なり0
    for tid, form in (("dmc68-002", FORM_002),
                      ("dmx16-057", FORM_057)):
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None and c["abilities"] == form
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    # dmex17-031 は対象外のまま残る
    assert rows["dmex17-031"].get("gaps") == ["cost_may_per_count"]


def test_proto_forms_match():
    assert proto_card("T1042")["abilities"] == FORM_002
    assert proto_card("T1043")["abilities"] == FORM_057
