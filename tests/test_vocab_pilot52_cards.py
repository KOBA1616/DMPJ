"""語彙パイロット第52弾（フェーズ17）: 実カードの parse 確認。

対象: 《戦慄の魔女 アリス / 神にも届く旋律》DM23EX1-034 — 呪文面の
「S・バック：アウトレイジ」が、面フィールド s_back への filter 指定
（{race_has: アウトレイジ}）で表せるようになった。ツインパクトでは
カード全体の s_back に面の値が集約されることも確認する。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "dm23ex1-034",
    "name": "戦慄の魔女 アリス / 神にも届く旋律",
    "text": "S・バック：アウトレイジ（アウトレイジを自分のシールドゾーンから手札に加える時、そのカードを捨ててもよい。そうしたら、コストを支払わずにこの呪文を唱える）",
    "faces": [
        {"name": "戦慄の魔女 アリス", "types": ["creature"], "civs": ["water"], "cost": 4,
         "power": 3000, "races": ["マジック・アウトレイジMAX"], "mana": 1,
         "keywords": ["last_burst"],
         "abilities": [
             {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
              "effect": [{"op": "may", "body": [{"op": "draw", "count": 3}]}]}]},
        {"name": "神にも届く旋律", "types": ["spell"], "civs": ["water"], "cost": 6,
         "races": ["マジック・ソング"], "mana": 1,
         "s_back": {"race_has": "アウトレイジ"},
         "spell": [{"op": "mekurade", "look": 3, "cost_le": 8,
                    "filter": {"race_has": "アウトレイジ"}}]},
    ],
    "source": {"official": "dm23ex1-034", "review": "pending"},
}


def test_alice_s_back_race_parses():
    card = parse_card(CARD, TABLES, where="dm23ex1-034")
    assert card.faces[1].s_back == {"race_has": "アウトレイジ"}
    assert card.s_back == {"race_has": "アウトレイジ"}
