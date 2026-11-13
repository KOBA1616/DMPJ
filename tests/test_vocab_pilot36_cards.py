"""語彙パイロット第36弾: 代表カードの手変換が parse_card を通ること。

- タブ＝タラウプ: 素の墓地召喚（キーワード summon_from_graveyard）
- 鬼面妖蟲ワーム・ゴワルスキー: 墓地進化（進化クリーチャー型。evolve_zone: graveyard で既存の進化機構を使う）
"""
import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    """
id: dm24rp1-064
name: タブ＝タラウプ
types: [creature]
civs: [darkness]
cost: 2
power: 2000
races: [アビスロイヤル]
mana: 1
keywords: [summon_from_graveyard]
text: このクリーチャーを自分の墓地から召喚してもよい。（コストは支払う）
source: {official: dm24rp1-064, review: pending}
""",
    """
id: dm22rp2x-tf18
name: 鬼面妖蟲ワーム・ゴワルスキー
types: [creature, evolution]
civs: [darkness]
cost: 2
power: 4000
races: [パラサイトワーム, デビルマスク]
mana: 1
evolve_zone: graveyard
evolve_from: {civs: [darkness]}
text: 墓地進化：闇のクリーチャーを１体自分の墓地から選び、このクリーチャーをその上に重ねつつ出す。このクリーチャーが破壊された時、相手の手札を１枚見ないで選び、捨てさせる。
abilities:
  - kind: trigger
    when: {event: move, from: bz, subject: self, reason: destroy}
    effect:
      - {op: discard, select: {zone: hand, owner: opp, count: 1}}
source: {official: dm22rp2x-tf18, review: pending}
""",
]


def test_pilot36_cards_parse():
    for text in CARDS:
        parse_card(yaml.safe_load(text), TABLES)
