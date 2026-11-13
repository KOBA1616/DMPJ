"""語彙パイロット第43弾: 代表カードの手変換が parse_card を通ること。

- ブランド-MAX: S-MAX進化（s_max: true＋敗北の置換 when: {event: lose}）を表す（再変換ラウンド18で登録した形）
"""
import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    r'''
id: dm24rp2-sp3
name: ブランド-MAX
types:
- creature
- evolution
civs:
- fire
cost: 4
power: 5000
races:
- ビートジョッキー
- レクスターズ
mana: 1
s_max: true
text: S-MAX進化：自分がゲームに負ける時、かわりにこのクリーチャーを破壊するか、自分の手札から《ブランド-MAX》を１枚捨てる。（このクリーチャーは進化元を必要としない。自分のS-MAX進化クリーチャーが２体以上あれば、そのうちの１体を残し、残りをすべて手札に戻す）
  / このクリーチャーが攻撃する時、自分の他のクリーチャーを１体アンタップする。このターン、そのクリーチャーはシールドをさらに１つブレイクする。 / 相手がこのクリーチャーを選んだ時、相手のシールドを１つ、持ち主の墓地に置く。
abilities:
- kind: replace
  optional: true
  when:
    event: lose
  instead:
  - op: if
    cond:
      exists:
        zone: hand
        owner: you
        filter:
          name: ブランド-MAX
    then:
    - op: modal
      modes:
      - - op: move
          select:
            ref: self
            count: 1
          to: graveyard
          reason: destroy
      - - op: discard
          select:
            zone: hand
            owner: you
            chooser: you
            filter:
              name: ブランド-MAX
            count: 1
    else:
    - op: move
      select:
        ref: self
        count: 1
      to: graveyard
      reason: destroy
- kind: trigger
  when:
    event: attack
    subject: self
  effect:
  - op: choose
    select:
      zone: bz
      owner: you
      chooser: you
      filter:
        types:
        - creature
      other: true
      count: 1
    as: tgt
  - op: untap
    select:
      ref: tgt
      count: 1
  - op: modify
    select:
      ref: tgt
      count: 1
    mod:
      breaks: 1
    duration: end_of_turn
- kind: trigger
  when:
    event: choose
    subject: self
  effect:
  - op: move
    select:
      zone: shield
      owner: opp
      chooser: you
      count: 1
    to: graveyard
    reason: put
source:
  official: dm24rp2-sp3
  review: pending
  notes: 'S-MAX進化は s_max: true＋第43弾の標準形。攻撃時のアンタップ＋追加ブレイクは mod breaks、選ばれた時は event:
    choose（アポロヌス先例どおり）。再変換ラウンド18。'
''',
]


def test_pilot43_cards_parse():
    for text in CARDS:
        cd = parse_card(yaml.safe_load(text), TABLES)
        assert cd.s_max is True
