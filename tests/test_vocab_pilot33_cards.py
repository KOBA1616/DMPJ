"""語彙パイロット第33弾: 代表カードの手変換が parse_card を通ること。

- ラギルップ＝ラギバーン: G-NEO進化（neo: true ＋ キーワード g_neo）
- 応援者 オシヤバミ: 「召喚によって出た時」（when の reason: summon）
- 九極 デュエンジェル: 「光以外の呪文を唱えられない」（affects ＋ deny: [cast]、シールド数の条件つき）
"""
import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    """
id: promoy24-005
name: ラギルップ＝ラギバーン
types: [creature]
civs: [darkness]
cost: 4
power: 6000
races: [アビスロイヤル]
mana: 1
neo: true
evolve_from: {civs: [water, darkness, fire]}
keywords: [g_neo, slayer, double_breaker]
text: G-NEO進化：水、闇、または火のクリーチャー１体の上に置いてもよい。（カードが下にあれば、NEO進化クリーチャーとして扱い、離れる時、かわりに下のカードすべてが離れる）
source: {official: promoy24-005, review: pending}
""",
    """
id: dmrp15-054
name: 応援者 オシヤバミ
types: [creature]
civs: [water, fire]
cost: 3
power: 4000
races: [ムートピア, 美孔麗王国]
mana: 1
text: 水または火のクリーチャーを召喚によって自分の手札からバトルゾーンに出した時、自分の手札を１枚捨て、その後、カードを１枚引く。
abilities:
  - kind: trigger
    when: {event: move, from: hand, to: bz, reason: summon, subject: {owner: you, filter: {types: [creature], civs: [water, fire]}}}
    effect:
      - {op: discard, select: {zone: hand, owner: you, count: 1}}
      - {op: draw, count: 1}
source: {official: dmrp15-054, review: pending}
""",
    """
id: dmr17-s02
name: 九極 デュエンジェル
types: [creature]
civs: [light]
cost: 9
power: 13500
races: [エンジェル・コマンド, 侵略者]
mana: 1
keywords: [blocker, triple_breaker]
text: 相手のシールドが２つ以下なら、誰も光以外の呪文を唱えられない。
abilities:
  - kind: static
    if: {cmp: [{count: {zone: shield, owner: opp}}, "<=", 2]}
    affects: {owner: any, zone: hand, filter: {types: [spell], not_civs: [light]}}
    mod: {deny: [cast]}
source: {official: dmr17-s02, review: pending}
""",
]


def test_pilot33_cards_parse():
    for text in CARDS:
        parse_card(yaml.safe_load(text), TABLES)
