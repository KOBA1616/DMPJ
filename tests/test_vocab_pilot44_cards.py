"""語彙パイロット第44弾: 代表カードの手変換が parse_card を通ること。

- ナゾの光・リリアング: キーワード kizuna＋[P]（kind: partner で光の呪文の無料詠唱）を表す（再変換ラウンド19で登録した形）
"""
import yaml

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    r'''
id: dm22bd2-006
name: ナゾの光・リリアング
types:
- creature
civs:
- light
cost: 2
power: 2000
races:
- メタリカ
- スペシャルズ
mana: 1
text: 'キズナ（このクリーチャーが出た時、自分のクリーチャー１体の[P]能力を使う）

  [P]光のコスト３以下の呪文を１枚、コストを支払わずに自分の手札から唱えてもよい。

  エスケープ（このクリーチャーが破壊される時、墓地に置くかわりに自分のシールドを１つ手札に加えてもよい。ただし、その「S・トリガー」は使えない）'
keywords:
- escape
- kizuna
abilities:
- kind: partner
  effect:
  - op: may
    body:
    - op: play_free
      select:
        zone: hand
        owner: you
        filter:
          types:
          - spell
          civs:
          - light
          cost_le: 3
        count: 1
source:
  official: dm22bd2-006
  review: pending
  notes: 'キズナはキーワード kizuna（第44弾）で表した。[P]は kind: partner で、光のコスト3以下の呪文の無料詠唱は may +
    play_free（手札選択）。エスケープはキーワード。再変換ラウンド19。'
  aliases:
  - dmex03-s03
  - dmex08-203
  - dmex19-s7
''',
]


def test_pilot44_cards_parse():
    for text in CARDS:
        cd = parse_card(yaml.safe_load(text), TABLES)
        assert "kizuna" in cd.keywords
