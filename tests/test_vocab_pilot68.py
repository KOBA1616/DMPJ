"""語彙パイロット第68弾: wave_striker（ウェーブストライカー）。

「ウェーブストライカー」は既存のキーワード。条件付き能力は
if: {cmp: [{count: {..., filter: {keyword: wave_striker}}}, ">=", 2]} で表す。新語彙なし。
"""
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-ws",
    "name": "試験波打獣",
    "types": ["creature"],
    "civs": ["water"],
    "cost": 4,
    "power": 4000,
    "races": ["テスト"],
    "keywords": ["wave_striker"],
    "text": "ウェーブストライカー（「ウェーブストライカー」を持つクリーチャーが他に２体以上あれば、このクリーチャーに次の能力を与える）自分のクリーチャーすべてのパワーを+5000する。",
    "abilities": [
        {"kind": "static",
         "if": {"cmp": [{"count": {"zone": "bz", "owner": "any", "other": True,
                                   "filter": {"keyword": "wave_striker"}}}, ">=", 2]},
         "affects": {"zone": "bz", "owner": "you",
                     "filter": {"types": ["creature"]}},
         "mod": {"power": 5000}},
    ],
    "source": {"official": "test-ws", "review": "pending"},
}


def test_wave_striker_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    assert "wave_striker" in card.keywords
    ab = card.abilities[0]
    assert "cmp" in ab["if"]


def test_wave_striker_keyword_exists():
    import yaml
    with open("data/rules/keywords.yaml") as f:
        kw = yaml.safe_load(f)
    assert "wave_striker" in kw.get("keywords", {})
