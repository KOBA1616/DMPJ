"""語彙パイロット第38弾: 代表カードの手変換が parse_card を通ること。

- めった切り・スクラッパー: 「相手のクリーチャーを、コストの合計が６以下になるように好きな数選び、破壊する」
"""
import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    """
id: dmex02-040
name: めった切り・スクラッパー
types: [spell]
civs: [fire]
cost: 7
mana: 1
keywords: [s_trigger]
text: S・トリガー（この呪文をシールドゾーンから手札に加える時、コストを支払わずにすぐ唱えてもよい）相手のクリーチャーを、コストの合計が６以下になるように好きな数選び、破壊する。
spell:
  - {op: destroy, select: {zone: bz, owner: opp, filter: {types: [creature]}, total_cost_le: 6}}
source: {official: dmex02-040, review: pending}
""",
]


def test_pilot38_cards_parse():
    for text in CARDS:
        parse_card(yaml.safe_load(text), TABLES)
