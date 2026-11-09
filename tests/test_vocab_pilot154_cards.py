"""語彙パイロット第154弾（crystal_soul）: 代表2枚の手書き変換の形を固定する。

変換の型は「面の宣言 `crystal_soul: N` をトップレベルに書く（キーワード欄には書かない）」。
手変換は rejects の partial に宣言を足し、unsupported から crystal_soul を外したもの。
登録（submit）は行わない（実装と変換は分ける）。
dm24bd6-001（付与側）は eternal_kappa 未実装のため本体の手変換には含めず、付与分は
proto T200（test_vocab_pilot154.py）で代表させる。
"""
import yaml
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()


def _parse(text):
    return parse_card(yaml.safe_load(text), TABLES)


def test_dm23ex3_036():
    """偽りの名 システイス: S・トリガー＋水晶ソウル2＋出た時に相手3体まで攻撃・ブロック不可。"""
    c = _parse("""
id: dm23ex3-036
name: 偽りの名 システイス
types: [creature]
civs: [water]
cost: 7
power: 4000
races: [マジック・コマンド, アンノウン]
mana: 1
crystal_soul: 2
keywords: [s_trigger]
text: S・トリガー（このクリーチャーをシールドゾーンから手札に加える時、コストを支払わずにすぐ召喚してもよい） / 水晶ソウル２（このクリーチャーを召喚する時、自分のマナゾーンにある裏向きのカードのマナの数字は２になる） / このクリーチャーが出た時、相手のクリーチャーを３体まで選ぶ。次の自分のターンのはじめまで、それらのクリーチャーは攻撃もブロックもできない。
abilities:
  - kind: trigger
    when: {event: move, to: bz, subject: self}
    effect:
      - op: modify
        select: {zone: bz, owner: opp, filter: {types: [creature]}, count: {upto: 3}}
        mod: {deny: [attack_creature, attack_player, block]}
        duration: until_next_own_turn_start
source: {official: dm23ex3-036, review: pending}
""")
    assert c.crystal_soul == 2
    assert "crystal_soul" not in c.keywords   # 宣言はキーワード欄には書かない


def test_dm24sp2_008():
    """偽りの名 プラット: S・トリガー＋水晶ソウル2＋出た時にクリーチャー1体をマナへ置いてもよい。"""
    c = _parse("""
id: dm24sp2-008
name: 偽りの名 プラット
types: [creature]
civs: [nature]
cost: 7
power: 5000
races: [ジャイアント, アンノウン]
mana: 1
crystal_soul: 2
keywords: [s_trigger]
text: S・トリガー（このクリーチャーをシールドゾーンから手札に加える時、コストを支払わずにすぐ召喚してもよい） / 水晶ソウル２（このクリーチャーを召喚する時、自分のマナゾーンにある裏向きのカードのマナの数字は２になる） / このクリーチャーが出た時、クリーチャーを１体選び、持ち主のマナゾーンに置いてもよい。
abilities:
  - kind: trigger
    when: {event: move, to: bz, subject: self}
    effect:
      - op: may
        body:
          - {op: move, select: {zone: bz, owner: any, filter: {types: [creature]}, count: 1}, to: mana, reason: put}
source: {official: dm24sp2-008, review: pending, aliases: [dm23ex3-047]}
""")
    assert c.crystal_soul == 2
    assert "crystal_soul" not in c.keywords
