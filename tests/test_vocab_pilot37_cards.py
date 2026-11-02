"""語彙パイロット第37弾: 代表カードの手変換が parse_card を通ること。

- 堕魔 ヴォーミラ: 「自分のターンに一度、魔導具クリーチャーを1体、墓地から召喚してもよい」
  = 回数制限つき許可 {action: summon_from_graveyard, once: true}
"""
import yaml

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    """
id: dmex08-206
name: 堕魔 ヴォーミラ
types: [creature]
civs: [darkness]
cost: 4
power: 4000
races: [マフィ・ギャング, 魔導具]
mana: 1
text: このクリーチャーがバトルゾーンに出た時、自分の山札の上から３枚を墓地に置いてもよい。自分のターンに一度、魔導具クリーチャーを１体、自分の墓地から召喚してもよい。
abilities:
  - kind: trigger
    when: {event: move, to: bz, subject: self}
    effect:
      - {op: may, body: [{op: mill, owner: you, count: 3}]}
  - kind: static
    affects: {owner: you, zone: graveyard, filter: {races: [魔導具]}}
    if: {is_turn: you}
    mod: {allow: [{action: summon_from_graveyard, once: true}]}
source: {official: dmex08-206, review: pending}
""",
]


def test_pilot37_cards_parse():
    for text in CARDS:
        parse_card(yaml.safe_load(text), TABLES)
