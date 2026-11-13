"""語彙パイロット第45弾: 代表カードの手変換が parse_card を通ること。

- 魔凰 デ・スザーク: 無月の門（手札/墓地で機能する誘発＋ summon_on）を表す（再変換ラウンド20で登録した形）
"""
import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    r'''
id: dmbd08-b-006
name: 魔凰 デ・スザーク
types:
- creature
civs:
- darkness
cost: 8
power: 6000
races:
- マスター・ドルスザク
- マフィ・ギャング
mana: 1
text: '無月の門：自分の魔導具をバトルゾーンに出した時、自分の魔導具をバトルゾーンと墓地から２つずつ選び、このクリーチャーを自分の手札または墓地からそれら４枚の上にコストを支払わずに召喚してもよい。

  W・ブレイカー（このクリーチャーはシールドを２つブレイクする）

  このクリーチャーがバトルゾーンに出た時、そのターン、バトルゾーンにある相手のクリーチャーすべてのパワーを－3000する。（パワー０以下のクリーチャーは破壊される）'
keywords:
- double_breaker
abilities:
- kind: trigger
  zone: hand
  when: &id001
    event: move
    to: bz
    subject:
      owner: you
      other: true
      filter:
        races:
        - 魔導具
  if: &id002
    all:
    - cmp:
      - count:
          zone: bz
          owner: you
          filter:
            races:
            - 魔導具
      - '>='
      - 2
    - cmp:
      - count:
          zone: graveyard
          owner: you
          filter:
            races:
            - 魔導具
      - '>='
      - 2
  effect: &id003
  - op: may
    body:
    - op: summon_on
      parts:
      - zone: bz
        count: 2
        filter:
          races:
          - 魔導具
      - zone: graveyard
        count: 2
        filter:
          races:
          - 魔導具
- kind: trigger
  zone: graveyard
  when: *id001
  if: *id002
  effect: *id003
- kind: trigger
  when:
    event: move
    to: bz
    subject: self
  effect:
  - op: modify
    select:
      zone: bz
      owner: opp
      filter:
        types:
        - creature
      count: all
    mod:
      power: -3000
    duration: end_of_turn
source:
  official: dmbd08-b-006
  review: pending
  notes: '無月の門は第45弾の標準形（zone: hand / graveyard の誘発＋summon_on、2つずつ）。出た時の相手全員パワー-3000は
    modify（count: all、duration: end_of_turn）。W・ブレイカーはキーワード。再変換ラウンド20。'
''',
]


def test_pilot45_cards_parse():
    for text in CARDS:
        cd = parse_card(yaml.safe_load(text), TABLES)
        kinds = [a.get("kind") for a in cd.abilities]
        assert "trigger" in kinds
