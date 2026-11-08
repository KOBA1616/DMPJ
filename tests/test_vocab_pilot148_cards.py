"""語彙パイロット第148弾: 代表カードの手変換が parse_card を通ること。

- 天門ノ裁キ（裁キ型）: 唱えた後の墓地送りを kind: replace（zone: hold、reason: resolve）で
  置換し、instead は stack_on つき move で自分のシールドの上に表向きに重ねる（第2.1節の型）。
- 煌龍 サッヴァーク: 出た時に相手のカードを表向きで持ち主のシールドの上に置く
  （stack_on の owner: opp。選択者は使用者）。離脱置換は partial の既存分。
- カイザー・ルピア: 出た時に自分のシールドゾーンのカードを1枚表向きにする
  （may＋flip_up）。コスト軽減の常在型は partial の既存分。
- シンクロ・ルピア / 「D4に敗北は許されない！」: 呪文面は choose でシールドを見て、
  may＋modal でその束の中のカードを表向き／裏向きにする（bundle_of の変数形）。
"""
import yaml

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    """
id: dmex19-024
name: 天門ノ裁キ
types: [spell]
civs: [light]
cost: 6
races: [裁きの紋章]
mana: 1
text: "カードを１枚引く。その後、「ブロッカー」を持つクリーチャーを１体、自分の手札から出してもよい。\\nこの呪文を自分の手札から唱えた後、墓地に置くかわりに自分のシールド１つの上に表向きにして置く。（そのシールドの束は１つと数える）"
spell:
  - {op: draw, player: you, count: 1}
  - op: may
    body:
      - {op: move, select: {zone: hand, owner: you, filter: {types: [creature], keyword: blocker}, count: 1}, to: bz, reason: put}
abilities:
  - kind: replace
    zone: hold
    when: {event: move, subject: self, to: graveyard, reason: resolve}
    instead:
      - {op: move, select: {ref: self}, to: shield, reason: put, face_up: true, stack_on: {zone: shield, owner: you, count: 1}}
source: {official: dmex19-024, review: pending}
""",
    """
id: dm26ex3-dcr003
name: 煌龍 サッヴァーク
types: [creature]
civs: [light]
cost: 7
power: 11000
races: [マスター・ドラゴン, メタリカ]
mana: 1
keywords: [double_breaker]
text: "ドラゴン・W・ブレイカー\\nこのクリーチャーが出た時、バトルゾーンにある相手のカードを１枚選び、表向きで持ち主のシールド１つの上に置く。\\n自分のクリーチャーが離れる時、かわりにいずれかのシールドゾーンにある表向きのカードを１枚選び、持ち主の墓地に置いてもよい。"
abilities:
  - kind: trigger
    when: {event: move, to: bz, subject: self}
    effect:
      - {op: move, select: {zone: bz, owner: opp, count: 1}, to: shield, reason: put, face_up: true, stack_on: {zone: shield, owner: opp, count: 1}}
  - kind: replace
    optional: true
    when: {event: move, from: bz, subject: {owner: you, filter: {types: [creature]}}}
    instead:
      - {op: move, select: {zone: shield, owner: any, filter: {face_up: true}, count: 1}, to: graveyard, reason: put}
source: {official: dm26ex3-dcr003, review: pending}
""",
    """
id: dm26ex2-052
name: カイザー・ルピア
types: [creature]
civs: [light]
cost: 2
power: 1000
races: [アーマード・ファイアー・バード]
mana: 1
text: "このクリーチャーが出た時、自分のシールドゾーンにあるカードを１枚表向きにしてもよい。\\n自分のアーマード・ドラゴン・カードを実行するコストを１少なくする。自分のシールドゾーンに表向きのカードがあれば、追加で１少なくする。ただしコストは０以下にならない。"
abilities:
  - kind: trigger
    when: {event: move, to: bz, subject: self}
    effect:
      - op: may
        body:
          - {op: flip_up, select: {zone: shield, owner: you, count: 1}}
  - kind: static
    affects: {zone: hand, owner: you, filter: {race_has: アーマード・ドラゴン}}
    mod: {cost_may: {amount: 1, min: 0}}
  - kind: static
    affects: {zone: hand, owner: you, filter: {race_has: アーマード・ドラゴン}}
    if: {exists: {zone: shield, owner: you, filter: {face_up: true}}}
    mod: {cost_may: {amount: 1, min: 0}}
source: {official: dm26ex2-052, review: pending}
""",
    """
id: dm26ex2-038
name: シンクロ・ルピア / 「D4に敗北は許されない！」
faces:
  - name: シンクロ・ルピア
    types: [creature]
    civs: [water]
    cost: 5
    power: 4000
    races: [アーマード・ドラゴン, ファイアー・バード, スノーフェアリー]
    keywords: [s_trigger]
    text: "S・トリガー\\nこのクリーチャーが出た時、相手のクリーチャーを１体選び、持ち主の手札に戻してもよい。"
    abilities:
      - kind: trigger
        when: {event: move, to: bz, subject: self}
        effect:
          - op: may
            body:
              - {op: bounce, select: {zone: bz, owner: opp, filter: {types: [creature]}, count: 1}}
  - name: 「D4に敗北は許されない！」
    types: [spell]
    civs: [water]
    cost: 3
    races: [アーマード・ドラゴン・ワード]
    text: "シールドを１つ見る。そのシールドに含まれるカードを１枚、表向きまたは裏向きにしてもよい。\\nカードを２枚引く。"
    spell:
      - {op: choose, select: {zone: shield, owner: you, count: 1, look: true}, as: sh}
      - op: may
        body:
          - op: modal
            modes:
              - [{op: flip_up, select: {bundle_of: sh, count: 1}}]
              - [{op: flip_down, select: {bundle_of: sh, count: 1}}]
      - {op: draw, player: you, count: 2}
mana: 1
text: "シンクロ・ルピア: S・トリガー\\nこのクリーチャーが出た時、相手のクリーチャーを１体選び、持ち主の手札に戻してもよい。／「D4に敗北は許されない！」: シールドを１つ見る。そのシールドに含まれるカードを１枚、表向きまたは裏向きにしてもよい。\\nカードを２枚引く。"
source: {official: dm26ex2-038, review: pending}
""",
]


def test_representative_cards_parse():
    for text in CARDS:
        card = parse_card(yaml.safe_load(text), TABLES)
        assert card is not None


def test_new_vocabulary_forms():
    tenmon = parse_card(yaml.safe_load(CARDS[0]), TABLES)
    ins = tenmon.abilities[0]["instead"][0]
    assert ins["op"] == "move" and ins["stack_on"]["count"] == 1 and ins["face_up"] is True
    savvaark = parse_card(yaml.safe_load(CARDS[1]), TABLES)
    cip = next(ab for ab in savvaark.abilities if ab["kind"] == "trigger")["effect"][0]
    assert cip["stack_on"] == {"zone": "shield", "owner": "opp", "count": 1}
    kaiser = parse_card(yaml.safe_load(CARDS[2]), TABLES)
    trig = next(ab for ab in kaiser.abilities if ab["kind"] == "trigger")
    assert trig["effect"][0]["body"][0]["op"] == "flip_up"
    synchro = parse_card(yaml.safe_load(CARDS[3]), TABLES)
    modal = synchro.faces[1].spell[1]["body"][0]
    assert modal["op"] == "modal"
    assert [m[0]["op"] for m in modal["modes"]] == ["flip_up", "flip_down"]
    assert modal["modes"][0][0]["select"]["bundle_of"] == "sh"
