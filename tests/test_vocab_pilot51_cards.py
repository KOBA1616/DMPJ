"""語彙パイロット第51弾（フェーズ17）: 実カードの parse 確認。

対象: 《指示虫アロー・ワーム》DMRP16-016 — 唯一の能力が攻撃先の強制そのもの。
static {affects: self, mod: {must_be_attacked: true}} で表す。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "dmrp16-016",
    "name": "指示虫アロー・ワーム",
    "types": ["creature"],
    "civs": ["darkness"],
    "cost": 3,
    "power": 3000,
    "races": ["パラサイトワーム"],
    "mana": 1,
    "text": "相手のクリーチャーが攻撃する時、可能なら自分を攻撃する。",
    "abilities": [
        {"kind": "static", "affects": "self", "mod": {"must_be_attacked": True}},
    ],
    "source": {"official": "dmrp16-016", "review": "pending"},
}


def test_arrow_worm_parses():
    card = parse_card(CARD, TABLES, where="dmrp16-016")
    assert card.abilities and card.abilities[0]["mod"]["must_be_attacked"] is True
