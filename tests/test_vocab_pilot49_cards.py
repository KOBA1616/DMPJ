"""語彙パイロット第49弾: 実カードの parse 確認（no_leave を使う2枚）。"""
import yaml

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    r'''
id: dm22rp1-010
name: ブルトゥーラ-D１
types: [creature]
civs: [light]
cost: 3
power: 3500
races: [メカ・デル・ディネロ]
mana: 1
text: 自分の他のクリーチャーは、破壊以外の方法で離れない。
abilities:
- kind: static
  affects: {owner: you, zone: bz, other: true, filter: {types: [creature]}}
  mod: {no_leave: {except_destroy: true}}
source: {official: dm22rp1-010, review: pending}
''',
    r'''
id: dm25ex1-031
name: 龍装者 ジスタジオ
types: [creature]
civs: [nature]
cost: 8
power: 15000
races: [ドラゴンギルド, グランセクト]
mana: 1
keywords: [guardman, triple_breaker]
text: ガードマン / T・ブレイカー / 自分のパワー12000以上のクリーチャーは、バトルに負けた時以外、離れない。
abilities:
- kind: static
  affects: {owner: you, zone: bz, filter: {types: [creature], power_ge: 12000}}
  mod: {no_leave: {except_battle: true}}
source: {official: dm25ex1-031, review: pending}
''',
]


def test_pilot49_cards_parse():
    for src in CARDS:
        card = yaml.safe_load(src)
        parse_card(card, TABLES, where=card["id"])
