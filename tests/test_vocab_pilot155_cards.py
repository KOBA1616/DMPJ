"""語彙パイロット第155弾（リンクした時）: 代表2枚の手書き変換の形を固定する。

when: {event: link_established, subject: self} の形と、枚数条件を能力の if の
link_count 式で書く形を、実カードの手変換で固定する。登録（submit）は行わない
（実装と変換は分ける）。手変換は rejects の partial にリンク側の能力を足したもの。
パターンA「出た時、またはリンクした時」の6件は本弾の対象外（誘発回数の公式裏取りが
取れていないため）のため、ここには含めない。
"""
import yaml
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()


def _parse(text):
    return parse_card(yaml.safe_load(text), TABLES)


def _link_ab(card):
    return next(a for a in card.abilities if a.get("kind") == "trigger"
                and (a.get("when") or {}).get("event") == "link_established")


def test_dm22ex2_s02():
    """「黒幕」: 「カード3枚でリンクした時」は link_established + if の link_count で書く。
    リンクされる側として成立した場合もこの形で誘発する（公式FAQ: すでに場にいる
    「黒幕」が他のゴッドの登場で3枚リンクした場合もトリガーする）。"""
    c = _parse("""
id: dm22ex2-s02
name: 「黒幕」
types: [creature]
civs: [darkness]
cost: 9
power: 12000
mana: 1
races: [ゴッド・ノヴァ OMG, オラクル]
keywords: [triple_breaker, center_g_link]
text: このクリーチャーが召喚によって出た時、相手は自身の手札をすべて捨てる。T・ブレイカー。中央G・リンク（このクリーチャーまたは自分の他のゴッドを出す時、自分の好きな数のゴッドからカードを１枚ずつリンクを外してもよい。その後、このクリーチャーを、「右G・リンク」または「左G・リンク」を持つゴッドにリンクしてもよい）このクリーチャーがカード３枚でリンクした時、このクリーチャーは各プレイヤーのシールドをすべてブレイクする。
abilities:
  - kind: trigger
    when: {event: summon, subject: self}
    effect:
      - {op: discard, select: {zone: hand, owner: opp, count: all}}
  - kind: trigger
    when: {event: link_established, subject: self}
    if: {cmp: [{link_count: self}, ">=", 3]}
    effect:
      - {op: break, player: you, count: {count: {zone: shield, owner: you}}}
      - {op: break, player: opp, count: {count: {zone: shield, owner: opp}}}
source: {official: dm22ex2-s02, review: pending}
""")
    ab = _link_ab(c)
    assert ab["when"] == {"event": "link_established", "subject": "self"}
    assert ab["if"] == {"cmp": [{"link_count": "self"}, ">=", 3]}


def test_dmr11_004():
    """悪魔右神メタモルフォーゼ: 「ゴッドとリンクした時」は link_established で書く
    （枚数条件なし）。"""
    c = _parse("""
id: dmr11-004
name: 悪魔右神メタモルフォーゼ
types: [creature]
civs: [darkness]
cost: 7
power: 7000
mana: 1
races: [ゴッド・ノヴァ OMG, デーモン・コマンド]
keywords: [double_breaker, right_g_link]
text: 相手のクリーチャーが破壊された時、クリーチャーを１体、自分の墓地から手札に戻してもよい。W・ブレイカー。右G・リンク。このクリーチャーがゴッドとリンクした時、自分の山札の上から２枚を墓地に置いてもよい。
abilities:
  - kind: trigger
    when: {event: move, from: bz, to: graveyard, reason: destroy, subject: {owner: opp, filter: {types: [creature]}}}
    effect:
      - op: may
        body:
          - {op: move, select: {zone: graveyard, owner: you, filter: {types: [creature]}, count: 1}, to: hand, reason: return}
  - kind: trigger
    when: {event: link_established, subject: self}
    effect:
      - op: may
        body:
          - {op: move, select: {zone: deck, owner: you, from_top: 2}, to: graveyard, reason: put}
source: {official: dmr11-004, review: pending}
""")
    ab = _link_ab(c)
    assert ab["when"] == {"event": "link_established", "subject": "self"}
    assert "if" not in ab
