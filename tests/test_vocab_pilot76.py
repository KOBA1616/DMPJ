"""語彙パイロット第76弾: dynamo（ダイナモ）。

ダイナモは keywords.yaml に定義済みのキーワードとして表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-dyn",
    "name": "試験ダイナモ獣",
    "types": ["creature"],
    "civs": ["nature"],
    "cost": 3,
    "power": 3000,
    "races": ["テスト"],
    "keywords": ["dynamo"],
    "text": "ダイナモ（バトルが始まる時、あるいはこのクリーチャーで攻撃できる時、タップしてもよい。そうした場合、そのターンの終わりまで、このクリーチャーのパワーと能力を自分の他のダイナモ1体に加える）",
    "source": {"official": "test-dyn", "review": "pending"},
}


def test_dynamo_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    assert "dynamo" in card.keywords


def test_dynamo_keyword_defined():
    import yaml
    with open("data/rules/keywords.yaml") as f:
        kws = yaml.safe_load(f)["keywords"]
    assert "dynamo" in kws
