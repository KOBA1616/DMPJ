"""語彙パイロット第147弾: 代表カードの手変換が parse_card を通ること。

- 無龍 <デッゾ.Star>（型2）: スター進化＋侵略（既存の partial）に、出た時の
  「コストが異なるクリーチャーを好きな数、自分の墓地から手札に戻す」を
  distinct_costs: true の select で足した形。
- 魔誕の邪将クエイクス（型1）: バラバラエティ5（第145弾で変換済みの partial）に、攻撃時の
  「自分のどのクリーチャーともコストが異なる」を distinct_from の select で足した形。
- ラトリエ・ロブション（型3）: 山札の上3枚の条項（既存の partial）に、自分のターンの終わりの
  「墓地にコストが違うクリーチャーが8体以上あれば、それらをすべて出す」を
  distinct_costs + count の {distinct_cost_count} 式で足した形。出す対象はコストが互いに
  異なるように選ぶ部分集合で、登場は1体ずつ順番（公式QA 31610／31611、ユーザー決定 2026-11-08）。
"""
import yaml

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    """
id: dmrp19-s03
name: 無龍 <デッゾ.Star>
types: [creature, evolution]
civs: [darkness]
cost: 5
power: 8000
races: [マスター・ドラゴンZ, ソニック・コマンド, レクスターズ]
mana: 1
star: true
evolve_from: {any_of: [{race_has: レクスターズ}, {civs: [darkness]}]}
keywords: [g_strike, double_breaker]
text: "G・ストライク\\nスター進化：レクスターズまたは闇のクリーチャー１体の上に置く。\\n侵略：闇のコスト４以上のレクスターズ（自分の闇のコスト４以上のレクスターズが攻撃する時、自分の手札にあるこのクリーチャーをその上に重ねてもよい）\\nW・ブレイカー\\nこのクリーチャーが出た時、コストが異なるクリーチャーを好きな数、自分の墓地から手札に戻す。"
abilities:
  - kind: declare
    zone: hand
    when: {event: attack, subject: {owner: you, filter: {civs: [darkness], cost_ge: 4, race_has: レクスターズ}}}
    effect:
      - {op: may, body: [{op: invade, onto: {ref: event.subject}}]}
  - kind: trigger
    when: {event: move, to: bz, subject: self}
    effect:
      - {op: move, select: {zone: graveyard, owner: you, filter: {types: [creature]}, count: any, distinct_costs: true}, to: hand, reason: return}
source: {official: dmrp19-s03, review: pending}
""",
    """
id: dm24ex3-rp4005
name: 魔誕の邪将クエイクス
types: [creature]
civs: [fire]
cost: 7
power: 7000
races: [デーモン・コマンド]
mana: 1
keywords: [speed_attacker, double_breaker]
text: "スピードアタッカー\\nW・ブレイカー\\nこのクリーチャーが攻撃する時、自分の山札の上から３枚を表向きにする。その中から、コスト６以下で、自分のどのクリーチャーともコストが異なるクリーチャーを好きな数出してもよい。残りをすべて墓地に置く。\\nバラバラエティ５：クリーチャーがプレイヤーを攻撃する時、自分のクリーチャーをすべてアンタップする。（コストが異なる自分のエレメントが５つ以上あれば、このクリーチャーにこの能力を与える）"
abilities:
  - kind: trigger
    when: {event: attack, subject: self}
    effect:
      - {op: choose, select: {zone: deck, owner: you, from_top: 3, look: true, count: all}, as: pile}
      - {op: move, select: {ref: pile, filter: {types: [creature], cost_le: 6}, count: any, distinct_from: {zone: bz, owner: you, filter: {types: [creature]}}}, to: bz, reason: put}
      - {op: move, select: {ref: pile, count: all}, to: graveyard, reason: put}
  - kind: trigger
    when: {event: attack, target: player}
    if: {cmp: [{distinct_cost_count: {zone: [bz, mana], owner: you}}, ">=", 5]}
    effect:
      - {op: untap, select: {zone: bz, owner: you, filter: {types: [creature]}, count: all}}
source: {official: dm24ex3-rp4005, review: pending}
""",
    """
id: dmrp03-007
name: ラトリエ・ロブション
types: [creature]
civs: [darkness]
cost: 8
power: 8000
races: [マフィ・ギャング]
mana: 1
keywords: [double_breaker]
text: "W・ブレイカー\\n自分のターンの終わりに、自分の山札の上から３枚を見てもよい。そうしたら、そのうちの１枚を手札に加え、残りを墓地に置く。自分のターンの終わりに、自分の墓地にコストが違うクリーチャーが８体以上あれば、それらをすべてバトルゾーンに出してもよい。"
abilities:
  - kind: trigger
    when: {event: turn_end, player: you}
    effect:
      - op: may
        body:
          - {op: choose, select: {zone: deck, owner: you, from_top: 3, look: true, count: all}, as: a}
          - {op: move, select: {ref: a, count: 1}, to: hand, reason: draw}
          - {op: move, select: {ref: a, count: all}, to: graveyard, reason: put}
  - kind: trigger
    when: {event: turn_end, player: you}
    if: {cmp: [{distinct_cost_count: {zone: graveyard, owner: you, filter: {types: [creature]}}}, ">=", 8]}
    effect:
      - op: may
        body:
          - {op: move, select: {zone: graveyard, owner: you, filter: {types: [creature]}, count: {distinct_cost_count: {zone: graveyard, owner: you, filter: {types: [creature]}}}, distinct_costs: true}, to: bz, reason: put}
source: {official: dmrp03-007, review: pending}
""",
]


def test_pilot147_cards_parse():
    for text in CARDS:
        parse_card(yaml.safe_load(text), TABLES)
