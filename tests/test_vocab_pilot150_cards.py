"""語彙パイロット第150弾（進化元になる時）: 代表4枚の手書き変換の形を固定する。

設計ノート pilot150-evo-base-design §3.6 の変換形どおりに書いた YAML が
parse_card（検証込み）を通ることと、when: {event: evolve_base, subject: self} と
付与先 {ref: event.top} の形を固定する。登録（submit）は行わない（実装と変換は分ける）。
手変換は rejects の partial（出た時側・CIP 側）に evolve_base 側を足したもの。
"""
import yaml
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()


def _parse(text):
    return parse_card(yaml.safe_load(text), TABLES)


def _evo_base(card):
    return next(a for a in card.abilities if a.get("kind") == "trigger"
                and (a.get("when") or {}).get("event") == "evolve_base")


def test_dmrp22_025():
    """レヴィヤの地版（型S）: シンカパワーは出た時と同文の効果を evolve_base で書く。"""
    c = _parse("""
id: dmrp22-025
name: レヴィヤの地版
types: [tamaseed]
civs: [nature]
cost: 5
mana: 1
races: [レッド・コマンド・ドラゴン, スノーフェアリー, レクスターズ]
keywords: [s_trigger, shinka_rise]
text: S・トリガー。シンカライズ。このタマシードが出た時、コスト３以下のクリーチャー１体またはコスト３以下のタマシードを１枚、自分のマナゾーンから出してもよい。シンカパワー：このタマシードが進化する時、コスト３以下のクリーチャー１体またはコスト３以下のタマシードを１枚、自分のマナゾーンから出してもよい。
abilities:
  - kind: trigger
    when: {event: move, to: bz, subject: self}
    effect:
      - op: may
        body:
          - {op: move, select: {zone: mana, owner: you, filter: {types: [creature, tamaseed], cost_le: 3}, count: 1}, to: bz, reason: put}
  - kind: trigger
    when: {event: evolve_base, subject: self}
    effect:
      - op: may
        body:
          - {op: move, select: {zone: mana, owner: you, filter: {types: [creature, tamaseed], cost_le: 3}, count: 1}, to: bz, reason: put}
source: {official: dmrp22-025, review: pending}
""")
    ab = _evo_base(c)
    assert ab["when"] == {"event": "evolve_base", "subject": "self"}
    cip = next(a for a in c.abilities if (a.get("when") or {}).get("event") == "move")
    assert ab["effect"] == cip["effect"]   # 出た時と同文の効果


def test_dm25rp2_058():
    """～淡き舵取りの唄～（型N）: 進化して出た時（stacked）と進化元になる時（evolve_base）の併記。"""
    c = _parse("""
id: dm25rp2-058
name: ～淡き舵取りの唄～
types: [creature]
civs: [water]
cost: 2
power: 2000
races: [サイバー・ウイルス, スチーム・ナイト]
mana: 1
neo: true
evolve_from: {civs: [light, water, darkness]}
text: NEO進化：光、水、または闇のクリーチャー１体の上に置いてもよい。（カードが下にあれば、これをNEO進化クリーチャーとして扱う）このクリーチャーが、進化して出た時、または進化元になる時、カードを１枚引いてもよい。
abilities:
  - kind: trigger
    when: {event: move, stacked: true, subject: self, to: bz}
    effect:
      - {op: may, body: [{op: draw, count: 1}]}
  - kind: trigger
    when: {event: evolve_base, subject: self}
    effect:
      - {op: may, body: [{op: draw, count: 1}]}
source: {official: dm25rp2-058, review: pending}
""")
    ab = _evo_base(c)
    assert ab["when"] == {"event": "evolve_base", "subject": "self"}
    stacked = next(a for a in c.abilities if (a.get("when") or {}).get("stacked"))
    assert ab["effect"] == stacked["effect"]


def test_dm25rp4_077():
    """スマッシュ・ホーンの地版（型S-a）: 「それに与える」の宛先は event.top（上に乗ったクリーチャー）。"""
    c = _parse("""
id: dm25rp4-077
name: スマッシュ・ホーンの地版
types: [tamaseed]
civs: [nature]
cost: 6
mana: 1
races: [ホーン・ビースト, サバイバー, フュージョナー]
keywords: [s_trigger, shinka_rise]
text: S・トリガー。このタマシードが出た時、相手のクリーチャーを１体選び、持ち主のマナゾーンに置く。シンカライズ。超魂X。このエレメントが進化元になる時、このターン、それに「マッハファイター」を与える。
abilities:
  - kind: trigger
    when: {event: move, to: bz, subject: self}
    effect:
      - {op: move, select: {zone: bz, owner: opp, filter: {types: [creature]}, count: 1}, to: mana, reason: put}
  - kind: trigger
    when: {event: evolve_base, subject: self}
    effect:
      - {op: modify, select: {ref: event.top}, mod: {allow: [{action: attack_creature, other: {tapped: false}}]}, duration: end_of_turn}
source: {official: dm25rp4-077, review: pending}
""")
    ab = _evo_base(c)
    eff = ab["effect"][0]
    assert eff["op"] == "modify" and eff["select"] == {"ref": "event.top"}   # 宛先は self ではなく上に乗った側
    assert eff["mod"] == {"allow": [{"action": "attack_creature", "other": {"tapped": False}}]}   # マッハファイターの展開形


def test_dm25rp3_044():
    """轟速 ジャ・ターボ3（型N）: 出た時側は D・D・D の declare と stacked、元になる時側は evolve_base。
    同じ破壊効果でも2能力に分ける（この弾の担当は evolve_base 側の追加）。"""
    c = _parse("""
id: dm25rp3-044
name: 轟速 ジャ・ターボ3
types: [creature]
civs: [fire]
cost: 3
power: 3000
races: [ソニック・コマンド, 侵略者]
mana: 1
neo: true
evolve_from: {civs: [darkness, fire, nature]}
text: D・D・D [ff01]。NEO進化：闇、火、または自然のクリーチャー１体の上に置いてもよい。このクリーチャーが、進化して出た時、または進化元になる時、相手の「ブロッカー」を持つクリーチャーを１体選び、破壊してもよい。
abilities:
  - kind: declare
    zone: hand
    when: {event: attack, subject: {owner: you, filter: {types: [creature]}}}
    effect:
      - op: may
        body:
          - {op: play_self, cost: 1, civs: [fire]}
  - kind: trigger
    when: {event: move, to: bz, subject: self, stacked: true}
    effect:
      - {op: may, body: [{op: destroy, select: {zone: bz, owner: opp, filter: {types: [creature], keyword: blocker}, count: 1}}]}
  - kind: trigger
    when: {event: evolve_base, subject: self}
    effect:
      - {op: may, body: [{op: destroy, select: {zone: bz, owner: opp, filter: {types: [creature], keyword: blocker}, count: 1}}]}
source: {official: dm25rp3-044, review: pending}
""")
    ab = _evo_base(c)
    assert ab["when"] == {"event": "evolve_base", "subject": "self"}
    stacked = next(a for a in c.abilities if (a.get("when") or {}).get("stacked"))
    assert ab["effect"] == stacked["effect"]
