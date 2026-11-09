"""語彙パイロット第153弾（キズナプラス）: 代表4枚の手書き変換の形を固定する。

変換の型は「keywords: [kizuna_plus]＋自身の[P]を kind: partner で書く」。
キズナプラスの展開（攻撃時誘発＋支払い＋2つの[P]を待機効果として使う）は
キーワード側が持つので、カード側は[P]の中身だけを書く。登録（submit）は行わない
（実装と変換は分ける）。手変換は rejects の partial にキズナプラスと[P]を足したもの。
"""
import yaml
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()


def _parse(text):
    return parse_card(yaml.safe_load(text), TABLES)


def _kizuna_plus(card):
    return next(a for a in card.abilities if a.get("keyword") == "kizuna_plus")


def _partner(card):
    return next(a for a in card.abilities if a["kind"] == "partner")


def test_dmrp03_002():
    """記憶の紡ぎ 重音: [P]は「1ドロー→コスト5以下の呪文を手札から無料で唱えてもよい」。"""
    c = _parse("""
id: dmrp03-002
name: 記憶の紡ぎ 重音
types: [creature]
civs: [light]
cost: 4
power: 4000
races: [ドラゴンギルド, メタリカ]
mana: 1
neo: true
evolve_from: {civs: [light]}
keywords: [kizuna_plus]
text: NEO進化：自分の光のクリーチャー1体の上に置いてもよい。（クリーチャーが下にあれば、これをNEO進化クリーチャーとして扱う）キズナプラス（このクリーチャーが攻撃する時、その下にあるカードを1枚、自分の墓地に置いてもよい。そうしたら、このクリーチャーと自分の他のクリーチャー1体の[P]能力を使う）[P]カードを1枚引く。その後、コスト5以下の呪文を1枚、自分の手札からコストを支払わずに唱えてもよい。
abilities:
  - kind: partner
    effect:
      - {op: draw, count: 1}
      - op: may
        body:
          - {op: play_free, select: {zone: hand, owner: you, filter: {types: [spell], cost_le: 5}, count: 1}}
source: {official: dmrp03-002, review: pending}
""")
    _kizuna_plus(c)
    p = _partner(c)
    assert p["effect"][0] == {"op": "draw", "count": 1}
    assert p["effect"][1]["body"][0]["op"] == "play_free"
    assert p["effect"][1]["body"][0]["select"]["filter"] == {"types": ["spell"], "cost_le": 5}


def test_dmrp03_015():
    """鬼動兵 デメタイ: W・ブレイカー＋攻撃の後に手札へ戻る誘発を併せ持ち、
    [P]は「このターン、自分のクリーチャーはブロックされない」。"""
    c = _parse("""
id: dmrp03-015
name: 鬼動兵 デメタイ
types: [creature]
civs: [water]
cost: 4
power: 6000
races: [ムートピア]
mana: 1
neo: true
evolve_from: {civs: [water]}
keywords: [double_breaker, kizuna_plus]
text: NEO進化：自分の水のクリーチャー1体の上に置いてもよい。（クリーチャーが下にあれば、これをNEO進化クリーチャーとして扱う）W・ブレイカー（このクリーチャーはシールドを2つブレイクする）このクリーチャーが攻撃する時、攻撃の後、自分の手札に戻す。キズナプラス（このクリーチャーが攻撃する時、その下にあるカードを1枚、自分の墓地に置いてもよい。そうしたら、このクリーチャーと自分の他のクリーチャー1体の[P]能力を使う）[P]このターン、自分のクリーチャーはブロックされない。
abilities:
  - kind: trigger
    when: {event: attack, subject: self}
    effect:
      - op: delayed_trigger
        when: {event: attack_end}
        duration: during_attack
        effect:
          - {op: move, select: {ref: self}, to: hand, reason: return}
  - kind: partner
    effect:
      - op: modify
        select: {zone: bz, owner: you, filter: {types: [creature]}, count: all}
        mod: {grant: [unblockable]}
        duration: end_of_turn
source: {official: dmrp03-015, review: pending}
""")
    _kizuna_plus(c)
    atk = next(a for a in c.abilities if a["kind"] == "trigger" and not a.get("keyword"))
    assert atk["effect"][0]["op"] == "delayed_trigger"   # 既存の攻撃時誘発（partial）と併存する
    p = _partner(c)
    assert p["effect"][0]["mod"] == {"grant": ["unblockable"]}
    assert p["effect"][0]["duration"] == "end_of_turn"


def test_dmrp04s_029():
    """奇石 ブルーナ: [P]は遅延誘発（このターンの終わりに、自分のクリーチャーを
    好きな数タップまたはアンタップする）。"""
    c = _parse("""
id: dmrp04s-029
name: 奇石 ブルーナ
types: [creature]
civs: [light]
cost: 4
power: 4000
races: [メタリカ]
mana: 1
neo: true
evolve_from: {civs: [light]}
keywords: [kizuna_plus]
text: NEO進化：自分の光のクリーチャー1体の上に置いてもよい。（クリーチャーが下にあれば、これをNEO進化クリーチャーとして扱う）キズナプラス（このクリーチャーが攻撃する時、その下にあるカードを1枚、自分の墓地に置いてもよい。そうしたら、このクリーチャーと自分の他のクリーチャー1体の[P]能力を使う）[P]このターンの終わりに、自分のクリーチャーを好きな数、タップまたはアンタップする。
abilities:
  - kind: partner
    effect:
      - op: delayed_trigger
        when: {event: turn_end, player: you}
        effect:
          - {op: tap, select: {zone: bz, owner: you, filter: {types: [creature], tapped: false}, count: any}}
          - {op: untap, select: {zone: bz, owner: you, filter: {types: [creature], tapped: true}, count: any}}
source: {official: dmrp04s-029, review: pending}
""")
    _kizuna_plus(c)
    p = _partner(c)
    dt = p["effect"][0]
    assert dt["op"] == "delayed_trigger" and dt["when"] == {"event": "turn_end", "player": "you"}
    assert [o["op"] for o in dt["effect"]] == ["tap", "untap"]


def test_dmex06_020():
    """グスタフ・アルブサール: W・ブレイカー併せ持ち。[P]は「進化ではないクリーチャーを
    1体、自分の墓地から出す」（play_free＋not_types: [evolution]。インフェルノ・サインと同型）。"""
    c = _parse("""
id: dmex06-020
name: グスタフ・アルブサール
types: [creature]
civs: [darkness]
cost: 8
power: 11000
races: [マフィ・ギャング]
mana: 1
neo: true
evolve_from: {civs: [darkness]}
keywords: [double_breaker, kizuna_plus]
text: NEO進化：自分の闇のクリーチャー1体の上に置いてもよい。（クリーチャーが下にあれば、これをNEO進化クリーチャーとして扱う）W・ブレイカーキズナプラス（このクリーチャーが攻撃する時、その下にあるカードを1枚、自分の墓地に置いてもよい。そうしたら、このクリーチャーと自分の他のクリーチャー1体の[P]能力を使う）[P]進化ではないクリーチャーを1体、自分の墓地からバトルゾーンに出す。
abilities:
  - kind: partner
    effect:
      - {op: play_free, select: {zone: graveyard, owner: you, filter: {types: [creature], not_types: [evolution]}, count: 1}}
source: {official: dmex06-020, review: pending}
""")
    _kizuna_plus(c)
    p = _partner(c)
    assert p["effect"][0]["op"] == "play_free"
    assert p["effect"][0]["select"]["filter"] == {"types": ["creature"], "not_types": ["evolution"]}
