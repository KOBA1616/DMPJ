"""語彙パイロット第46弾: 代表カードの手変換が parse_card を通ること。

- D2-W革命のボルトロン: ターン終了時に自分のクリーチャーへ封印を付ける（再変換ラウンド21で登録した形）
"""
import yaml

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    r'''
id: dm26rp2-051
name: D2-W革命のボルトロン
types:
- creature
civs:
- darkness
- fire
cost: 3
power: 10000
mana: 1
races:
- ソニック・コマンド
- イニシャルズW
keywords:
- double_breaker
text: 'W・ブレイカー（このクリーチャーはシールドを２つブレイクする）

  自分のターンの終わりに、自分のクリーチャー１体に封印を１つ付ける。

  （カードを封印するには、自分の山札の上から１枚を裏向きでそのカードの上に置く。コマンドが出た時、その持ち主はそのコマンドと同じ文明を持つ自身のカードから封印を１つ、墓地に置く。封印されているクリーチャーは無視される）'
abilities:
- kind: trigger
  when:
    event: turn_end
    player: you
  effect:
  - op: attach_seal
    select:
      zone: bz
      owner: you
      filter:
        types:
        - creature
      count: 1
source:
  official: dm26rp2-051
  review: pending
  notes: 原文どおり第46弾の attach_seal で表した。コマンドが出た時の自動解放・封印中は無視される点はエンジン側の処理''',
]


def test_cards_parse():
    for raw in CARDS:
        card = yaml.safe_load(raw)
        parse_card(card, TABLES, where=card["id"])
