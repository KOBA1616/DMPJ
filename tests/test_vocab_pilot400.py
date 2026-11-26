"""語彙パイロット第400弾: untap_restriction（ドリフト）。

センサス（rejects 1,933件を取り直し）: pure 1,785件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜399弾）は再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021 と
battle_opponent_reference の残り1件 dmr01-049 は
先行弾の評価を覆す根拠が無く再提案しない。
destroyed_this_turn_condition と count_cards_drawn_
this_turn は次点のまま残す。本弾で個別に評価して
見送った候補: enters_tapped_rule（pure 1、
dmex11-005。第398・399弾の後続候補だが、スピード
アタッカー付与＋タップ入り付与2系統で静的効果3件と
なり本弾より重い。後続候補として残す）、
does_not_untap（pure 2件。dm22rp1-011 はタマシード
条件の攻撃制限とタマシード登場時アンタップが同居し
partial に能力が何も構築されていない。dm25ex2-031 は
シンパシー＋出た時すべて破壊が未構築で、本 gap 単独
では登録形が定まらない）、s_trigger_suppression
（pure 2件。dm28-025 は相手シールド4枚以上という
条件付きの shield deny で形は組めるが、条件の count
{zone: shield, owner: opp} の静的 if 評価が未検証で
本弾より重い。dm27-051 は「このクリーチャーが
ブレイクするシールド」限定で別形）。範囲内・最小の
**untap_restriction のうち dmrp21-t14 の1件** を選定
した（ファミリー pure 3件のうち残り2件は形が異なる
ため対象外とし、ファミリーは解消しない）。

対象は dmrp21-t14 ブルース・ガー（火のクリーチャー /
コスト1 / パワー1000 / 種族 ファイアー・バード /
K・ソウル）。partial は骨格のみで、text は断片
（「アンタップしない」）、keywords・abilities は
何も構築されておらず、未解決は unsupported の
untap_restriction 1件だけ。補完あり: races と text
のみ（【K・ソウル】は種族特性で、登録先例 dmex01-043 /
dm36-032 と同様に races へ 'K・ソウル' を入れて表す。
partial の races は [ファイアー・バード] のみ。
text には公式テキスト全文を入れる）。alias は
dm38-029 / dmrp21-tf14 の2件で、いずれも rejects に
独自行は無く、identity 実測で canon_id は対象・
全 alias とも dmrp21-t14。第400弾時点で real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも登録なし。
単面カードで未検証の面は無い。

条項「このクリーチャーは、自分のターンのはじめに
アンタップしない」の確立形は static 1件:

- static {affects: self, mod: {deny: [untap_at_start]}}

登録済み dmrp06-027（第397弾・ラウンド432）の partial
構築済み・登録形そのもので、登録先例 dmrp18-025 も
同形。エンジン側は turn.py のアンタップステップが
permits(c, "untap_at_start") を見る実装で、deny が
掛かったクリーチャーだけがターン開始時にタップした
ままになる。partial の注記「アンタップ制限を表す
語彙が無い」は、この deny 形の登録より前の陳腐化
だった。deny / untap_at_start は defs と schema.py
（生成済み card.schema.json）の両側に定義済みを
確認（第408ラウンドの教訓）。

ファミリーの残り2件が対象外の理由: dm26rp1-td004 の
条項は「相手のクリーチャーは、ターンのはじめ以外、
アンタップしない」＝効果によるアンタップの禁止で、
ターン開始ステップの deny とは別形。dmx15-011 の
条項は「誰も自身のマナゾーンにある呪文をアンタップ
できない」＝マナゾーンの呪文への全般的なアンタップ
禁止で別形。どちらも本弾の形では正確に表せないため
残置する。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い
（本弾で実測）。

proto T1167（dmrp21-t14 型）。判別役は既存 proto を
流用: T001（通常クリーチャー＝対照役・マナ役）/
T1090（火マナ役）。

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

FORM = [{"kind": "static", "affects": "self",
         "mod": {"deny": ["untap_at_start"]}}]
FULL_TEXT = ("【K・ソウル】\n"
             "このクリーチャーは、自分のターンのはじめにアンタップしない。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1167")
    assert c["name"] == "ブルース・ガー"
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 1 and c["power"] == 1000 and c["mana"] == 1
    assert c["races"] == ["ファイアー・バード", "K・ソウル"]
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(copy.deepcopy(c), TABLES)
    assert FORM[0] in d.abilities
    for tid in ("T001", "T1090"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX400", "name": "x",
                    "types": ["creature"], "civs": ["fire"],
                    "cost": 1, "power": 1000, "mana": 1,
                    "races": ["ファイアー・バード", "K・ソウル"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert FORM[0] in d.abilities


def test_bad_forms_rejected(rules):
    # 未知の deny アクションは DefError
    bad = copy.deepcopy(proto_card("T1167"))
    bad["abilities"][0]["mod"] = {"deny": ["untap_at_strt"]}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # 未知の mod キーは DefError
    bad2 = copy.deepcopy(proto_card("T1167"))
    bad2["abilities"][0]["mod"] = {"denyy": ["untap_at_start"]}
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "pay_mana":
        e.answer([0])
    elif d["kind"] == "choose_shields":
        e.answer(list(range(d["min"])))
    elif d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _mine(e, defn):
    return next(c for c in e.zlist("bz", 0)
                if e.s.cards[c].defn == defn)


def _drive(e, script, max_steps=6000):
    state = {}
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if script(e, d, state):
            if state.get("done"):
                return state
            continue
        _answer_default(e, d)
    raise AssertionError(f"script not finished: {state}")


def _attack_flow(e, defn, cid_box):
    """自ターン1: 召喚。自ターン2: 攻撃してタップし
    シールドを1枚ブレイク。自ターン3のはじめの状態を
    cid_box['at_turn3'] に記録する共通フロー。"""
    def script(e, d, st):
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 0:
            st["charges"] = st.get("charges", 0) + 1
            if st["charges"] == 3:
                # 自ターン3のはじめ: アンタップステップを
                # 過ぎた時点のタップ状態を記録
                cid_box["at_turn3"] = \
                    e.s.cards[cid_box["cid"]].tapped
                st["done"] = True
                return True
            return False
        if d["kind"] == "main" and d.get("player") == 0 \
                and not st.get("summoned"):
            key = f"play:{defn}"
            assert key in keys, keys
            st["summoned"] = True
            e.answer([keys.index(key)])
            return True
        if st.get("summoned") and "cid" not in cid_box:
            cid_box["cid"] = _mine(e, defn)
            return False
        if d["kind"] == "attack" and d.get("player") == 0 \
                and st.get("summoned") and not st.get("attacked"):
            hit = [k for k in keys
                   if k == f"attack:{defn}:player"]
            if hit:
                st["attacked"] = True
                cid_box["shields_before"] = len(e.zlist("shield", 1))
                e.answer([keys.index(hit[0])])
                return True
            return False
        if st.get("attacked") and not st.get("after_attack"):
            if d["kind"] in ("main", "charge", "attack"):
                st["after_attack"] = True
                # 攻撃でタップし、シールドが1枚減っている
                assert e.s.cards[cid_box["cid"]].tapped is True
                assert len(e.zlist("shield", 1)) \
                    == cid_box["shields_before"] - 1
                return True
            return False
        return False
    return script


def test_stays_tapped_at_own_turn_start(rules):
    # 実フロー: 召喚→次の自ターンに攻撃してタップ→
    # さらに次の自ターンのはじめにもアンタップしない
    e = _build(rules,
               {"hand": ["T1167"],
                "mana": ["T1090", "T001", "T001"]},
               {"bz": []})
    cid_box = {}
    _drive(e, _attack_flow(e, "T1167", cid_box))
    assert cid_box["at_turn3"] is True


def test_control_creature_untaps(rules):
    # 対照: deny を持たない通常クリーチャーは同じ
    # フローで自ターン3のはじめにアンタップしている
    e = _build(rules,
               {"hand": ["T001"],
                "mana": ["T001", "T001", "T001"]},
               {"bz": []})
    cid_box = {}
    _drive(e, _attack_flow(e, "T001", cid_box))
    assert cid_box["at_turn3"] is False


def test_permits_discrimination(rules):
    # 特性判別: deny は発生源自身の untap_at_start
    # だけに付き、同じバトルゾーンの他のクリーチャー
    # には付かない。攻撃の許可は奪わない
    e = _build(rules,
               {"bz": ["T1167", "T001"]},
               {"bz": []})
    cid = _mine(e, "T1167")
    other = _mine(e, "T001")
    assert e.permits(cid, "untap_at_start") is False
    assert e.permits(other, "untap_at_start") is True
    assert e.permits(cid, "attack_player") is True
    assert e.permits(cid, "attack_creature") is True
