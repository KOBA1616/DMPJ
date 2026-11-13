"""語彙パイロット第149弾（D・D・Dライダー）: 対象11枚の手書き変換の形を固定する。

設計ノート pilot149-d-d-d-rider-design §6 の変換形どおりに書いた YAML が
parse_card（検証込み）を通ることと、declare の via / ライダー誘発の when /
呪文の if: {ddd_paid} の形を固定する。登録（submit）は行わない（実装と変換は分ける）。
複合4枚は残る unsupported の内訳まで固定する。
"""
import yaml
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()


def _parse(text):
    return parse_card(yaml.safe_load(text), TABLES)


def _declares(card):
    return [a for a in card.abilities if a.get("kind") == "declare"]


def _play_self(declare):
    return declare["effect"][0]["body"][0]


def _rider(card):
    return next(a for a in card.abilities if a.get("kind") == "trigger"
                and (a.get("when") or {}).get("via") == "d_d_d")


def _needs(card):
    return {u["need"] for u in (card.source.get("unsupported") or [])}


# ---------------------------------------------------------------- 単独7枚

def test_dm25ex3_021():
    """魔誕妖蟲デンジャラス・ワーム: D・D・Dで出た時、墓地とマナからコスト4以下を1体ずつ出してもよい。"""
    c = _parse("""
id: dm25ex3-021
name: 魔誕妖蟲デンジャラス・ワーム
civs: [fire]
cost: 2
power: 2000
types: [creature]
races: [パラサイトワーム]
mana: 1
keywords: [guardman]
text: D・D・D。ガードマン。このクリーチャーが「D・D・D」によって出た時、コスト４以下のエレメントを１つ、自分の墓地から出してもよい。そうしたら、コスト４以下のエレメントを１つ、自分のマナゾーンから出してもよい。このクリーチャーが離れる時、かわりに手札を１枚捨ててもよい。そうしたら、カードを２枚引く。
abilities:
  - kind: declare
    zone: hand
    when: {event: attack, subject: {owner: you, filter: {types: [creature]}}}
    effect:
      - op: may
        body:
          - {op: play_self, cost: 6, civs: [darkness, fire, nature], via: d_d_d}
  - kind: trigger
    when: {event: move, subject: self, to: bz, via: d_d_d}
    effect:
      - op: may
        body:
          - {op: move, select: {zone: graveyard, owner: you, filter: {cost_le: 4}, count: 1, up_to: true}, to: bz, reason: put}
      - op: may
        body:
          - {op: move, select: {zone: mana, owner: you, filter: {cost_le: 4}, count: 1, up_to: true}, to: bz, reason: put}
  - kind: trigger
    when: {event: move, from: bz, subject: self}
    effect:
      - op: may
        body:
          - {op: discard, select: {zone: hand, owner: you, count: 1}, as: paid}
          - op: if
            cond: {exists: {ref: paid}}
            then:
              - {op: draw, count: 2}
source: {official: dm25ex3-021, review: pending}
""")
    assert _play_self(_declares(c)[0])["via"] == "d_d_d"
    w = _rider(c)["when"]
    assert w["event"] == "move" and w["to"] == "bz" and w["subject"] == "self"
    moves = [_rider(c)["effect"][0]["body"][0], _rider(c)["effect"][1]["body"][0]]
    assert [m["select"]["zone"] for m in moves] == ["graveyard", "mana"]
    assert all(m["select"]["up_to"] and m["reason"] == "put" for m in moves)


def test_dm25ex3_026():
    """剣轟奥義 ドドド・ドギラゴン・ドライブ: D・D・Dで唱えたなら、マナの数−1以下のエレメントをマナから出してもよい。"""
    c = _parse("""
id: dm25ex3-026
name: 剣轟奥義 ドドド・ドギラゴン・ドライブ
civs: [nature]
cost: 4
types: [spell]
mana: 1
text: D・D・D。自分の山札の上から２枚を見る。その中から、クリーチャーとタマシードをすべて手札に加え、残りをタップしてマナゾーンに置く。この呪文を「D・D・D」で唱えたなら、コストが（自分のマナゾーンにあるカードの数－１）以下のエレメントを１つ、自分のマナゾーンから出してもよい。
abilities:
  - kind: declare
    zone: hand
    when: {event: attack, subject: {owner: you, filter: {types: [creature]}}}
    effect:
      - op: may
        body:
          - {op: play_self, cost: 7, civs: [nature], via: d_d_d}
spell:
  - {op: choose, select: {zone: deck, owner: you, from_top: 2, look: true, count: all}, as: pile}
  - {op: move, select: {ref: pile, filter: {types: [creature, tamaseed]}, count: any}, to: hand, reason: return}
  - {op: move, select: {ref: pile, count: all}, to: mana, reason: put, tapped: true}
  - op: if
    cond: {ddd_paid: true}
    then:
      - op: may
        body:
          - op: move
            select: {zone: mana, owner: you, filter: {types: [creature, tamaseed], cost_le: {sum: [{count: {zone: mana, owner: you}}, -1]}}, count: 1}
            to: bz
            reason: put
source: {official: dm25ex3-026, review: pending}
""")
    assert _play_self(_declares(c)[0])["via"] == "d_d_d"
    tail = c.spell[-1]
    assert tail["op"] == "if" and tail["cond"] == {"ddd_paid": True}
    mv = tail["then"][0]["body"][0]
    assert mv["select"]["filter"]["cost_le"]["sum"][1] == -1    # 「マナの数－1」
    assert mv["select"]["zone"] == "mana" and mv["to"] == "bz"


_RP3011_MODES = """          - - {op: choose, select: {zone: bz, owner: you, filter: {types: [creature]}, count: 1}, as: tgt}
            - {op: delayed_trigger, when: {event: attack_end, subject: {ref: tgt}}, duration: end_of_turn, effect: [{op: untap, select: {ref: tgt}}]}
          - - {op: untap, select: {zone: mana, owner: you, count: 4}}
          - - {op: mill, owner: you, count: 3}
            - {op: move, select: {zone: graveyard, owner: you, filter: {types: [creature]}, count: 1}, to: hand, reason: return}
"""


def test_dm25ex3_rp3011():
    """弐闘路と轟点火の決断: モード数を if で書き分ける（通常2つ・重複可／D・D・Dなら3つ・重複なし）。"""
    c = _parse("""
id: dm25ex3-rp3011
name: 弐闘路と轟点火の決断
civs: [darkness, fire, nature]
cost: 5
types: [spell]
mana: 1
text: D・D・D。次の中から２つ選ぶ。（同じものを２回選んでもよい）この呪文を「D・D・D」で唱えたなら、３つ選ぶ。（同じものは１回だけ）
abilities:
  - kind: declare
    zone: hand
    when: {event: attack, subject: {owner: you, filter: {types: [creature]}}}
    effect:
      - op: may
        body:
          - {op: play_self, cost: 3, civs: [darkness, fire, nature], via: d_d_d}
spell:
  - op: if
    cond: {ddd_paid: true}
    then:
      - op: modal
        count: 3
        modes:
""" + _RP3011_MODES + """    else:
      - op: modal
        count: 2
        repeat: true
        modes:
""" + _RP3011_MODES + """source: {official: dm25ex3-rp3011, review: pending}
""")
    assert _play_self(_declares(c)[0])["via"] == "d_d_d"
    head = c.spell[0]
    assert head["cond"] == {"ddd_paid": True}
    assert head["then"][0]["count"] == 3 and "repeat" not in head["then"][0]
    assert head["else"][0]["count"] == 2 and head["else"][0]["repeat"] is True
    assert head["then"][0]["modes"] == head["else"][0]["modes"]


_RP3S08_MODES = """          - - {op: draw, count: 2}
            - {op: choose, select: {zone: hand, owner: you, count: 1}, as: c}
            - op: modal
              modes:
                - - {op: move, select: {ref: c}, to: deck, position: top, reason: put}
                - - {op: move, select: {ref: c}, to: deck, position: bottom, reason: put}
          - - {op: play_free, select: {zone: hand, owner: you, filter: {cost_le: 3}, count: 1}}
          - - {op: move, select: {zone: bz, owner: any, filter: {cost_le: 6}, count: 1}, to: mana, reason: put}
"""


def test_dm25ex3_rp3s08():
    """心転地と透幻郷の決断: 手札・マナの2つの declare に via。通常2つ／D・D・Dなら3つ（どちらも重複可）。"""
    c = _parse("""
id: dm25ex3-rp3s08
name: 心転地と透幻郷の決断
civs: [light, water, nature]
cost: 4
types: [spell]
mana: 1
text: D・D・D（自分のクリーチャーが攻撃する時、このターン、このカードを自分の手札またはマナゾーンから実行してもよい）。次の中から２つ選ぶ。（同じものを２回選んでもよい）この呪文を「D・D・D」で唱えたなら、３つ選ぶ。（同じものを３回選んでもよい）
abilities:
  - kind: declare
    zone: hand
    when: {event: attack, subject: {owner: you, filter: {types: [creature]}}}
    effect:
      - op: may
        body:
          - {op: play_self, cost: 5, civs: [light, water, nature], via: d_d_d}
  - kind: declare
    zone: mana
    when: {event: attack, subject: {owner: you, filter: {types: [creature]}}}
    effect:
      - op: may
        body:
          - {op: play_self, cost: 5, civs: [light, water, nature], via: d_d_d}
spell:
  - op: if
    cond: {ddd_paid: true}
    then:
      - op: modal
        count: 3
        repeat: true
        modes:
""" + _RP3S08_MODES + """    else:
      - op: modal
        count: 2
        repeat: true
        modes:
""" + _RP3S08_MODES + """source: {official: dm25ex3-rp3s08, review: pending}
""")
    ds = _declares(c)
    assert [d["zone"] for d in ds] == ["hand", "mana"]          # declare はゾーンごとに複製
    assert all(_play_self(d)["via"] == "d_d_d" for d in ds)
    head = c.spell[0]
    assert head["then"][0]["count"] == 3 and head["then"][0]["repeat"] is True
    assert head["else"][0]["count"] == 2 and head["else"][0]["repeat"] is True


def test_dm25ex3_rp4007():
    """アセビ with 9OD-2: D・D・Dで出た時、そのターン中、自分のクリーチャーすべてが強化される。"""
    c = _parse("""
id: dm25ex3-rp4007
name: アセビ with 9OD-2
civs: [nature]
cost: 2
power: 3000
types: [creature]
races: [スノーフェアリー, テクノ・サムライ]
mana: 1
text: D・D・D。このクリーチャーが「D・D・D」によって出た時、このターン、自分のクリーチャーすべてのパワーを２倍にし、「パワード・ブレイカー」を与え、バトルに勝つ。相手のターン中に、相手がコストを支払わずにクリーチャーを出した時、自分のマナゾーンにあるクリーチャーを１体、出してもよい。そのクリーチャーのコストは、出たクリーチャーのコスト以下でなければならない。
abilities:
  - kind: declare
    zone: hand
    when: {event: attack, subject: {owner: you, filter: {types: [creature]}}}
    effect:
      - op: may
        body:
          - {op: play_self, cost: 6, civs: [light, fire, nature], via: d_d_d}
  - kind: trigger
    when: {event: move, subject: self, to: bz, via: d_d_d}
    effect:
      - op: modify
        select: {zone: bz, owner: you, filter: {types: [creature]}, count: all}
        mod: {double_power: true, grant: [powered_breaker], win_all_battles: true}
        duration: end_of_turn
  - kind: trigger
    when: {event: move, to: bz, subject: {owner: opp}, unpaid: true}
    effect:
      - op: may
        body:
          - {op: move, select: {zone: mana, owner: you, filter: {types: [creature], cost_le: {cost_of: event.subject}}, count: 1}, to: bz, reason: put}
source: {official: dm25ex3-rp4007, review: pending}
""")
    assert _play_self(_declares(c)[0])["via"] == "d_d_d"
    mod = _rider(c)["effect"][0]
    assert mod["op"] == "modify" and mod["select"]["count"] == "all"
    assert mod["mod"] == {"double_power": True, "grant": ["powered_breaker"],
                          "win_all_battles": True}
    assert mod["duration"] == "end_of_turn"


def test_dm25rp4_019():
    """愛馬 デンジャラス=スベルニル: D・D・Dで出た時、2ドロー1ディス→墓地からコスト8以下をSA化して出してもよい。"""
    c = _parse("""
id: dm25rp4-019
name: 愛馬 デンジャラス=スベルニル
civs: [darkness]
cost: 2
power: 2000
types: [creature]
races: [アビスロイヤル]
mana: 1
keywords: [slayer]
text: D・D・D。スレイヤー。このクリーチャーが「D・D・D」によって出た時、カードを２枚引いてから、自分の手札を１枚捨てる。その後、コスト８以下のクリーチャーを１体、自分の墓地から出してもよい。そのクリーチャーに「スピードアタッカー」を与える。相手がコストを支払わずにクリーチャーを出した時、自分は相手の手札を１枚見ないで選び、捨てさせる。
abilities:
  - kind: declare
    zone: hand
    when: {event: attack, subject: {owner: you, filter: {types: [creature]}}}
    effect:
      - op: may
        body:
          - {op: play_self, cost: 6, civs: [water, darkness, fire], via: d_d_d}
  - kind: trigger
    when: {event: move, subject: self, to: bz, via: d_d_d}
    effect:
      - {op: draw, count: 2}
      - {op: discard, select: {zone: hand, owner: you, count: 1}}
      - op: may
        body:
          - {op: move, select: {zone: graveyard, owner: you, filter: {types: [creature], cost_le: 8}, count: 1}, to: bz, reason: put, as: came}
          - {op: modify, select: {ref: came}, mod: {grant: [speed_attacker]}, duration: end_of_turn}
  - kind: trigger
    when: {event: move, to: bz, subject: {owner: opp, filter: {types: [creature]}}, unpaid: true}
    effect:
      - {op: discard, select: {zone: hand, owner: opp, count: 1}}
source: {official: dm25rp4-019, review: pending}
""")
    assert _play_self(_declares(c)[0])["via"] == "d_d_d"
    eff = _rider(c)["effect"]
    assert [o["op"] for o in eff] == ["draw", "move", "may"]    # discard はマクロで move に展開される
    assert eff[1]["select"]["zone"] == "hand" and eff[1]["to"] == "graveyard"
    put = eff[2]["body"][0]
    assert put["select"]["zone"] == "graveyard" and put["select"]["filter"]["cost_le"] == 8
    assert eff[2]["body"][1]["mod"] == {"grant": ["speed_attacker"]}


def test_dm25ex3_038():
    """♪離れても 周りが廻り 離回りなり: D・D・Dで唱えたなら、次の自分のターンのはじめまで自分のシールドすべてにS・トリガーを与える。"""
    c = _parse("""
id: dm25ex3-038
name: ♪離れても 周りが廻り 離回りなり
civs: [light]
cost: 2
types: [spell]
races: [マジック・ソング]
mana: 1
text: D・D・D。自分の山札の上から１枚をシールド化する。この呪文を「D・D・D」で唱えたなら、次の自分のターンのはじめまで、自分のシールドゾーンにあるカードすべてに「S・トリガー」を与える。
abilities:
  - kind: declare
    zone: hand
    when: {event: attack, subject: {owner: you, filter: {types: [creature]}}}
    effect:
      - op: may
        body:
          - {op: play_self, cost: 3, civs: [light], via: d_d_d}
spell:
  - {op: move, select: {zone: deck, owner: you, from_top: 1}, to: shield, reason: charge}
  - op: if
    cond: {ddd_paid: true}
    then:
      - op: modify
        select: {zone: shield, owner: you, count: all}
        mod: {grant: [s_trigger]}
        duration: until_next_own_turn_start
source: {official: dm25ex3-038, review: pending}
""")
    assert _play_self(_declares(c)[0])["via"] == "d_d_d"
    tail = c.spell[-1]
    assert tail["op"] == "if" and tail["cond"] == {"ddd_paid": True}
    grant = tail["then"][0]
    assert grant["mod"] == {"grant": ["s_trigger"]}
    assert grant["select"]["zone"] == "shield" and grant["select"]["count"] == "all"
    assert grant["duration"] == "until_next_own_turn_start"


# ---------------------------------------------------------------- 複合4枚（parse のみ＋残 unsupported の固定）

def test_dm25ex3_010_composite():
    """～その怪物、害悪なり～: ライダー本体は書ける。残るのは cip_trigger_double のみ（本弾の範囲外）。"""
    c = _parse("""
id: dm25ex3-010
name: ～その怪物、害悪なり～
civs: [water]
cost: 2
power: 2000
types: [creature]
races: [アースイーター, スチーム・ナイト]
mana: 1
keywords: [blocker]
text: D・D・D。ブロッカー。このクリーチャーが「D・D・D」によって出た時、コスト６以下のクリーチャーを１体、自分の、手札または墓地からコストを支払わずに召喚してもよい。相手が呪文を唱えた時、自分はカードを１枚引いてもよい。
abilities:
  - kind: declare
    zone: hand
    when: {event: attack, subject: {owner: you, filter: {types: [creature]}}}
    effect:
      - op: may
        body:
          - {op: play_self, cost: 6, civs: [light, water, darkness], via: d_d_d}
  - kind: trigger
    when: {event: move, subject: self, to: bz, via: d_d_d}
    effect:
      - op: may
        body:
          - {op: move, select: {zone: [hand, graveyard], owner: you, filter: {types: [creature], cost_le: 6}, count: 1}, to: bz, reason: summon}
  - kind: trigger
    when: {event: cast, subject: {owner: opp, filter: {types: [spell]}}}
    effect:
      - op: may
        body:
          - {op: draw, count: 1}
source:
  official: dm25ex3-010
  review: pending
  unsupported:
    - {need: cip_trigger_double, text: そのクリーチャーの、出た時にトリガーする能力は、１度のかわりに２度トリガーする。}
""")
    assert _play_self(_declares(c)[0])["via"] == "d_d_d"
    mv = _rider(c)["effect"][0]["body"][0]
    assert mv["select"]["zone"] == ["hand", "graveyard"] and mv["reason"] == "summon"
    assert _needs(c) == {"cip_trigger_double"}                 # 範囲外（第149弾では実装しない）


def test_dm25ex3_rp4005_composite():
    """仙界の闘神将 ムロク: declare に via を付ける。ライダーは山札の上が絡むため残るのは deck_top 系のみ。"""
    c = _parse("""
id: dm25ex3-rp4005
name: 仙界の闘神将 ムロク
civs: [fire]
cost: 3
power: 4000
types: [creature]
races: [スターノイド, テクノ・サムライ]
mana: 1
text: D・D・D。自分のNEOクリーチャーの召喚コストを１少なくする。
abilities:
  - kind: static
    affects: {owner: you, zone: hand, filter: {types: [creature], race_has: NEO}}
    mod: {cost: -1}
  - kind: declare
    zone: hand
    when: {event: attack, subject: {owner: you, filter: {types: [creature]}}}
    effect:
      - op: may
        body:
          - {op: play_self, cost: 5, civs: [fire], via: d_d_d}
source:
  official: dm25ex3-rp4005
  review: pending
  unsupported:
    - {need: deck_top_look, text: 自分のターン中、自分の山札の上から１枚をいつでも見てもよい。}
    - {need: summon_from_deck_top, text: このクリーチャーが「D・D・D」によって出た時、このクリーチャーから進化できるコスト７以下のクリーチャーを１体、自分の手札または山札の上から、このクリーチャーの上に置いてもよい。自分のターン中、NEOクリーチャーを自分の山札の上から召喚してもよい。（コストは支払う）}
""")
    assert _play_self(_declares(c)[0])["via"] == "d_d_d"
    assert _needs(c) == {"deck_top_look", "summon_from_deck_top"}   # d_d_d_rider は消える


def test_dm25ex3_rp4s05_composite():
    """「K」-9+9+9: ライダー本体（マナから12体まで出す）は書ける。

    「出ることによって起こる効果やルールはすべて無視する」は本弾の範囲外（親判断）で、
    unsupported に仮の need 名 enter_effects_ignored で残す（命名は再変換時に確定する）。
    """
    c = _parse("""
id: dm25ex3-rp4s05
name: 「K」-9+9+9
civs: [nature]
cost: 6
power: 12000
types: [creature]
races: [グランセクト, テクノ・サムライ]
mana: 1
keywords: [triple_breaker]
text: D・D・D。マッハファイター。T・ブレイカー。このクリーチャーが「D・D・D」によって出た時、クリーチャーを12体まで、自分のマナゾーンから出す。このクリーチャーが出た時または攻撃する時、自分の山札の上から２枚をマナゾーンに置く。
abilities:
  - kind: trigger
    when: {event: move, to: bz, subject: self}
    effect:
      - {op: modify, select: {ref: self}, mod: {allow: [{action: attack_creature, other: {tapped: false}}]}, duration: end_of_turn}
  - kind: trigger
    when: {event: move, to: bz, subject: self}
    effect:
      - {op: move, select: {zone: deck, owner: you, from_top: 2}, to: mana, reason: put}
  - kind: trigger
    when: {event: attack, subject: self}
    effect:
      - {op: move, select: {zone: deck, owner: you, from_top: 2}, to: mana, reason: put}
  - kind: declare
    zone: hand
    when: {event: attack, subject: {owner: you, filter: {types: [creature]}}}
    effect:
      - op: may
        body:
          - {op: play_self, cost: 12, civs: [nature], via: d_d_d}
  - kind: trigger
    when: {event: move, subject: self, to: bz, via: d_d_d}
    effect:
      - {op: move, select: {zone: mana, owner: you, filter: {types: [creature]}, count: 12, up_to: true}, to: bz, reason: put}
source:
  official: dm25ex3-rp4s05
  review: pending
  unsupported:
    - {need: enter_effects_ignored, text: これらのクリーチャーが出ることによって起こる効果やルールはすべて無視する。}
    - {need: must_be_attacked_first_only, text: 各ターン、相手のクリーチャーがはじめて攻撃する時、可能ならこのクリーチャーを攻撃する。}
""")
    assert _play_self(_declares(c)[0])["via"] == "d_d_d"
    mv = _rider(c)["effect"][0]
    assert mv["select"]["count"] == 12 and mv["select"]["up_to"] is True
    assert _needs(c) == {"enter_effects_ignored", "must_be_attacked_first_only"}


def test_dm25rp4_012_composite():
    """創世竜 ゴルギーネクスト: ライダーは本弾では書かない（効果側の精査は再変換時）。

    declare に via だけ付け、unsupported には d_d_d_rider を残す
    （シャッフル→公開→無料実行/手札かマナ の複合は再変換ラウンドで精査する）。
    """
    c = _parse("""
id: dm25rp4-012
name: 創世竜 ゴルギーネクスト
civs: [light]
cost: 3
power: 4000
types: [creature]
races: [メカ・デル・ディネロ, スーパーカー・ドラゴン]
mana: 1
keywords: [escape]
text: D・D・D。エスケープ。
abilities:
  - kind: declare
    zone: hand
    when: {event: attack, subject: {owner: you, filter: {types: [creature]}}}
    effect:
      - op: may
        body:
          - {op: play_self, cost: 4, civs: [light, water, nature], via: d_d_d}
source:
  official: dm25rp4-012
  review: pending
  unsupported:
    - {need: d_d_d_rider, text: このクリーチャーが「D・D・D」によって出た時、自分の山札をシャッフルし、上から１枚を表向きにする。それをコストを支払わずに実行してもよい。そうしなければ、手札に加えるかマナゾーンに置く。}
    - {need: per_turn_entry_limit, text: 相手は各ターン、クリーチャーを２体までしか出せない。}
""")
    assert _play_self(_declares(c)[0])["via"] == "d_d_d"
    assert not any((a.get("when") or {}).get("via") for a in c.abilities if a.get("kind") == "trigger")
    assert _needs(c) == {"d_d_d_rider", "per_turn_entry_limit"}
