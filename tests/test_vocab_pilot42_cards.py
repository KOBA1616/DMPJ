"""語彙パイロット第42弾: 代表カードの手変換が parse_card を通ること。

- ボルシャック・ドギラゴン: 革命０トリガーを kind: declare で表す（再変換ラウンド17で登録した形）
"""
import yaml

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    r'''
id: dm24bd1-002
name: ボルシャック・ドギラゴン
types:
- creature
- evolution
civs:
- fire
cost: 7
power: 12000
races:
- メガ・コマンド・ドラゴン
- 革命軍
mana: 1
keywords:
- triple_breaker
evolve_from:
  types:
  - creature
  civs:
  - fire
text: 革命０トリガー：クリーチャーが自分を攻撃する時、自分のシールドが１つもなければ、このクリーチャーを手札から見せてもよい。そうしたら、自分の山札の上から１枚目を表向きにする。そのカードが火の進化ではないクリーチャーなら出し、このクリーチャーをその上に置く。
  / 進化：火のクリーチャー１体の上に置く。 / T・ブレイカー / このクリーチャーが出た時または攻撃する時、相手のクリーチャーを１体選んでもよい。その選んだクリーチャーとこのクリーチャーをバトルさせる。
abilities:
- kind: declare
  zone: hand
  when:
    event: attack
    target: player
  if:
    all:
    - is_turn: opp
    - cmp:
      - count:
          zone: shield
          owner: you
      - ==
      - 0
  effect:
  - op: choose
    select:
      zone: deck
      owner: you
      from_top: 1
      look: true
      count: all
    as: top
  - op: if
    cond:
      exists:
        ref: top
        filter:
          types:
          - creature
          not_types:
          - evolution
          civs:
          - fire
    then:
    - op: move
      select:
        ref: top
        count: 1
      to: bz
      reason: put
      as: base
    - op: invade
      onto:
        ref: base
- kind: trigger
  when:
    event: move
    to: bz
    subject: self
  effect:
  - op: may
    body:
    - op: force_battle
      a:
        ref: self
      b:
        zone: bz
        owner: opp
        filter:
          types:
          - creature
        count: 1
- kind: trigger
  when:
    event: attack
    subject: self
  effect:
  - op: may
    body:
    - op: force_battle
      a:
        ref: self
      b:
        zone: bz
        owner: opp
        filter:
          types:
          - creature
        count: 1
source:
  official: dm24bd1-002
  review: pending
  notes: 革命０トリガーは第42弾の declare 形式（proto T120 と同型）。出た時・攻撃する時のバトルは force_battle（dmrp14-021
    と同型）を2つの trigger に分けて書いた。再変換ラウンド17。
''',
]


def test_pilot42_cards_parse():
    for text in CARDS:
        parse_card(yaml.safe_load(text), TABLES)
