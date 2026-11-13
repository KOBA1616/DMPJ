"""語彙パイロット第145弾: 代表カードの手変換が parse_card を通ること。

- 魔誕哀樹シンバーロ: S・トリガー＋出た時にバトルさせる誘発（既存）に、バラバラエティ3の常在型
  （コストが異なる自分のエレメントが3つ以上あればパワー+5000し「W・ブレイカー」を与える）を
  新式 distinct_cost_count の if で足した形。
"""
import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    """
id: dm24rp4-043
name: 魔誕哀樹シンバーロ
types: [creature]
civs: [nature]
cost: 8
power: 5000
races: [デーモン・コマンド, デモンズ・レガシー]
mana: 1
keywords: [s_trigger]
text: "S・トリガー（このクリーチャーをシールドゾーンから手札に加える時、コストを支払わずにすぐ召喚してもよい）\\nこのクリーチャーが出た時、相手のクリーチャーを１体選んでもよい。その選んだクリーチャーとこのクリーチャーをバトルさせる。\\nバラバラエティ３：このクリーチャーのパワーを+5000し、「W・ブレイカー」を与える。（コストが異なる自分のエレメントが３つ以上あれば、このクリーチャーはパワーを+5000され、シールドを２つブレイクする）"
abilities:
  - kind: trigger
    when: {event: move, to: bz, subject: self}
    effect:
      - op: may
        body:
          - {op: force_battle, a: {ref: self}, b: {zone: bz, owner: opp, filter: {types: [creature]}, count: 1}}
  - kind: static
    affects: self
    if: {cmp: [{distinct_cost_count: {zone: [bz, mana], owner: you}}, ">=", 3]}
    mod: {power: 5000, breaks: 2}
source: {official: dm24rp4-043, review: pending}
""",
]


def test_pilot145_cards_parse():
    for text in CARDS:
        parse_card(yaml.safe_load(text), TABLES)
