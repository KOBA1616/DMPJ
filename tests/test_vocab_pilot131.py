"""語彙パイロット第131弾: powered_blocker（パワード・ブロッカー）。

「パワード・ブロッカー +N（ブロック中、このクリーチャーのパワーを+Nする）」は
mod: {power_when: {amount: N, when: blocking}} で表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-pb",
    "name": "試験堅壁獣",
    "types": ["creature"],
    "civs": ["light"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト"],
    "keywords": ["blocker"],
    "text": "ブロッカー\nパワード・ブロッカー +4000（ブロック中、このクリーチャーのパワーを+4000する）",
    "abilities": [
        {"kind": "static", "affects": "self",
         "mod": {"power_when": {"amount": 4000, "when": "blocking"}}},
    ],
    "source": {"official": "test-pb", "review": "pending"},
}


def test_powered_blocker_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"


def test_powered_blocker_power_when():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    pw = ab["mod"]["power_when"]
    assert pw["amount"] == 4000
    assert pw["when"] == "blocking"
