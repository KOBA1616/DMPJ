"""語彙パイロット第40弾（フェーズ17-1）: 代表カードの手変換が parse_card を通ること。

- ゲロ NICE・ハンゾウ: 「相手の呪文の効果または相手のクリーチャーの能力によって捨てられる時、かわりに置く」を when.by: opp で表す
- アクア闘士 サンダーボルト: 「かわりに出し、カードを2枚引いてもよい」（instead 内の任意ドロー）と手札5枚以上の常在修整
（どちらも再変換ラウンド15で登録した形）
"""
import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    """
id: dmx04-006
name: ゲロ NICE・ハンゾウ
types: [creature]
civs: [darkness]
cost: 7
power: 5000
races: [デーモン・コマンド, ハンター]
mana: 1
text: "このクリーチャーをバトルゾーンに出した時、バトルゾーンにある相手のクリーチャーを１体選ぶ。そのターン、そのクリーチャーのパワーは-6000される。(パワー０以下のクリーチャーは破壊される) / 相手の呪文の効果または相手のクリーチャーの能力によって、このクリーチャーが自分の手札から捨てられる時、墓地に置くかわりにバトルゾーンに置いてもよい。"
abilities:
  - kind: trigger
    when: {event: move, to: bz, subject: self}
    effect:
      - {op: modify, select: {zone: bz, owner: opp, filter: {types: [creature]}, count: 1}, mod: {power: -6000}, duration: end_of_turn}
  - kind: replace
    zone: hand
    optional: true
    when: {event: move, from: hand, to: graveyard, reason: discard, subject: self, by: opp}
    instead:
      - {op: move, select: {ref: self, count: 1}, to: bz, reason: put}
source: {official: dmx04-006, review: pending}
""",
    """
id: dmex09-029
name: アクア闘士 サンダーボルト
types: [creature]
civs: [water]
cost: 3
power: 2000
races: [リキッド・ピープル閃]
mana: 1
text: "相手の呪文の効果またはクリーチャーの能力によって、このクリーチャーが自分の手札から捨てられる時、墓地に置くかわりにバトルゾーンに出し、カードを２枚引いてもよい。 / 自分の手札が５枚以上あれば、このクリーチャーのパワーを+4000し、「W・ブレイカー」を与える。"
abilities:
  - kind: replace
    zone: hand
    optional: true
    when: {event: move, from: hand, to: graveyard, reason: discard, subject: self, by: opp}
    instead:
      - {op: move, select: {ref: self, count: 1}, to: bz, reason: put}
      - {op: may, body: [{op: draw, count: 2}]}
  - kind: static
    affects: self
    if: {cmp: [{count: {zone: hand, owner: you}}, ">=", 5]}
    mod: {power: 4000, grant: [double_breaker]}
source: {official: dmex09-029, review: pending}
""",
]


def test_pilot40_cards_parse():
    for text in CARDS:
        parse_card(yaml.safe_load(text), TABLES)
