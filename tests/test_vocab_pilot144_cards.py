"""語彙パイロット第144弾: 代表カードの手変換が parse_card を通ること。

- 地獄万力: 「バトルゾーンにある相手のクリーチャーを、パワーの合計が8000以下になるように好きな数選ぶ。
  相手はそれを持ち主の墓地に置く」（持ち主の墓地に置く、は destroy op の通常の行き先で表現する）
- プラスワン・フレーム: S・トリガー＋「パワーの合計が5000以下になるように好きな数選び、破壊する」＋ドロー
"""
import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    """
id: dmc27-017
name: 地獄万力
types: [spell]
civs: [fire]
cost: 7
mana: 1
text: バトルゾーンにある相手のクリーチャーを、パワーの合計が8000以下になるように好きな数選ぶ。相手はそれを持ち主の墓地に置く。
spell:
  - {op: destroy, select: {zone: bz, owner: opp, filter: {types: [creature]}, total_power_le: 8000}}
source: {official: dmc27-017, review: pending}
""",
    """
id: dm26rp1-070
name: プラスワン・フレーム
types: [spell]
civs: [fire]
cost: 4
mana: 1
keywords: [s_trigger]
text: S・トリガー（このカードを自分のシールドゾーンから手札に加える時、コストを支払わずにすぐ実行してもよい）相手のクリーチャーを、パワーの合計が5000以下になるように好きな数選び、破壊する。カードを１枚引く。
spell:
  - {op: destroy, select: {zone: bz, owner: opp, filter: {types: [creature]}, total_power_le: 5000}}
  - {op: draw, player: you, count: 1}
source: {official: dm26rp1-070, review: pending}
""",
]


def test_pilot144_cards_parse():
    for text in CARDS:
        parse_card(yaml.safe_load(text), TABLES)
