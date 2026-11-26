"""語彙パイロット第422弾: block_event_target（ドリフト）。

対象は dmrp12-046 凶鬼79号 ジュージュ（闇 / コスト6 /
パワー2000 / 種族 マフィ・ギャング）。公式テキスト:
「S・トリガー（このクリーチャーをシールドゾーンから
手札に加える時、コストを支払わずにすぐ召喚してもよい）
ブロッカー（このクリーチャーをタップして、相手
クリーチャーの攻撃先をこのクリーチャーに変更してもよい）
このクリーチャーがブロックした時、このターン、その
相手クリーチャーのパワーを－9000する。（パワー０以下の
クリーチャーは破壊される）
このターンの終わりに、このクリーチャーがタップして
いたら、破壊する。」

行の注記は「ブロック対象への効果を表す語彙が無い」で、
第359弾では「-9000 の継続付与とターン終わり自己破壊が
併記され重い」、第387弾では「partial が stub で複数
条項が未構築」として見送られたが、その後の弾で両条項の
確立形が揃ったため再評価した（第410・411・418・420弾と
同じ覆し型。新規語彙・エンジン・defs・スキーマ変更なし）:
- 第3条項は第401弾の trigger {when: {event: block,
  subject: self}}（block レコードの subject はブロッカー、
  combat.py で確認）に、第388弾の modify の event 参照を
  組み合わせた形。対象の参照は event.opponent では
  なく event.attacker: block レコードは opponent キーを
  持たず（attacker に攻撃クリーチャーが入る）、登録済み
  dmr16g-015 が「ブロックされた時」の対象を
  ref event.attacker で登録済み。本弾の初回プローブで
  event.opponent では modify が空転して通常バトルに
  なることを実測し、event.attacker に差し替えた。
  duration は文面「このターン」どおり end_of_turn。
- 第4条項は登録済み dmrp15-069 の登録形そのもの:
  trigger {when: {event: turn_end}, if: {exists:
  {ref: self, filter: {tapped: true}}}, effect:
  [destroy {select: {ref: self}}]}（本件は同カードの
  鬼タイム条件が無い分だけ単純）。
- S・トリガー／ブロッカーは partial に keywords
  [s_trigger, blocker] として構築済み。

partial は骨格＋keywords まで構築済みで text は公式全文
（補完なし）。alias は無し（identity 実測で canon_id は
対象自身、aliases_for = []）。登録ブロッカーの確認
（第375弾の教訓）: rule_convert.split（対象行）は
(['s_trigger', 'blocker'], 条項テキスト, []) を返し、
定型所有はキーワードのみで part[2] の能力所有は空
＝二重付着ブロッカー無し。

proto: T1195（dmrp12-046 型）＋ T1196（パワー5000:
-9000 で 0 以下になり破壊される判別役）＋ T1197
（パワー12000: -9000 でも 3000 で残り、ターン終了後に
12000 に戻る判別役）＋ T1198（パワー10000: -9000 で
1000 になりバトルに負けるため、ブロッカーがタップした
まま生き残る判別役）。既存 proto の流用: T1126
（パワー8000ブロッカー＝第3条項の不発判別役）/ T001
（パワー2000バニラ＝第4条項の対照役）。

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
     "when": {"event": "block", "subject": "self"},
     "effect": [{"op": "modify", "select": {"ref": "event.attacker"},
                 "mod": {"power": -9000}, "duration": "end_of_turn"}]},
    {"kind": "trigger",
     "when": {"event": "turn_end"},
     "if": {"exists": {"ref": "self", "filter": {"tapped": True}}},
     "effect": [{"op": "destroy", "select": {"ref": "self"}}]},
]
PARSED_FORM = [
    FORM[0],
    {"kind": "trigger",
     "when": {"event": "turn_end"},
     "if": {"exists": {"ref": "self", "filter": {"tapped": True}}},
     "effect": [{"op": "move", "select": {"ref": "self"},
                 "to": "graveyard", "reason": "destroy"}]},
]
FULL_TEXT = ("S・トリガー（このクリーチャーをシールドゾーンから"
             "手札に加える時、コストを支払わずにすぐ召喚してもよい）\n"
             "ブロッカー（このクリーチャーをタップして、相手"
             "クリーチャーの攻撃先をこのクリーチャーに変更してもよい）\n"
             "このクリーチャーがブロックした時、このターン、その"
             "相手クリーチャーのパワーを－9000する。（パワー０以下の"
             "クリーチャーは破壊される）\n"
             "このターンの終わりに、このクリーチャーがタップしていたら、"
             "破壊する。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1195")
    assert c["name"] == "凶鬼79号 ジュージュ"
    assert c["types"] == ["creature"] and c["civs"] == ["darkness"]
    assert c["cost"] == 6 and c["power"] == 2000 and c["mana"] == 1
    assert c["races"] == ["マフィ・ギャング"]
    assert c["keywords"] == ["s_trigger", "blocker"]
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(copy.deepcopy(c), TABLES)
    assert FORM[0] in d.abilities
    # destroy は parse で move（to: graveyard, reason: destroy）に
    # 正規化される
    assert PARSED_FORM[1] in d.abilities
    for tid in ("T1196", "T1197", "T1198", "T1126", "T001"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX422", "name": "x",
                    "types": ["creature"], "civs": ["darkness"],
                    "cost": 6, "power": 2000, "mana": 1,
                    "races": ["マフィ・ギャング"],
                    "keywords": ["s_trigger", "blocker"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert FORM[0] in d.abilities
    assert PARSED_FORM[1] in d.abilities


def test_bad_forms_rejected(rules):
    base = proto_card("T1195")
    # when の未知イベントは DefError
    bad = copy.deepcopy(base)
    bad["abilities"][0]["when"] = {"event": "blocked", "subject": "self"}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # 未知の duration は DefError
    bad2 = copy.deepcopy(base)
    bad2["abilities"][0]["effect"][0]["duration"] = "during_battle"
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)
    # mod の未知キーは DefError
    bad3 = copy.deepcopy(base)
    bad3["abilities"][0]["effect"][0]["mod"] = {"power": -9000, "speed": 1}
    with pytest.raises(DefError):
        parse_card(bad3, TABLES)
    # if 内フィルタの未知キーは DefError
    bad4 = copy.deepcopy(base)
    bad4["abilities"][1]["if"] = {
        "exists": {"ref": "self", "filter": {"tapped": True, "bogus": 1}}}
    with pytest.raises(DefError):
        parse_card(bad4, TABLES)
    # effect の未知 op は DefError
    bad5 = copy.deepcopy(base)
    bad5["abilities"][1]["effect"] = [{"op": "destroyy",
                                       "select": {"ref": "self"}}]
    with pytest.raises(DefError):
        parse_card(bad5, TABLES)


# ---------- 駆動ヘルパ ----------

def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "pay_mana":
        e.answer([0])
    elif d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn):
    return next(c for c in e.zlist("bz", p)
                if e.s.cards[c].defn == defn)


def _drive(e, attacker=None, blocker=None, stop=None, limit=600):
    """attacker（攻撃キー）を一度だけ攻撃させ、blocker
    （proto id）がいればブロックさせる。stop(e) が真に
    なるまで進める。"""
    st = {"attacked": False}
    for _ in range(limit):
        if stop and stop():
            return st
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if attacker and not st["attacked"] and d["kind"] == "attack" \
                and attacker in keys:
            e.answer([keys.index(attacker)])
            st["attacked"] = True
            continue
        if d["kind"] == "block" and blocker:
            hit = [i for i, k in enumerate(keys)
                   if k.startswith(f"bz:{blocker}")]
            if hit:
                e.answer([hit[0]])
                continue
        _answer_default(e, d)
    return st


def test_block_destroys_5000_attacker(rules):
    # 第3条項: パワー5000のアタッカーをブロックすると
    # -9000 でパワー0以下になり破壊される（修整が無ければ
    # パワー2000のブロッカーがバトルで負ける判別）。
    e = _build(rules, {"bz": ["T1195"]}, {"bz": ["T1196"]})
    atk = _cid(e, 1, "T1196")
    st = _drive(e, attacker="attack:T1196:player", blocker="T1195",
                stop=lambda: e.s.cards[atk].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[atk].zone == "graveyard"


def test_block_reduces_12000_and_restores(rules):
    # 第3条項の対象と duration: パワー12000のアタッカーは
    # -9000 で 3000 になりバトルに勝ち（ブロッカーは
    # 破壊される）、同じターンの間は 3000 のまま。
    # ブロックしていない相手の獣（T001）は修整を受けない。
    # ターンが終われば 12000 に戻る（end_of_turn の判別）。
    e = _build(rules, {"bz": ["T1195"]}, {"bz": ["T1197", "T001"]})
    atk = _cid(e, 1, "T1197")
    blk = _cid(e, 0, "T1195")
    other = _cid(e, 1, "T001")
    st = _drive(e, attacker="attack:T1197:player", blocker="T1195",
                stop=lambda: e.s.cards[blk].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[atk].zone == "bz"
    assert e.chars_ro(atk)["power"] == 3000
    assert e.chars_ro(other)["power"] == 2000
    # 次の自分の攻撃ステップまで進めると修整は切れている
    seen = {"n": 0}
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if d["kind"] == "attack" and d.get("player") == 1:
            seen["n"] += 1
            if seen["n"] >= 1:
                break
        _answer_default(e, d)
    assert e.chars_ro(atk)["power"] == 12000


def test_block_10000_attacker_loses_and_blocker_destroyed_at_turn_end(rules):
    # 第3+4条項の合成判別: パワー10000のアタッカーは
    # -9000 で 1000 になりバトルに負けるため、ブロッカーは
    # タップしたまま生き残る。第4条項が無ければブロッカーは
    # 場に残るはずだが、ターンの終わりに破壊される。
    e = _build(rules, {"bz": ["T1195"]}, {"bz": ["T1198"]})
    atk = _cid(e, 1, "T1198")
    blk = _cid(e, 0, "T1195")
    st = _drive(e, attacker="attack:T1198:player", blocker="T1195",
                stop=lambda: e.s.cards[atk].zone == "graveyard"
                and e.s.cards[blk].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[atk].zone == "graveyard"
    assert e.s.cards[blk].zone == "graveyard"


def test_clause4_attacking_unblocked_destroyed_at_turn_end(rules):
    # 第4条項の単独判別（ブロックを介さない）: プレイヤーを
    # 攻撃してタップした発生源は、自分のターンの終わりに
    # 破壊される。
    e = _build(rules, {"bz": ["T1195"]}, {"bz": []})
    src = _cid(e, 0, "T1195")
    st = _drive(e, attacker="attack:T1195:player",
                stop=lambda: e.s.cards[src].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[src].zone == "graveyard"


def test_clause4_control_vanilla_survives(rules):
    # 対照: 第4条項を持たないバニラは、攻撃してタップしても
    # ターンの終わりに破壊されない。
    e = _build(rules, {"bz": []}, {"bz": ["T001"]})
    atk = _cid(e, 1, "T001")
    seen = {"n": 0}
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 1:
            seen["n"] += 1
            if seen["n"] == 1 and "attack:T001:player" in keys:
                e.answer([keys.index("attack:T001:player")])
                continue
            if seen["n"] >= 2:
                break
        _answer_default(e, d)
    assert seen["n"] >= 2
    assert e.s.cards[atk].zone == "bz"


def test_clause4_untapped_survives(rules):
    # 対照: 発生源がタップしていなければ、ターンの終わりを
    # 2回跨いでも破壊されない（if の tapped 判別）。
    e = _build(rules, {"bz": ["T1195"]}, {"bz": []})
    src = _cid(e, 0, "T1195")
    seen = {"n": 0}
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if d["kind"] == "attack" and d.get("player") == 0:
            seen["n"] += 1
            if seen["n"] >= 2:
                break
        _answer_default(e, d)
    assert seen["n"] >= 2
    assert e.s.cards[src].zone == "bz"
    assert not e.s.cards[src].tapped


def test_no_reduction_when_attacking(rules):
    # 第3条項の不発判別: 発生源が攻撃側の時は発火しない。
    # パワー8000ブロッカーにブロックされても修整は無く、
    # 発生源は素のパワー2000でバトルに負ける。
    e = _build(rules, {"bz": ["T1195"]}, {"bz": ["T1126"]})
    src = _cid(e, 0, "T1195")
    wall = _cid(e, 1, "T1126")
    st = _drive(e, attacker="attack:T1195:player", blocker="T1126",
                stop=lambda: e.s.cards[src].zone == "graveyard")
    assert st["attacked"]
    assert e.s.cards[src].zone == "graveyard"
    assert e.s.cards[wall].zone == "bz"
    assert e.chars_ro(wall)["power"] == 8000
