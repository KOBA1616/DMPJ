"""語彙パイロット第93弾: soul（ソウル種族フィルタ）。

ソウルは種族（H・ソウル等）として any_of の race_has で表す。新語彙なし。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

SOUL_FILTER = {"any_of": [{"race_has": "H・ソウル"}, {"race_has": "M・ソウル"},
                          {"race_has": "E・ソウル"}, {"race_has": "K・ソウル"},
                          {"race_has": "W・ソウル"}, {"race_has": "B・ソウル"}]}

CARD = {
    "id": "test-soul",
    "name": "試験ソウル獣",
    "types": ["creature"],
    "civs": ["light"],
    "cost": 4,
    "power": 3000,
    "races": ["テスト", "H・ソウル"],
    "text": "バトルゾーンにある自分の他のソウルクリーチャーすべてのパワーは+1000される。",
    "abilities": [
        {"kind": "static",
         "affects": {"zone": "bz", "owner": "you", "other": True, "filter": SOUL_FILTER},
         "mod": {"power": 1000}},
    ],
    "source": {"official": "test-soul", "review": "pending"},
}


def test_soul_filter_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "static"


def test_soul_filter_contents():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    races = [x["race_has"] for x in ab["affects"]["filter"]["any_of"]]
    assert "H・ソウル" in races and "B・ソウル" in races
