"""語彙パイロット第34弾: 代表カードの手変換が parse_card を通ること。

- 暴投の針棺: 離脱置換（とどまる型。instead: []＋パワーの if）
- 単騎連射 マグナム: 出現置換（相手の登場を墓地送りに置換。is_turn: you の条件つき）
- 威牙忍ジンナイ: 離脱置換（身代わり型。optional＋instead で自分のクリーチャーを破壊）
"""
import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    """
id: dmrp16-031
name: 暴投の針棺
types: [creature]
civs: [light]
cost: 4
power: 1000
races: [グレートメカオー, 暴拳王国]
mana: 1
text: このクリーチャーがバトルゾーンを離れる時、そのパワーが０より大きければ、離れるかわりにとどまる。
abilities:
  - kind: replace
    when: {event: move, from: bz, subject: self}
    if: {exists: {ref: self, filter: {power_ge: 1}}}
    instead: []
source: {official: dmrp16-031, review: pending}
""",
    """
id: dm26sd1-i011
name: 単騎連射 マグナム
types: [creature]
civs: [fire]
cost: 3
power: 3000
races: [アウトレイジ]
mana: 1
text: 自分のターンに相手のクリーチャーが出る時、かわりにそのクリーチャーを墓地に置く。
abilities:
  - kind: replace
    when: {event: move, to: bz, subject: {owner: opp, filter: {types: [creature]}}}
    if: {is_turn: you}
    instead:
      - {op: move, select: {ref: subject, count: 1}, to: graveyard, reason: put}
source: {official: dm26sd1-i011, review: pending}
""",
    """
id: dm29-028
name: 威牙忍ジンナイ
types: [creature]
civs: [darkness]
cost: 4
power: 3000
races: [ダークロード, シノビ]
mana: 1
keywords: [blocker]
text: このクリーチャーは攻撃することができない。自分の他のシノビがバトルゾーンを離れる時、かわりに自分のクリーチャーを１体破壊してもよい。
abilities:
  - kind: static
    affects: self
    mod: {deny: [attack_player, attack_creature]}
  - kind: replace
    optional: true
    when: {event: move, from: bz, subject: {owner: you, filter: {race_has: シノビ}, other: true}}
    instead:
      - {op: destroy, select: {zone: bz, owner: you, count: 1}}
source: {official: dm29-028, review: pending}
""",
]


def test_pilot34_cards_parse():
    for text in CARDS:
        parse_card(yaml.safe_load(text), TABLES)
