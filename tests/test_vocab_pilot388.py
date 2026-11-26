"""語彙パイロット第388弾: battle_opponent_reference（ドリフト）。

対象は pure 2件のうち単一条項の1件:
dm24rp4-065 カンテ＝ランタン（闇 / コスト2 / パワー1000 /
アビスロイヤル）。公式テキストは単一条項:
「このクリーチャーがバトルする時、そのバトルの終わりまで、
バトルしている相手クリーチャーのパワーを－3000する。
（パワー０以下のクリーチャーは破壊される）」

既存部品の確認（すべて確立済みで、新規語彙・エンジン・
defs・スキーマ変更なし）:
- 「バトルする時」は第75弾の battle_start 両面誘発で表す:
  攻撃側は when {event: battle_start, subject: self}、
  守備側は when {event: battle_start, opponent: self}。
  バトル相手は攻撃側では ref: event.opponent、守備側では
  ref: event.subject（登録先例 dmr01-020 ほか多数）。
- 「そのバトルの終わりまで、バトルしている相手の
  パワーを－Nする」は登録先例 dm26rp1-039（我竜塔最高層
  ローズ・キャッスル、第176弾）の形そのもの:
  modify {select: {ref: event.opponent / event.subject},
  mod: {power: -4000}, duration: during_attack}。
  本カードは発生源が自身のため subject / opponent を
  self に絞り、数値を -3000 にするだけの完全なドリフト。
- partial の注記「バトル相手を参照する語彙が無い」は
  第75・176弾の実装より前の陳腐化だった。
- modify / duration: during_attack / ref: event.opponent は
  defs の検証と schema.py の両方に定義済みであることを
  第408ラウンドの教訓どおり確認済み（スキーマ再生成不要・
  Rust ミラー不要・rust_stamp への影響なし）。

確立形: abilities = [攻撃側 trigger, 守備側 trigger] の2件。

partial は骨格のみ（クリーチャー / 闇 / コスト2 /
パワー1000 / 種族 アビスロイヤル、mana 1、keywords・
abilities ともに無し）と unsupported の
battle_opponent_reference 1件だけ。text は条項の断片
（「バトルしている相手クリーチャーのパワーを－3000する」）
のため、提出形では text に行の公式テキスト全文を入れる
（補完あり。ラウンド423への注意に明記）。alias は無い。
単面カードで未検証の面は無い。

ファミリーのもう1件 dmr01-049 は本弾の対象外: 行に
partial が無く（name・partial 欠落の data_incomplete 類）、
条項も「自分のバトル中、バトルしている相手クリーチャーは
破壊されない」という相手スコープのバトル破壊不能で形が
異なるため、battle_opponent_reference はラウンド423では
解消しない（1件残る）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い（第388弾で実測）。

proto: T1152（dm24rp4-065 型）。判別役は新規フィクスチャ
T1153（パワー3500ブロッカー: 素ではカンテが負け、-3000 で
500 になって勝つ）と既存 proto T1126（パワー8000
ブロッカー: -3000 でも 5000 で勝てず、バトル後にパワーが
8000 に戻る＝duration の判別）/ T1140（パワー4000
ブロッカー: -3000 で 1000 になり相打ちになる判別）。

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
    {"kind": "trigger",
     "when": {"event": "battle_start", "subject": "self"},
     "effect": [{"op": "modify", "select": {"ref": "event.opponent"},
                 "mod": {"power": -3000}, "duration": "during_attack"}]},
    {"kind": "trigger",
     "when": {"event": "battle_start", "opponent": "self"},
     "effect": [{"op": "modify", "select": {"ref": "event.subject"},
                 "mod": {"power": -3000}, "duration": "during_attack"}]},
]
FULL_TEXT = ("このクリーチャーがバトルする時、そのバトルの終わりまで、"
             "バトルしている相手クリーチャーのパワーを－3000する。"
             "（パワー０以下のクリーチャーは破壊される）")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1152")
    assert c["name"] == "カンテ＝ランタン"
    assert c["types"] == ["creature"] and c["civs"] == ["darkness"]
    assert c["cost"] == 2 and c["power"] == 1000 and c["mana"] == 1
    assert c["races"] == ["アビスロイヤル"]
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 2
    trigs = [a for a in d.abilities if a["kind"] == "trigger"]
    assert trigs[0]["when"] == {"event": "battle_start", "subject": "self"}
    assert trigs[1]["when"] == {"event": "battle_start", "opponent": "self"}


def test_fixture_form(rules):
    c = proto_card("T1153")
    assert c["types"] == ["creature"] and c["power"] == 3500
    assert c["keywords"] == ["blocker"]
    parse_card(c, TABLES)


def test_bad_forms_rejected(rules):
    base = copy.deepcopy(proto_card("T1152"))
    # 未知の duration は DefError
    bad = copy.deepcopy(base)
    bad["abilities"][0]["effect"][0]["duration"] = "during_battle"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # 未知の mod キーは DefError
    bad2 = copy.deepcopy(base)
    bad2["abilities"][0]["effect"][0]["mod"] = {"power": -3000, "speed": 1}
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)
    # 未知のイベント名は DefError
    bad3 = copy.deepcopy(base)
    bad3["abilities"][0]["when"] = {"event": "battle_began", "subject": "self"}
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


def test_attacking_side_wins_against_3500(rules):
    # 攻撃側: カンテ（1000）がプレイヤーを攻撃し、パワー3500
    # ブロッカーにブロックされる。-3000 で相手は 500 になり
    # カンテが勝つ（修整が無ければカンテが負ける判別）。
    e = _build(rules, {"bz": ["T1152"]}, {"bz": ["T1153"]})
    kante = _cid(e, 0, "T1152")
    wall = _cid(e, 1, "T1153")
    ok = _drive_battle(
        e, "attack:T1152:player", block_defn="T1153",
        done=lambda: e.s.cards[wall].zone == "graveyard")
    assert ok, "バトル相手への -3000 が効かず、3500ブロッカーを破壊できなかった"
    assert e.s.cards[wall].zone == "graveyard"
    assert e.s.cards[kante].zone == "bz"


def test_attacking_side_tie_against_4000(rules):
    # パワー4000ブロッカーは -3000 で 1000 になり相打ち
    # （修整が無ければブロッカーだけが残る判別）。
    e = _build(rules, {"bz": ["T1152"]}, {"bz": ["T1140"]})
    kante = _cid(e, 0, "T1152")
    wall = _cid(e, 1, "T1140")
    ok = _drive_battle(
        e, "attack:T1152:player", block_defn="T1140",
        done=lambda: e.s.cards[wall].zone == "graveyard")
    assert ok, "パワー4000ブロッカーが -3000 で相打ちにならなかった"
    assert e.s.cards[wall].zone == "graveyard"
    assert e.s.cards[kante].zone == "graveyard"


def test_reduction_expires_after_battle(rules):
    # パワー8000ブロッカーは -3000 でも 5000 でカンテが負ける。
    # バトル終了後は修整が切れてパワーは 8000 に戻る
    # （duration: during_attack の判別）。
    e = _build(rules, {"bz": ["T1152"]}, {"bz": ["T1126"]})
    kante = _cid(e, 0, "T1152")
    wall = _cid(e, 1, "T1126")
    ok = _drive_battle(
        e, "attack:T1152:player", block_defn="T1126",
        done=lambda: e.s.cards[kante].zone == "graveyard")
    assert ok, "パワー8000ブロッカーにカンテが負けなかった"
    assert e.s.cards[wall].zone == "bz"
    assert e.chars_ro(wall)["power"] == 8000, "バトル後に -3000 が残っている"


def test_defending_side_wins_against_3500(rules):
    # 守備側: タップしたカンテがパワー3500に攻撃される。
    # opponent: self の誘発で攻撃側は 500 になりカンテが勝つ
    # （修整が無ければカンテが負ける判別）。
    e = _build(rules, {"bz": ["T1153"]}, {"bz": ["T1152"]})
    atk = _cid(e, 0, "T1153")
    kante = _cid(e, 1, "T1152")
    e.s.cards[kante].tapped = True
    ok = _drive_battle(
        e, "attack:T1153:T1152", block_defn=None,
        done=lambda: e.s.cards[atk].zone == "graveyard")
    assert ok, "守備側の -3000 が効かず、3500のアタッカーを破壊できなかった"
    assert e.s.cards[atk].zone == "graveyard"
    assert e.s.cards[kante].zone == "bz"


def test_no_battle_no_reduction(rules):
    # 対照: ブロックされなければバトル自体が起きず、誘発も
    # 修整も無いままシールドを1枚ブレイクする。
    e = _build(rules, {"bz": ["T1152"]}, {"bz": ["T1153"]})
    kante = _cid(e, 0, "T1152")
    wall = _cid(e, 1, "T1153")
    sh0 = len(e.zlist("shield", 1))
    ok = _drive_battle(
        e, "attack:T1152:player", block_defn=None,
        done=lambda: len(e.zlist("shield", 1)) == sh0 - 1)
    assert ok, "ブロックなしでシールドをブレイクできなかった"
    assert e.s.cards[wall].zone == "bz"
    assert e.chars_ro(wall)["power"] == 3500
    assert e.s.cards[kante].zone == "bz"
