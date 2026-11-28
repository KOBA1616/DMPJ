"""語彙パイロット第327弾の対象カード検証（登録形）。

first_attack_end の純粋2件（dm26ex4-cho025 / dm26sd1-i004）は
同一カード瞬閃と疾駆と双撃の決断の2印刷で、canon_id は
dm26ex4-cho025。両行とも partial あり（unsupported の断片だけ）。
by_product で原文照合済み（正本は cho025 の文面。sd1-i004 の
文面はモード2に注釈が付くが、注釈はデータモデルに無いため正本の
文面で登録する）。submit 時に aliases 10件を自動記録
（dm26sd1-i004 を含む）。

第327弾の結論はドリフト（追加語彙なし）。modal op が「次の中から
２回選ぶ（同じものを選んでもよい）」をそのまま表す（count: 2,
repeat: true）。モード3の first_attack_end は once 既定の遅延誘発。

注: first_attack_end は multi-gap 行 dmex15-b019 滅亡の光にも残る
（gaps [filter_not_race, first_attack_end]）。「それぞれの最初の
攻撃」は once_per_turn 付きの付与型誘発で書く見込みで、第328弾の
候補。今回は純粋2件のみを対象とする。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
_conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
REJECTS = ROOT / "data" / "cards" / "raw" / "rejects.jsonl"
TABLES = load_tables()

GAP = "first_attack_end"

FORM = [
    {"op": "modal", "count": 2, "repeat": True,
     "modes": [
         [{"op": "play_free",
           "select": {"zone": "hand", "owner": "you",
                      "filter": {"types": ["creature"], "cost_le": 3},
                      "count": 1}}],
         [{"op": "choose",
           "select": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["creature"]}, "count": 1},
           "as": "c"},
          {"op": "modify", "select": {"ref": "c", "count": "all"},
           "mod": {"grant": ["speed_attacker"]},
           "duration": "end_of_turn"}],
         [{"op": "choose",
           "select": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["creature"]}, "count": 1},
           "as": "chosen"},
          {"op": "delayed_trigger",
           "when": {"event": "attack_end", "subject": {"ref": "chosen"}},
           "effect": [{"op": "untap", "select": {"ref": "chosen"}}],
           "duration": "end_of_turn"}],
     ]},
]


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_registered():
    rows = _rows()
    assert len(rows) <= 2039  # 件数は減る一方（スナップショット固定をやめた）
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10276  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    for tid in ("dm26ex4-cho025", "dm26sd1-i004"):
        assert tid not in rows, tid
    assert "dm26ex4-cho025" in ids
    # dm26sd1-i004 は正本の aliases に記録されるだけで、カードとしては
    # 登録されない（canon_id は dm26ex4-cho025）
    c = _conv_cache.find(CONVERTED, "dm26ex4-cho025")
    assert c is not None
    assert c["name"] == "瞬閃と疾駆と双撃の決断"
    assert c["spell"] == FORM
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == [
        "dm22bd2-014", "dm23rp2-tr08", "dm23rp2x-tr08", "dm23rp4-sp2",
        "dm23rp4x-sp2", "dm23sd3-002", "dm26sd1-i004", "dmart04-003",
        "dmex19-012", "dmrp11-007"]
    d = parse_card(c, TABLES)
    assert len(d.spell) == 1 and d.spell[0]["op"] == "modal"
    # 純粋 first_attack_end は残り0件でファミリー解消。
    # multi-gap の dmex15-b019 は第328弾の候補として残る
    left = {rid for rid, r in rows.items()
            if (r.get("gaps") or []) == [GAP]}
    assert left == set(), left
    assert rows["dmex15-b019"].get("gaps") == ["filter_not_race",
                                               "first_attack_end"]


def test_proto_forms_match():
    c996 = proto_card("T996")
    assert c996["spell"] == FORM
    d = parse_card(c996, TABLES)
    assert len(d.spell) == 1 and d.spell[0]["op"] == "modal"
