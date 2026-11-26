"""語彙パイロット第391弾: battle_duration（ドリフト）。

対象は pure 1件すべて: dmd15-005 ギャノバズガ・ドラゴン
（火 / コスト5 / パワー4000 / アーマード・ドラゴン）。
公式テキストは単一条項:
「自分の火のクリーチャーがバトルする時、そのバトルの
終わりまで、そのクリーチャーのパワーは+3000される。」

既存部品の確認（すべて確立済みで、新規語彙・エンジン・
defs・スキーマ変更なし）:
- 「バトルする時、そのバトルの終わりまで、パワーは
  +Nされる」は mod **battle_power**（第122弾）そのもの:
  defs の定義どおり「バトル中だけのパワー修整」で、
  duration の概念は mod 自体に組み込まれている。
  partial の注記「バトル中のみの効果を表す語彙が無い」は
  この mod より前の陳腐化だった。
- 他者への付与形は登録先例が同型で2件ある:
  dmrp15-040（static {affects: {owner: you, zone: bz,
  filter: {types: [creature]}}, mod: {battle_power:
  {amount: 2000}}}。「自分のクリーチャーすべての、
  バトル中のパワーを+2000する」）と dmr17-054（同形に
  civs: [nature] フィルタと if 条件。本弾の対象は
  civs: [fire] フィルタ・条件なし）。only: attacking を
  付けないため攻撃側・守備側の両方で効く（テキストは
  「バトルする時」で攻撃に限定されない）。
- battle_power の他者付与は第342弾で combat.
  _battle_bonus の付与経路（bz 発生源の affects 辞書形を
  集約）が実装済みで、発生源自身も affects に合えば
  自分への付与を受ける（本弾で実挙動を固定: 発生源自身
  も「自分の火のクリーチャー」に含まれる）。
- battle_power / affects の filter civs は defs の検証と
  schema.py の両方に定義済みであることを第408ラウンドの
  教訓どおり確認済み（スキーマ再生成不要・Rust ミラー
  不要・rust_stamp への影響なし）。

確立形: abilities = [static {affects: {zone: bz,
owner: you, filter: {types: [creature], civs: [fire]}},
mod: {battle_power: {amount: 3000}}}] の1件。

partial は骨格のみ（クリーチャー / 火 / コスト5 /
パワー4000 / 種族 アーマード・ドラゴン、mana 1、
keywords 無し）と unsupported の battle_duration
1件だけ。text は条項の断片（「バトルする時、その
バトルの終わりまで」）のため、提出形では text に
行の公式テキスト全文を入れる（補完あり。ラウンド426
への注意に明記）。alias は無い。単面カードで
未検証の面は無い。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い
（第391弾で実測）。

proto: T1156（dmd15-005 型）。判別役は新規フィクスチャ
T1157（火・パワー2000: 素では4000ブロッカーに負け、
+3000 で 5000 になって勝つ）/ T1158（水・パワー2000:
火フィルタに合わず負ける）と既存 proto T1140
（火・パワー4000ブロッカー）/ T1155（光・パワー6000
ブロッカー: 発生源自身 4000 が +3000 で 7000 になって
勝つ判別）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

FORM = [
    {"kind": "static",
     "affects": {"zone": "bz", "owner": "you",
                 "filter": {"types": ["creature"], "civs": ["fire"]}},
     "mod": {"battle_power": {"amount": 3000}}},
]
FULL_TEXT = ("自分の火のクリーチャーがバトルする時、そのバトルの"
             "終わりまで、そのクリーチャーのパワーは+3000される。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1156")
    assert c["name"] == "ギャノバズガ・ドラゴン"
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 5 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["アーマード・ドラゴン"]
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 1
    assert d.abilities[0]["kind"] == "static"
    assert d.abilities[0]["mod"] == {"battle_power": {"amount": 3000}}


def test_fixture_forms(rules):
    f = proto_card("T1157")
    assert f["types"] == ["creature"] and f["civs"] == ["fire"]
    assert f["power"] == 2000 and not f.get("abilities")
    parse_card(f, TABLES)
    w = proto_card("T1158")
    assert w["types"] == ["creature"] and w["civs"] == ["water"]
    assert w["power"] == 2000 and not w.get("abilities")
    parse_card(w, TABLES)


def test_bad_forms_rejected(rules):
    base = copy.deepcopy(proto_card("T1156"))
    # battle_power の only は attacking のみ（blocking は DefError）
    bad = copy.deepcopy(base)
    bad["abilities"][0]["mod"]["battle_power"] = {
        "amount": 3000, "only": "blocking"}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # amount が無ければ DefError
    bad2 = copy.deepcopy(base)
    bad2["abilities"][0]["mod"]["battle_power"] = {}
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)
    # 未知の mod キーは DefError
    bad3 = copy.deepcopy(base)
    bad3["abilities"][0]["mod"] = {"battle_power": {"amount": 3000},
                                   "battle_powers": {"amount": 3000}}
    with pytest.raises(DefError):
        parse_card(bad3, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "yes_no":
        e.answer([keys.index("yes")] if "yes" in keys
                 else list(range(d["min"])))
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _cid(e, p, defn):
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn)


def _drive_battle(e, attack_key, block_defn=None, done=None, limit=400):
    """attack_key で攻撃し、block_defn があればブロックさせる。
    done() が真になるまで進める。"""
    for _ in range(limit):
        if done and done():
            return True
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if done and done():
            return True
        if d["kind"] == "attack" and attack_key in keys:
            e.answer([keys.index(attack_key)])
            continue
        if d["kind"] == "block":
            if block_defn:
                hit = [i for i, k in enumerate(keys)
                       if k.startswith(f"bz:{block_defn}")]
                if hit:
                    e.answer([hit[0]])
                    continue
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
                continue
        _answer_default(e, d)
    return done() if done else False


def test_grant_attacking_side(rules):
    # 攻撃側への付与: 自分の火獣（2000）がプレイヤーを攻撃し、
    # パワー4000ブロッカーにブロックされる。+3000 で 5000 に
    # なって勝つ（修整が無ければ 2000 で負ける判別）。
    e = _build(rules, {"bz": ["T1156", "T1157"]}, {"bz": ["T1140"]})
    src = _cid(e, 0, "T1156")
    beast = _cid(e, 0, "T1157")
    wall = _cid(e, 1, "T1140")
    ok = _drive_battle(
        e, "attack:T1157:player", block_defn="T1140",
        done=lambda: e.s.cards[wall].zone == "graveyard")
    assert ok, "火のクリーチャーへの battle_power +3000 が効かなかった"
    assert e.s.cards[wall].zone == "graveyard"
    assert e.s.cards[beast].zone == "bz"
    assert e.s.cards[src].zone == "bz"


def test_grant_defending_side_and_opponent_fire_gets_nothing(rules):
    # 守備側への付与＋相手の火は対象外: 相手の火（4000）が
    # タップした自分の火獣（2000）を攻撃する。守備側は
    # +3000 で 5000 になって勝ち、攻撃側の火は owner: you
    # （発生源から見て相手）のため +3000 を受けない
    # （受ければ 7000 で勝ってしまう二重の判別）。
    e = _build(rules, {"bz": ["T1140"]}, {"bz": ["T1156", "T1157"]})
    atk = _cid(e, 0, "T1140")
    beast = _cid(e, 1, "T1157")
    e.s.cards[beast].tapped = True
    ok = _drive_battle(
        e, "attack:T1140:T1157", block_defn=None,
        done=lambda: e.s.cards[atk].zone == "graveyard")
    assert ok, "守備側の火への +3000 が効かなかった／相手の火が +3000 を受けた"
    assert e.s.cards[atk].zone == "graveyard"
    assert e.s.cards[beast].zone == "bz"


def test_source_itself_battles(rules):
    # 発生源自身も「自分の火のクリーチャー」に含まれる:
    # ギャノバズガ自身（4000）がプレイヤーを攻撃し、
    # パワー6000ブロッカーにブロックされる。+3000 で
    # 7000 になって勝つ（自身が対象外なら 4000 で負ける判別）。
    e = _build(rules, {"bz": ["T1156"]}, {"bz": ["T1155"]})
    src = _cid(e, 0, "T1156")
    wall = _cid(e, 1, "T1155")
    ok = _drive_battle(
        e, "attack:T1156:player", block_defn="T1155",
        done=lambda: e.s.cards[wall].zone == "graveyard")
    assert ok, "発生源自身が battle_power +3000 を受けなかった"
    assert e.s.cards[wall].zone == "graveyard"
    assert e.s.cards[src].zone == "bz"


def test_non_fire_gets_nothing(rules):
    # 文明フィルタの判別: 自分の水獣（2000）は火ではないため
    # +3000 を受けず、パワー4000ブロッカーに負ける。
    e = _build(rules, {"bz": ["T1156", "T1158"]}, {"bz": ["T1140"]})
    beast = _cid(e, 0, "T1158")
    wall = _cid(e, 1, "T1140")
    ok = _drive_battle(
        e, "attack:T1158:player", block_defn="T1140",
        done=lambda: e.s.cards[beast].zone == "graveyard")
    assert ok, "水のクリーチャーが +3000 を受けてしまった"
    assert e.s.cards[beast].zone == "graveyard"
    assert e.s.cards[wall].zone == "bz"


def test_no_battle_no_bonus(rules):
    # 対照: バトルが無ければ修整は現れず、特性パワーは
    # 素のまま（火獣 2000 / 発生源 4000）。ブロックなしの
    # プレイヤー攻撃はシールドを1枚ブレイクする。
    e = _build(rules, {"bz": ["T1156", "T1157"]}, {"bz": []})
    src = _cid(e, 0, "T1156")
    beast = _cid(e, 0, "T1157")
    assert e.chars_ro(beast)["power"] == 2000
    assert e.chars_ro(src)["power"] == 4000
    sh0 = len(e.zlist("shield", 1))
    ok = _drive_battle(
        e, "attack:T1157:player", block_defn=None,
        done=lambda: len(e.zlist("shield", 1)) == sh0 - 1)
    assert ok, "ブロックなしでシールドをブレイクできなかった"
    assert e.s.cards[beast].zone == "bz"
    assert e.chars_ro(beast)["power"] == 2000
