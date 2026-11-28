"""語彙パイロット第334弾の対象カード検証（proto 形）。

対象は pure な play_from_deck_top 2件で、ラウンド369で登録済み:
- dm22rp2x-002 アカシック・ヴィジョン（partial は本体のみ。
  本弾で allow static を構成。submit 時に aliases
  [dm22rp2-002, dm22rp2x-002x] が自動記録されたが rejects 行
  ではない）
- dm26sd1-j009 斬龍電融 オロチリュウセイ（partial は
  スピードアタッカー付与 static を持ち、召喚許可だけが欠けて
  いた。submit 時に aliases [dm23bd6-017, dm25sp2-005,
  dmrp17-s11] が自動記録されたが rejects 行ではない）
- dmrp22-005 は multi（reveal_stay＋play_from_deck_top）のため
  本弾の対象外で rejects に残る。

結論はエンジン拡張（山札の上からのプレイ。第334弾の本体テスト
参照）: permissions.yaml に summon/cast/generate_from_deck_top
を追加し、_play_options に山札の一番上だけを見るブロックを追加。
h_play は from_zone を汎用に読むため変更は要らず、summon_once
の消費条件に "deck" を加えただけ。

確立形:
- dm22rp2x-002: {kind: static, affects: {zone: deck, owner: you,
  filter: {types: [spell, tamaseed]}}, if: {is_turn: you},
  mod: {allow: [{action: cast_from_deck_top},
                {action: generate_from_deck_top}]}}
- dm26sd1-j009: 既存のスピードアタッカー付与 static＋
  {kind: static, affects: {zone: deck, owner: you,
  filter: {types: [creature]}}, if: {is_turn: you},
  mod: {allow: [{action: summon_from_deck_top, once: true}]}}
  （「クリーチャーを１体」は once: true で読む）

「いつでも見てもよい」は既存12枚と同じく原文のみ。

play_from_deck_top は multi の dmrp22-005 だけが残る。

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

ALLOW_002 = {
    "kind": "static",
    "affects": {"zone": "deck", "owner": "you",
                "filter": {"types": ["spell", "tamaseed"]}},
    "if": {"is_turn": "you"},
    "mod": {"allow": [{"action": "cast_from_deck_top"},
                      {"action": "generate_from_deck_top"}]}}

SPEED_ALL = {
    "kind": "static",
    "affects": {"owner": "you", "filter": {"types": ["creature"]}},
    "mod": {"grant": ["speed_attacker"]}}

ALLOW_J009 = {
    "kind": "static",
    "affects": {"zone": "deck", "owner": "you",
                "filter": {"types": ["creature"]}},
    "if": {"is_turn": "you"},
    "mod": {"allow": [{"action": "summon_from_deck_top", "once": True}]}}

FORM_002 = [ALLOW_002]
FORM_J009 = [SPEED_ALL, ALLOW_J009]


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_registered():
    rows = _rows()
    assert len(rows) <= 2026  # 件数は減る一方（スナップショット固定をやめた）
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) >= 10288  # 件数は増える一方
    assert not (ids & set(rows))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dm22rp2x-002")
    assert c is not None
    assert c["abilities"] == FORM_002
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == ["dm22rp2-002",
                                                     "dm22rp2x-002x"]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = _conv_cache.find(CONVERTED, "dm26sd1-j009")
    assert c is not None
    assert c["abilities"] == FORM_J009
    assert not (c.get("source") or {}).get("unsupported")
    assert (c.get("source") or {}).get("aliases") == ["dm23bd6-017",
                                                     "dm25sp2-005",
                                                     "dmrp17-s11"]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 2
    left = {rid for rid, r in rows.items()
            if "play_from_deck_top" in (r.get("gaps") or [])}
    assert left == {"dmrp22-005"}, left    # multi のため残る


def test_proto_forms_match():
    c = proto_card("T1013")
    assert c["abilities"] == FORM_002
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = proto_card("T1014")
    assert c["abilities"] == FORM_J009
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 2
