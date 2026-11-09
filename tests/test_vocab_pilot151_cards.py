"""語彙パイロット第151弾（D2フィールド）: 代表7枚の手書き変換の形を固定する。

設計ノート pilot151-d2-field-design §3／§6 の変換形どおりに書いた YAML が
parse_card（検証込み）を通ることと、型印・Dスイッチ・禁止の形を固定する。
登録（submit）は行わない（実装と変換は分ける）。手変換は rejects の partial を土台にする。

- dm23ex3-042 の Dスイッチ効果「このターン破壊された自分のクリーチャーをすべて墓地から
  手札に戻す」は、「このターン破壊された」カードを墓地から選ぶセレクタが現行語彙に無いため
  unsupported に細分して残す（近似しない）。
- dmex08-204 ワチャゴナの「誰もD2フィールドをバトルゾーンに出せない」は、メインの generate
  より広い禁止（play_free 経路を含む）で、本弾の範囲外（親判断）。unsupported に細分して残す。
"""
import yaml
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()


def _parse(text):
    return parse_card(yaml.safe_load(text), TABLES)


def test_dmr21_036():
    """ユニバーサル・鮫・アンド・シー（A2）: 型印の併記＋常在型（ブロックされない）。"""
    c = _parse("""
id: dmr21-036
name: ユニバーサル・鮫・アンド・シー
types: [field, d2_field]
civs: [water]
cost: 2
mana: 1
text: 自分のクリーチャーはブロックされない。（他のD２フィールドがバトルゾーンに出た時、このD２フィールドを自分の墓地に置く）
abilities:
  - kind: static
    affects: {zone: bz, owner: you, filter: {types: [creature]}}
    mod: {deny: [be_blocked]}
source: {official: dmr21-036, review: pending}
""")
    assert c.face(None).types == ["field", "d2_field"]
    ab = c.abilities[0]
    assert ab["mod"] == {"deny": ["be_blocked"]}


def test_dmr21_047():
    """爆裂筋肉養成所（A2）: 型印の併記＋常在型（パワー修整）。"""
    c = _parse("""
id: dmr21-047
name: 爆裂筋肉養成所
types: [field, d2_field]
civs: [nature]
cost: 3
mana: 1
text: 自分のクリーチャーすべてのパワーを+3000する。（他のD２フィールドがバトルゾーンに出た時、このD２フィールドを自分の墓地に置く）
abilities:
  - kind: static
    affects: {zone: bz, owner: you, filter: {types: [creature]}}
    mod: {power: 3000}
source: {official: dmr21-047, review: pending}
""")
    assert c.face(None).types == ["field", "d2_field"]
    assert c.abilities[0]["mod"] == {"power": 3000}


def test_dm23ex3_042():
    """Dの魔城 ブリティッシュ・パビリオン（A1）: 常在型は書ける。Dスイッチ効果は
    「このターン破壊された」セレクタが無いため unsupported に細分して残す。"""
    c = _parse("""
id: dm23ex3-042
name: Dの魔城 ブリティッシュ・パビリオン
types: [field, d2_field]
civs: [darkness]
cost: 2
mana: 1
races: [ゼニス]
text: 自分のクリーチャーすべてに「スレイヤー」を与える。（他のD２フィールドが出た時、このD２フィールドを破壊する）Dスイッチ：自分のターンの終わりに、このD２フィールドをゲーム中で一度上下逆さまにしてもよい。そうしたら、このターン破壊された自分のクリーチャーをすべて、自分の墓地から手札に戻す。
abilities:
  - kind: static
    affects: {zone: bz, owner: you, filter: {types: [creature]}}
    mod: {grant: [slayer]}
source:
  official: dm23ex3-042
  review: pending
  unsupported:
    - {need: destroyed_this_turn_select, text: "Dスイッチ：自分のターンの終わりに、このD２フィールドをゲーム中で一度上下逆さまにしてもよい。そうしたら、このターン破壊された自分のクリーチャーをすべて、自分の墓地から手札に戻す。"}
""")
    assert c.face(None).types == ["field", "d2_field"]
    assert c.abilities[0]["mod"] == {"grant": ["slayer"]}


def test_dmd35_011():
    """ZEROの暴走 デッドリー・ハイウェイ（A1）: Dスイッチの型（dswitch: true＋may＋dswitch）を
    フルに書ける代表。侵略ZERO は本弾の対象外として unsupported に残す。"""
    c = _parse("""
id: dmd35-011
name: ZEROの暴走 デッドリー・ハイウェイ
types: [field, d2_field]
civs: [darkness]
cost: 4
mana: 1
text: 侵略ZERO：相手のターンの終わりに、そのターン相手がコストを支払わずにクリーチャーをバトルゾーンに出していたら、このD２フィールドを自分の手札からバトルゾーンに出してもよい。（他のD２フィールドがバトルゾーンに出た時、このD２フィールドを自分の墓地に置く）Dスイッチ：自分のターンのはじめに、このD２フィールドをゲーム中で一度上下逆さまにしてもよい。そうしたら、相手のタップしているクリーチャーを１体破壊する。
abilities:
  - kind: trigger
    dswitch: true
    when: {event: turn_start, player: you}
    effect:
      - op: may
        body:
          - {op: dswitch}
          - {op: destroy, select: {zone: bz, owner: opp, filter: {types: [creature], tapped: true}, count: 1}}
source:
  official: dmd35-011
  review: pending
  aliases: [dmr22-035, promoy15-036]
  unsupported:
    - {need: invasion_zero, text: "侵略ZERO：相手のターンの終わりに、そのターン相手がコストを支払わずにクリーチャーをバトルゾーンに出していたら、このD２フィールドを自分の手札からバトルゾーンに出してもよい。"}
""")
    assert c.face(None).types == ["field", "d2_field"]
    ab = c.abilities[0]
    assert ab["dswitch"] is True
    assert ab["effect"][0]["body"][0] == {"op": "dswitch"}
    second = ab["effect"][0]["body"][1]   # destroy はマクロで move（reason: destroy）に展開される
    assert second["op"] == "move" and second["to"] == "graveyard" and second["reason"] == "destroy"
    assert second["select"]["filter"] == {"types": ["creature"], "tapped": True}


def test_dmr21_035():
    """ワルスラS（B1）: G・ゼロの条件が {types: [d2_field]} の exists で書ける。"""
    c = _parse("""
id: dmr21-035
name: ワルスラS
types: [creature]
civs: [water]
cost: 3
power: 1000
mana: 1
races: [リキッド・ピープル閃, イニシャルズ]
free_if: {exists: {zone: bz, owner: you, filter: {types: [d2_field], civs: [water]}}}
text: G・ゼロ：バトルゾーンに自分の水のD２フィールドがあれば、このクリーチャーをコストを支払わずに召喚してもよい。
source: {official: dmr21-035, review: pending}
""")
    f = c.face(None)
    assert f.free_if == {"exists": {"zone": "bz", "owner": "you", "filter": {"types": ["d2_field"], "civs": ["water"]}}}


def test_dmr23_040():
    """ワールド・ストップ（B3）: 呪文の解決で duration つき禁止を置く形。
    「展開できない」はメインの generate まで（親判断）。"""
    c = _parse("""
id: dmr23-040
name: ワールド・ストップ
types: [spell]
civs: [light, water]
cost: 3
mana: 1
text: 次の自分のターンのはじめまで、相手はDスイッチを使えず、D２フィールドを展開できない。
spell:
  - op: modify
    select: {zone: hand, owner: opp, filter: {types: [d2_field]}}
    mod: {deny: [generate]}
    dynamic: true
    duration: until_next_own_turn_start
  - op: modify
    select: {zone: bz, owner: opp, filter: {types: [d2_field]}}
    mod: {deny: [d_switch]}
    dynamic: true
    duration: until_next_own_turn_start
source: {official: dmr23-040, review: pending}
""")
    ops = c.face(None).spell
    assert [o["mod"] for o in ops] == [{"deny": ["generate"]}, {"deny": ["d_switch"]}]
    assert all(o["dynamic"] is True and o["duration"] == "until_next_own_turn_start" for o in ops)


def test_dmex08_204():
    """族長の魂友 ワチャゴナ（B2）: 出た時の「D2フィールドをマナゾーンから出す」は
    {types: [d2_field]} の move で書ける。「誰も出せない」は本弾の範囲外（親判断）で
    unsupported に細分して残す。"""
    c = _parse("""
id: dmex08-204
name: 族長の魂友 ワチャゴナ
types: [creature]
civs: [light, nature]
cost: 8
power: 12500
mana: 1
races: [ガーディアン・コマンド・ドラゴン, マスター革命軍, ダママ団]
keywords: [triple_breaker]
text: T・ブレイカー。革命チェンジ：光または自然のコスト５以上のドラゴン。このクリーチャーがバトルゾーンに出た時、D２フィールドを１枚、自分のマナゾーンからバトルゾーンに出してもよい。自分のD２フィールドがバトルゾーンにある時、誰もD２フィールドをバトルゾーンに出せない。
abilities:
  - kind: declare
    zone: hand
    when: {event: attack, subject: {owner: you, filter: {civs: [light, nature], cost_ge: 5, race_has: ドラゴン}}}
    effect:
      - {op: swap, out: {ref: event.subject}, in: {ref: self}}
  - kind: trigger
    when: {event: move, to: bz, subject: self}
    effect:
      - op: may
        body:
          - {op: move, select: {zone: mana, owner: you, filter: {types: [d2_field]}, count: 1}, to: bz, reason: put}
source:
  official: dmex08-204
  review: pending
  aliases: [dmr22-s05]
  unsupported:
    - {need: d2_field_enter_ban_all_paths, text: "自分のD２フィールドがバトルゾーンにある時、誰もD２フィールドをバトルゾーンに出せない。"}
""")
    trig = next(a for a in c.abilities if a["kind"] == "trigger")
    move = trig["effect"][0]["body"][0]
    assert move["select"]["filter"] == {"types": ["d2_field"]}
    assert move["to"] == "bz"
