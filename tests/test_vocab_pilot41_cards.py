"""語彙パイロット第41弾: 代表カードの手変換が parse_card を通ること。

- アクア提督 ザ・ミスター: 「カードに能力が書かれていないクリーチャー」を filter の vanilla: true で表す
（再変換ラウンド16で登録した形）
"""
import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    """
id: dmr16g-023
name: アクア提督 ザ・ミスター
types: [creature]
civs: [water]
cost: 5
power: 5000
races: [リキッド・ピープル閃]
mana: 1
text: "相手の呪文の効果または相手のクリーチャーの能力によって、このクリーチャーが自分の手札から捨てられる時、墓地に置くかわりに自分のバトルゾーンに置いてもよい。このクリーチャーをバトルゾーンに出した時、自分の山札の上から３枚をすべてのプレイヤーに見せる。その中から、カードに能力が書かれていないクリーチャーをすべて自分の手札に加え、残りを好きな順序で自分の山札の一番下に置く。"
abilities:
  - kind: trigger
    when: {event: move, to: bz, subject: self}
    effect:
      - {op: choose, select: {zone: deck, owner: you, from_top: 3, look: true, count: all}, as: pile}
      - {op: move, select: {ref: pile, filter: {types: [creature], vanilla: true}, count: all}, to: hand, reason: return}
      - {op: move, select: {ref: pile, count: all}, to: deck, position: bottom, order: choose, reason: put}
  - kind: replace
    zone: hand
    optional: true
    when: {event: move, from: hand, to: graveyard, reason: discard, subject: self, by: opp}
    instead:
      - {op: move, select: {ref: self, count: 1}, to: bz, reason: put}
source: {official: dmr16g-023, review: pending}
""",
]


def test_pilot41_cards_parse():
    for text in CARDS:
        parse_card(yaml.safe_load(text), TABLES)
