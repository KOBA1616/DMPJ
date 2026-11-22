"""語彙パイロット第334弾の対象カード検証（proto 形）。

対象は pure な play_from_deck_top 2件:
- dm22rp2x-002 アカシック・ヴィジョン（partial は本体のみ。
  本弾で allow static を構成。aliases [dm22rp2-002,
  dm22rp2x-002x] は partial 由来）
- dm26sd1-j009 斬龍電融 オロチリュウセイ（partial は
  スピードアタッカー付与 static を持ち、召喚許可だけが欠けて
  いた。aliases [dm23bd6-017, dm25sp2-005, dmrp17-s11] は
  partial 由来）
- dmrp22-005 は multi（reveal_stay＋play_from_deck_top）のため
  本弾の対象外。

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


def _partial(cid):
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            if r["id"] == cid:
                return r.get("partial")
    return None


def test_targets_still_in_rejects():
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    for t in ("dm22rp2x-002", "dm26sd1-j009"):
        assert t not in ids
        assert _partial(t) is not None, t


def test_partial_forms():
    p = _partial("dm22rp2x-002")
    assert p["name"] == "アカシック・ヴィジョン"
    assert not p.get("abilities")
    # aliases は partial には無く identity 側にある（submit 時に
    # 自動記録される）。reopen/submit 時の rejects 書き換えで
    # partial の aliases は消えるため、ここでは assert しない
    p = _partial("dm26sd1-j009")
    assert p["name"] == "斬龍電融 オロチリュウセイ"
    assert p["abilities"] == [SPEED_ALL]
    assert p["keywords"] == ["ex_life", "triple_breaker"]


def test_proto_forms_match():
    c = proto_card("T1013")
    assert c["abilities"] == FORM_002
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = proto_card("T1014")
    assert c["abilities"] == FORM_J009
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 2
