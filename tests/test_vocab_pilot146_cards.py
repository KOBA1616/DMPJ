"""語彙パイロット第146弾: 代表カードの手変換が parse_card を通ること。

- ボルメテウス・ホワイト・ドラゴン GS: B型（ブレイク側・必須の行き先変更）。
  replace＋when: {event: break, subject: self}、instead でそのシールドを墓地に置く。
- ガイアール・ベイビー: A型（割り込み・自己置換でブレイク継続）。
  continue: true を付け、instead は may＋手札からコスト参照つきで出す。
  コスト参照は {cost_of: {ref: shield}}（束なら最大コスト＝存在読み。FAQ qa_old/36515）。
"""
import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    """
id: dmsp02-002
name: ボルメテウス・ホワイト・ドラゴン GS
types: [creature]
civs: [fire]
cost: 7
power: 7000
races: [アーマード・ドラゴン]
keywords: [g_strike, double_breaker]
text: "G・ストライク（このクリーチャーを自分のシールドゾーンから手札に加える時、相手に見せ、相手のクリーチャーを１体選んでもよい。このターン、そのクリーチャーは攻撃できない）\\nW・ブレイカー\\nこのクリーチャーがシールドをブレイクする時、相手はかわりにそのシールドを墓地に置く。"
abilities:
  - kind: replace
    when: {event: break, subject: self}
    instead:
      - {op: move, select: {ref: event.shield, count: 1}, to: graveyard, reason: put}
source: {official: dmsp02-002, review: pending}
""",
    """
id: dmr04-005
name: ガイアール・ベイビー
types: [creature]
civs: [water, fire, nature]
cost: 5
power: 5000
races: [レッド・コマンド・ドラゴン, ハンター]
keywords: [speed_attacker]
text: "マナゾーンに置く時、このカードはタップして置く。\\nスピードアタッカー\\nこのクリーチャーが相手のシールドをブレイクする時、相手はかわりにそのシールドをすべてのプレイヤーに見せる。そのシールドの中のカード１枚よりコストが小さい、進化ではないクリーチャーを１体、自分の手札からバトルゾーンに出してもよい。その後、このクリーチャーはそのシールドをブレイクする。"
abilities:
  - kind: replace
    when: {event: break, subject: self}
    continue: true
    instead:
      - op: may
        body:
          - {op: move, select: {zone: hand, owner: you, filter: {types: [creature], cost_le: {sum: [{cost_of: {ref: shield}}, -1]}, evolution: false}, count: 1, up_to: true}, to: bz, reason: put}
source: {official: dmr04-005, review: pending}
""",
]


def test_pilot146_cards_parse():
    for text in CARDS:
        card = parse_card(yaml.safe_load(text), TABLES)
        ab = card.abilities[-1]
        assert ab["kind"] == "replace" and ab["when"]["event"] == "break"
    gaia = parse_card(yaml.safe_load(CARDS[1]), TABLES)
    assert gaia.abilities[-1]["continue"] is True
