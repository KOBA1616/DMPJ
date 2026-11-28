"""語彙パイロット第324弾の対象カード検証（登録形）。

breaks_equal_creature_count は dm24ex2-024 / dm26ex4-cho021
（同名カード ジョジョジョ・マキシマムの2印刷）の純粋2件だった。
dm24ex2-024 は旧印刷で canon_id は dm26ex4-cho021（identity 実測）。
aliases_for（ジョジョジョ・マキシマム, dm26ex4-cho021）は
[dm24ex2-024, dmex19-002, dmrp04m-001]。submit の原文コーパス
（canonical_rows）は正本だけを通すため、dm24ex2-024 は直接は
提出できない。reopen breaks_equal_creature_count で dm24ex2-024
の行は外れ済み（alias 畳み込み1件）。dm26ex4-cho021 を1件だけ
提出し、validate の aliases_for が source.aliases に自動付与した
（第292弾の c48-sec001 / 第293弾の dm26ex4-sec012 と同じ扱い）。

第324弾の結論はエンジン拡張（スキーマのみ）。breaks_add の辞書形に
{var: 名前} を許可するスキーマ拡張（dmsim/cards/defs.py Checker.mod
と dmsim/cards/schema.py。card.schema.json は `python -m
dmsim.cards.schema` で再生成。提出時の _schema_check は
card.schema.json を読むため、defs.py だけでは足りず提出で弾かれた）。
実行時は op_modify の _bake_refs が生成時に数値へ焼くため core.py
の変更は不要。

登録形（dm26ex4-cho021）: 無色・コスト9・マナ1の呪文。
free_if {cmp: [{count: {zone: [bz, mana], owner: you,
filter: {race_has: ジョーカーズ}}}, '>=', 11]} +
[set_var n {count: {zone: bz, owner: you, filter: {types: [creature]}}};
choose {zone: bz, owner: you, filter: {types: [creature]}, count: 1}
as chosen; modify {ref: chosen} {breaks_add: {var: n}} end_of_turn;
delayed_trigger {event: attack, subject: {ref: chosen}} ->
[modify {zone: hand, owner: opp, filter: {types: [spell]}}
{deny: [cast]} during_attack] end_of_turn, once: false]。

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

GAP = "breaks_equal_creature_count"

FREE_IF = {
    "cmp": [{"count": {"zone": ["bz", "mana"], "owner": "you",
                       "filter": {"race_has": "ジョーカーズ"}}},
            ">=", 11]}

SPELL = [
    {"op": "set_var", "name": "n",
     "value": {"count": {"zone": "bz", "owner": "you",
                         "filter": {"types": ["creature"]}}}},
    {"op": "choose",
     "select": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}, "count": 1},
     "as": "chosen"},
    {"op": "modify", "select": {"ref": "chosen"},
     "mod": {"breaks_add": {"var": "n"}}, "duration": "end_of_turn"},
    {"op": "delayed_trigger",
     "when": {"event": "attack", "subject": {"ref": "chosen"}},
     "effect": [{"op": "modify",
                 "select": {"zone": "hand", "owner": "opp",
                            "filter": {"types": ["spell"]}},
                 "mod": {"deny": ["cast"]},
                 "duration": "during_attack"}],
     "duration": "end_of_turn", "once": False},
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
    assert len(rows) <= 2045  # 件数は減る一方（スナップショット固定をやめた）
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10271  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    # 正本 dm26ex4-cho021 が登録され、旧印刷 dm24ex2-024 は独立
    # エントリではなく source.aliases に畳み込まれた
    assert "dm26ex4-cho021" in ids and "dm26ex4-cho021" not in rows
    assert "dm24ex2-024" not in ids and "dm24ex2-024" not in rows
    c = _conv_cache.find(CONVERTED, "dm26ex4-cho021")
    assert c is not None
    assert c["name"] == "ジョジョジョ・マキシマム"
    assert c["free_if"] == FREE_IF
    assert c["spell"] == SPELL
    assert (c.get("source") or {}).get("aliases") == [
        "dm24ex2-024", "dmex19-002", "dmrp04m-001"]
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d.free_if is not None
    assert len(d.spell) == 4
    # breaks_equal_creature_count は残り0件でファミリー解消
    left = {rid for rid, r in rows.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left


def test_proto_forms_match():
    for cid in ("T990", "T991"):
        card = proto_card(cid)
        assert card["free_if"] == FREE_IF, cid
        assert card["spell"] == SPELL, cid
        d = parse_card(card, TABLES)
        assert d.free_if is not None
        assert len(d.spell) == 4
