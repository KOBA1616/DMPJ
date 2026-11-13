"""hyper_release: 対象7件全件の手変換 parse。

変換の型は op `hyper_release {select}`（期限は書かない＝st_start の無条件解除と一致。
ハイパー化のタップ手順とは別）。手変換は rejects の partial に解放の部分を足し、
unsupported から hyper_release を外したもの。登録（submit）は行わない。
設計ノート: pilot156-hyper-release-design.md（ツリー内では第157弾）。
"""
import yaml
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

SEL1 = {"zone": "bz", "owner": "you", "count": 1, "filter": {"types": ["creature"], "race_has": "超化獣"}}


def _parse(text):
    return parse_card(yaml.safe_load(text), TABLES)


def _ops(c, key="abilities"):
    out = []
    for a in c.abilities:
        if a["kind"] == "trigger":
            out += a["effect"]
    return out


def test_dm24ex3_066():
    """コッコ・格・ルピア: 攻撃時、自分の超化獣1体を解放（A型・他者）。"""
    c = _parse("""
id: dm24ex3-066
name: コッコ・格・ルピア
types: [creature]
civs: [fire]
cost: 4
power: 4000
races: [アーマード・ファイアー・バード]
mana: 1
keywords: [speed_attacker]
text: このクリーチャーが攻撃する時、次の自分のターンのはじめまで、自分の超化獣クリーチャー１体のハイパーモードを解放する。
abilities:
  - kind: trigger
    when: {event: attack, subject: self}
    effect:
      - {op: hyper_release, select: {zone: bz, owner: you, count: 1, filter: {types: [creature], race_has: 超化獣}}}
source: {official: dm24ex3-066, review: pending}
""")
    assert _ops(c) == [{"op": "hyper_release", "select": SEL1}]


def test_dm24ex3_072():
    """ルナサンライト コハク: 出た時、自分の超化獣1体を解放（A型・他者）。"""
    c = _parse("""
id: dm24ex3-072
name: ルナサンライト コハク
types: [creature]
civs: [nature]
cost: 4
power: 5000
races: [ジャイアント・スノーフェアリー]
mana: 1
text: このクリーチャーが出た時、次の自分のターンのはじめまで、自分の超化獣クリーチャー１体のハイパーモードを解放する。このクリーチャーがタップした時、自分の山札の上から１枚目をマナゾーンに置く。
abilities:
  - kind: trigger
    when: {event: move, to: bz, subject: self}
    effect:
      - {op: hyper_release, select: {zone: bz, owner: you, count: 1, filter: {types: [creature], race_has: 超化獣}}}
  - kind: trigger
    when: {event: tap, subject: self}
    effect:
      - {op: move, select: {zone: deck, owner: you, count: 1, from_top: 1}, to: mana, reason: put}
source: {official: dm24ex3-072, review: pending}
""")
    assert {"op": "hyper_release", "select": SEL1} in _ops(c)


def test_dm24rp2_065():
    """超侵入（呪文）: 相手が選んで破壊＋自分の超化獣1体を解放（A型・他者）。"""
    c = _parse("""
id: dm24rp2-065
name: 超侵入
types: [spell]
civs: [darkness]
cost: 4
keywords: [s_trigger]
text: 相手は自身のアンタップしているクリーチャーを１体選び、破壊する。次の自分のターンのはじめまで、自分の超化獣クリーチャー１体のハイパーモードを解放する。
spell:
  - {op: destroy, select: {zone: bz, owner: opp, filter: {types: [creature], tapped: false}, count: 1, chooser: opp}}
  - {op: hyper_release, select: {zone: bz, owner: you, count: 1, filter: {types: [creature], race_has: 超化獣}}}
source: {official: dm24rp2-065, review: pending}
""")
    assert c.spell[1] == {"op": "hyper_release", "select": SEL1}


def test_dm24ex3_sec13():
    """ハイパー・エントリー（呪文）: 手札から出して解放＋ブロッカー付与（A型・参照）。"""
    c = _parse("""
id: dm24ex3-sec13
name: ハイパー・エントリー
types: [spell]
civs: [light]
cost: 5
keywords: [s_trigger]
text: コスト７以下の超化獣クリーチャーを１体、自分の手札から出してもよい。次の自分のターンのはじめまで、そのクリーチャーのハイパーモードを解放し、「ブロッカー」を与える。
spell:
  - op: may
    body:
      - {op: move, select: {zone: hand, owner: you, count: 1, filter: {types: [creature], race_has: 超化獣, cost_le: 7}}, to: bz, reason: put, as: ent}
  - {op: hyper_release, select: {ref: ent}}
  - {op: modify, select: {ref: ent}, mod: {grant: [blocker]}, duration: until_next_own_turn_start}
source: {official: dm24ex3-sec13, review: pending}
""")
    assert c.spell[1] == {"op": "hyper_release", "select": {"ref": "ent"}}


def test_dm24rp2_015():
    """文藍月 Eine k'Reine: 出た時、このクリーチャー自身を解放（B型・自己）。"""
    c = _parse("""
id: dm24rp2-015
name: 文藍月 Eine k'Reine
types: [creature]
civs: [water]
cost: 3
power: 4000
races: [マジック・スプラッシュ・クイーン, 超化獣]
mana: 1
hyper: true
keywords: [s_trigger, blocker]
text: このクリーチャーが出た時、次の自分のターンのはじめまで、このクリーチャーのハイパーモードを解放する。
abilities:
  - kind: static
    affects: self
    mod: {power: 4000}
    if: {hyper: true}
  - kind: static
    affects: self
    mod: {grant: [double_breaker]}
    if: {hyper: true}
  - kind: trigger
    when: {event: move, to: bz, subject: self}
    effect:
      - {op: hyper_release, select: {ref: self}}
source: {official: dm24rp2-015, review: pending}
""")
    assert _ops(c) == [{"op": "hyper_release", "select": {"ref": "self"}}]


def test_dm24ex3_rp2s09():
    """森翠月 ゴルファンタジスタ: ハイパー面の攻撃時誘発で自分の超化獣すべてを解放（B型・全体）。"""
    c = _parse("""
id: dm24ex3-rp2s09
name: 森翠月 ゴルファンタジスタ
types: [creature]
civs: [nature]
cost: 5
power: 6000
races: [ジャイアント・ドラゴン, 超化獣]
mana: 1
hyper: true
keywords: [double_breaker]
text: このクリーチャーが攻撃する時、次の自分のターンのはじめまで、自分の超化獣クリーチャーすべてのハイパーモードを解放する。
abilities:
  - kind: static
    affects: self
    mod: {power: 5000}
    if: {hyper: true}
  - kind: trigger
    when: {event: move, to: bz, subject: self}
    effect:
      - {op: modify, select: {ref: self}, mod: {allow: [{action: attack_creature, other: {tapped: false}}]}, duration: end_of_turn}
  - kind: static
    affects: {zone: hand, owner: you, count: all, filter: {types: [creature], race_has: 超化獣}}
    mod: {cost: -3}
  - kind: trigger
    when: {event: attack, subject: self}
    if: {hyper: true}
    effect:
      - {op: hyper_release, select: {zone: bz, owner: you, count: all, filter: {types: [creature], race_has: 超化獣}}}
source: {official: dm24ex3-rp2s09, review: pending}
""")
    trig = [a for a in c.abilities if a["kind"] == "trigger" and a.get("if") == {"hyper": True}]
    assert trig and trig[0]["effect"][0]["select"]["count"] == "all"


def test_dm24rp2_070():
    """ハイパー・キャストオフ（呪文）: 選んだ1体が超化獣なら解放。その後バトル（C型・条件つき）。"""
    c = _parse("""
id: dm24rp2-070
name: ハイパー・キャストオフ
types: [spell]
civs: [fire]
cost: 2
keywords: [s_trigger]
text: 自分のクリーチャーを１体選ぶ。それが超化獣であれば、次の自分のターンのはじめまで、そのハイパーモードを解放する。その後、相手のクリーチャーを１体選んでもよい。その２体をバトルさせる。
spell:
  - {op: choose, select: {zone: bz, owner: you, count: 1, filter: {types: [creature]}}, as: a}
  - op: if
    cond: {exists: {ref: a, filter: {race_has: 超化獣}}}
    then:
      - {op: hyper_release, select: {ref: a}}
  - op: may
    body:
      - {op: choose, select: {zone: bz, owner: opp, count: 1, filter: {types: [creature]}}, as: b}
      - {op: force_battle, a: {ref: a}, b: {ref: b}}
source: {official: dm24rp2-070, review: pending}
""")
    assert c.spell[1]["then"] == [{"op": "hyper_release", "select": {"ref": "a"}}]
