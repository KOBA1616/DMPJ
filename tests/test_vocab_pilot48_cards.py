"""語彙パイロット第48弾: 実カードの parse 確認（cost_may must へ直した3枚）。"""
import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    r'''
id: dm24bd5-060
name: 珊瑚妖精キユリ
types:
- creature
civs:
- water
- nature
cost: 2
power: 2000
races:
- スノーフェアリー
- チームウェイブ
mana: 1
text: 各ターン、自分のクリーチャー１体目の召喚コストを１少なくする。ただし、コストは０以下にはならない。相手はこのクリーチャーを選べない。
abilities:
- kind: static
  affects:
    owner: you
    zone: hand
    filter:
      types:
      - creature
  mod:
    cost_may:
      amount: 1
      once: true
      min: 1
      must: true
- kind: static
  mod:
    deny:
    - be_chosen
source:
  official: dm24bd5-060
  review: pending
  notes: 1体目の軽減は cost_may（once・must）で、「選ばれない」は deny be_chosen で表した
  aliases:
  - dm24ex3-tf46
  - dm24rp1-t12
  - dmex16-100
  - dmrp13-089
  - promoy19-070

''',
    r'''
id: dm24ex3-tf22
name: ザパンプ
types:
- creature
civs:
- water
cost: 2
power: 2000
races:
- ジョーカーズ
mana: 1
text: 各ターン、自分が唱える１枚目の呪文のコストを１少なくする。ただし、コストは０以下にはならない。
abilities:
- kind: static
  affects:
    owner: you
    zone: hand
    filter:
      types:
      - spell
  mod:
    cost_may:
      amount: 1
      once: true
      min: 1
      must: true
source:
  official: dm24ex3-tf22
  review: pending
  notes: '「各ターン1枚目」は opt_reduce で表した。「０以下にはならない」は cost_min: 1 と解釈した'
  aliases:
  - dm24rp2-t07
  - dmbd11-a06

''',
    r'''
id: dm26ex4-055
name: 珊瑚妖精キユリ / キユリのFSMラジオ
cost: 2
mana: 1
text: 'キユリ: 各ターン、自分のクリーチャー１体目の召喚コストを１少なくする。相手はこのクリーチャーを選べない。 ／ FSMラジオ: 自分の山札の上から３枚を見る。その中から、コスト３以下のクリーチャーを１体出す。残りを好きな順序で山札の下に置く。'
faces:
- name: 珊瑚妖精キユリ
  types:
  - creature
  civs:
  - water
  - nature
  cost: 2
  power: 2000
  races:
  - スノーフェアリー
  - チームウェイブ
  abilities:
  - kind: static
    affects:
      owner: you
      zone: hand
      filter:
        types:
        - creature
    mod:
      cost_may:
        amount: 1
        once: true
        must: true
  - kind: static
    affects: self
    mod:
      deny:
      - be_chosen
- name: キユリのFSMラジオ
  types:
  - spell
  civs:
  - nature
  cost: 3
  spell:
  - op: choose
    select:
      zone: deck
      owner: you
      from_top: 3
      look: true
      count: all
    as: a
  - op: play_free
    select:
      ref: a
      filter:
        types:
        - creature
        cost_le: 3
      count: 1
  - op: move
    select:
      ref: a
      count: all
    to: deck
    reason: put
source:
  official: dm26ex4-055
  review: pending
''',
]


def test_pilot48_cards_parse():
    for src in CARDS:
        card = yaml.safe_load(src)
        parse_card(card, TABLES, where=card["id"])
