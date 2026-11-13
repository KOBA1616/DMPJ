"""語彙パイロット第88弾: grant_based_on_own_power_threshold（自分のパワー条件で得る）。

「パワーがN以上のとき〜を得る」は static + if: {exists: {ref: self, filter: {power_ge: N}}} で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-gpt",
    "name": "試験閾値獣",
    "types": ["creature"],
    "civs": ["nature"],
    "cost": 5,
    "power": 4000,
    "races": ["テスト"],
    "text": "このクリーチャーは、パワーが6000以上のとき、「W・ブレイカー」を得る。",
    "abilities": [
        {"kind": "static", "affects": "self",
         "if": {"exists": {"ref": "self", "filter": {"power_ge": 6000}}},
         "mod": {"grant": ["double_breaker"]}},
    ],
    "source": {"official": "test-gpt", "review": "pending"},
}


def test_power_threshold_grant_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"
    assert ab["mod"]["grant"] == ["double_breaker"]


def test_power_threshold_condition():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["if"]["exists"]["filter"]["power_ge"] == 6000
