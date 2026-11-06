"""語彙パイロット第124弾: holy_field（ホーリー・フィールド）。

「ホーリー・フィールド（自分のシールドの数が相手以上であれば、このクリーチャーは
次の能力を得る）」は、得る能力そのものに
if: {cmp: [{count: {zone: shield, owner: you}}, ">=", {count: {zone: shield, owner: opp}}]}
を付けて表す（新語彙なし。第73弾のゾーン枚数比較＋第97弾の条件つき能力）。
静的なら static の if、誘発なら trigger の if に付ける。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()
HF = {"cmp": [{"count": {"zone": "shield", "owner": "you"}}, ">=",
              {"count": {"zone": "shield", "owner": "opp"}}]}

CARD = {
    "id": "test-hf",
    "name": "試験予言者",
    "types": ["creature"],
    "civs": ["light"],
    "cost": 3,
    "power": 2000,
    "races": ["テスト"],
    "text": "ホーリー・フィールド（自分のシールドの数が相手以上であれば、このクリーチャーは次の能力を得る）このクリーチャーは「ブロッカー」を得る。",
    "abilities": [
        {"kind": "static", "affects": "self", "if": HF,
         "mod": {"grant": ["blocker"]}},
    ],
    "source": {"official": "test-hf", "review": "pending"},
}

CARD_TRIG = {
    "id": "test-hf2",
    "name": "試験宣凶師",
    "types": ["creature"],
    "civs": ["light"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト"],
    "text": "ホーリー・フィールド（自分のシールドの数が相手以上であれば、このクリーチャーは次の能力を得る）このクリーチャーをバトルゾーンに出した時、バトルゾーンにある相手のクリーチャーを２体まで選び、タップする。",
    "abilities": [
        {"kind": "trigger", "when": {"event": "summon", "subject": "self"}, "if": HF,
         "effect": [
             {"op": "tap", "select": {"zone": "bz", "owner": "opp", "count": 2, "up_to": True}},
         ]},
    ],
    "source": {"official": "test-hf2", "review": "pending"},
}


def test_holy_field_static_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["mod"]["grant"] == ["blocker"]
    assert ab["if"] == HF


def test_holy_field_trigger_parses():
    card = parse_card(CARD_TRIG, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["if"] == HF


def test_real_card_dm36_072_parses():
    """実カード: 予言者カーラ（ホーリー・フィールドでブロッカーを得る）。"""
    import glob
    import json
    raw = None
    for path in glob.glob('data/cards/raw/by_product/*.jsonl'):
        with open(path) as f:
            for line in f:
                rec = json.loads(line)
                if rec.get('id') == 'dm36-072':
                    raw = rec
    assert raw is not None
    assert 'ホーリー・フィールド' in raw['text']
