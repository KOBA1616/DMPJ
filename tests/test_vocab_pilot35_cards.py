"""語彙パイロット第35弾: 代表カードの手変換が parse_card を通ること。

- 巡霊者ソルディアス: 「攻撃するかわりに、このクリーチャーとマナ8枚をタップして使う」複合コストの起動型能力
"""
import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    """
id: dm24-042
name: 巡霊者ソルディアス
types: [creature]
civs: [light]
cost: 3
power: 2500
races: [コスモ・ウォーカー]
mana: 1
text: このクリーチャーで攻撃するかわりに、このクリーチャーと自分のマナゾーンのタップされていないカードを８枚タップして、次の能力を使ってもよい。呪文を１枚、自分の墓地から手札に戻す。
abilities:
  - kind: activate
    cost: {tap: self, tap_mana: 8}
    effect:
      - {op: move, select: {zone: graveyard, owner: you, filter: {types: [spell]}, count: 1}, to: hand, reason: return}
source: {official: dm24-042, review: pending}
""",
]


def test_pilot35_cards_parse():
    for text in CARDS:
        parse_card(yaml.safe_load(text), TABLES)
