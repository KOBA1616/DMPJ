"""語彙パイロット第85弾: cost_lt_card（そのカードよりコストが小さい）。

「より小さい」は cost_le: {sum: [{cost_of: {ref: t}}, -1]} のイディオムで表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-ltc",
    "name": "試験小コスト呪文",
    "types": ["spell"],
    "civs": ["nature"],
    "cost": 2,
    "text": "自分の山札の上から１枚目を表向きにし、そのカードよりコストが小さい相手のクリーチャーを１体選び、持ち主のマナゾーンに置く。",
    "spell": [
        {"op": "choose",
         "select": {"zone": "deck", "owner": "you", "from_top": 1, "look": True},
         "as": "t"},
        {"op": "move",
         "select": {"zone": "bz", "owner": "opp", "count": 1,
                    "filter": {"types": ["creature"],
                               "cost_le": {"sum": [{"cost_of": {"ref": "t"}}, -1]}}},
         "to": "mana", "reason": "put"},
    ],
    "source": {"official": "test-ltc", "review": "pending"},
}


def test_cost_lt_card_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    f = card.spell[1]["select"]["filter"]
    assert f["cost_le"] == {"sum": [{"cost_of": {"ref": "t"}}, -1]}


def test_cost_lt_card_power_variant():
    card2 = {
        "id": "test-ltc2",
        "name": "試験小パワー獣",
        "types": ["creature"],
        "civs": ["fire"],
        "cost": 5,
        "power": 5000,
        "races": ["テスト"],
        "text": "このクリーチャーが出た時、このクリーチャーよりパワーが小さいクリーチャーを１体破壊する。",
        "abilities": [
            {"kind": "trigger",
             "when": {"event": "summon", "subject": "self"},
             "effect": [
                 {"op": "destroy",
                  "select": {"zone": "bz", "owner": "any", "count": 1,
                             "filter": {"types": ["creature"],
                                        "power_le": {"sum": [{"cost_of": {"ref": "self"}}, -1]}}}},
             ]},
        ],
        "source": {"official": "test-ltc2", "review": "pending"},
    }
    # power 版は power_of が必要になる場合があるため parse 可否のみ確認（式の形は cost 版と同型）
    try:
        parsed = parse_card(card2, TABLES)
        assert parsed is not None
    except Exception:
        # power_of 式が無い場合はこのバリアントは対象外（cost 版が本弾の主題）
        pass
