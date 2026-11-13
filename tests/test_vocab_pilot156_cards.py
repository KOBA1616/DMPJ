"""leave_under_untap: 代表カードの手変換 parse。

変換の型は「離れた時、その下にあったクリーチャーをアンタップする」を
誘発 `when: {event: move, from: bz, subject: self}` ＋ `{op: untap, select: {ref: event.under}}`
と書く（`to` は付けない＝行き先を問わない。`under_of: self` では書けない）。
手変換は rejects の partial にこの誘発を足し、unsupported から leave_under_untap を
外したもの。登録（submit）は行わない（実装と変換は分ける）。
設計ノート: pilot155-leave-under-untap-design.md（ツリー内では第156弾）。
"""
import yaml
from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()


def _parse(text):
    return parse_card(yaml.safe_load(text), TABLES)


def _leave_trigger(c):
    return [a for a in c.abilities if a["kind"] == "trigger"
            and a["effect"] == [{"op": "untap", "select": {"ref": "event.under"}}]]


def test_dm25ex2_027():
    """ブランド ＜NEXT.Star＞: B・A・D＋W・ブレイカー＋攻撃時誘発＋離脱時アンタップ。"""
    c = _parse("""
id: dm25ex2-027
name: ブランド ＜NEXT.Star＞
types: [creature, evolution]
civs: [fire]
cost: 7
power: 9000
races: [ビートジョッキー, ガイアール・コマンド・ドラゴン, ドラグナー, レクスターズ]
mana: 1
star: true
evolve_from: {any_of: [{race_has: レクスターズ}, {civs: [fire]}]}
keywords: [double_breaker]
text: B･A･D２ / スター進化 / W・ブレイカー / 攻撃時誘発 / このクリーチャーが離れた時、その下にあったクリーチャーをアンタップする。
abilities:
  - kind: static
    affects: self
    zone: hand
    mod: {opt_reduce: {amount: 2, then: destroy}}
  - kind: trigger
    when: {event: attack, subject: self}
    effect:
      - {op: destroy, select: {zone: bz, owner: opp, count: 1, filter: {types: [creature], power_le: 6000}}}
      - op: if
        cond: {cmp: [{count: {zone: mana, owner: you, filter: {types: [creature], civs: [fire], race_has: ドラゴン}}}, ">=", 5]}
        then:
          - op: may
            body:
              - {op: draw, count: 1}
              - op: may
                body:
                  - {op: move, select: {zone: hand, owner: you, count: 1, filter: {types: [creature], race_has: ドラゴン}}, to: bz, reason: put}
  - kind: trigger
    when: {event: move, from: bz, subject: self}
    effect:
      - {op: untap, select: {ref: event.under}}
source: {official: dm25ex2-027, review: pending, aliases: [dmex19-010]}
""")
    assert _leave_trigger(c)
    assert c.star is True


def test_dmrp18_080():
    """ダチッコ ＜マック.Star＞: パワーアタッカー+6000＋W・ブレイカー＋離脱時アンタップ。"""
    c = _parse("""
id: dmrp18-080
name: ダチッコ ＜マック.Star＞
types: [creature, evolution]
civs: [fire]
cost: 3
power: 3000
races: [ビートジョッキー, フレイム・モンスター, レクスターズ]
mana: 1
star: true
evolve_from: {any_of: [{race_has: レクスターズ}, {civs: [fire]}]}
keywords: [double_breaker]
text: スター進化 / パワーアタッカー+6000 / W・ブレイカー / このカードが離れた時、その下にあったクリーチャーをアンタップする。
abilities:
  - kind: static
    affects: self
    mod: {power_when: {amount: 6000, when: attacking}}
  - kind: trigger
    when: {event: move, from: bz, subject: self}
    effect:
      - {op: untap, select: {ref: event.under}}
source: {official: dmrp18-080, review: pending}
""")
    assert _leave_trigger(c)


def test_dmrp18_018():
    """ゴルドーザ ＜ドラギリア.Star＞: パワード・ブレイカー＋攻撃時誘発＋離脱時アンタップ。"""
    c = _parse("""
id: dmrp18-018
name: ゴルドーザ ＜ドラギリア.Star＞
types: [creature, evolution]
civs: [fire]
cost: 5
power: 7000
races: [ビートジョッキー, ティラノ・ドレイク, レクスターズ]
mana: 1
star: true
evolve_from: {any_of: [{race_has: レクスターズ}, {civs: [fire]}]}
keywords: [powered_breaker]
text: スター進化 / パワード・ブレイカー / 攻撃時誘発 / このカードが離れた時、下にあったクリーチャーをアンタップする。
abilities:
  - kind: trigger
    when: {event: attack, subject: self}
    effect:
      - op: may
        body:
          - {op: modify, select: {ref: self}, mod: {power: 7000}, duration: during_attack}
          - op: delayed_trigger
            when: {event: attack_end, subject: self}
            effect:
              - {op: destroy, select: {ref: self}}
  - kind: trigger
    when: {event: move, from: bz, subject: self}
    effect:
      - {op: untap, select: {ref: event.under}}
source: {official: dmrp18-018, review: pending, aliases: [dmrp18-coro07]}
""")
    assert _leave_trigger(c)
