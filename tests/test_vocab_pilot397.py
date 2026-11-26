"""語彙パイロット第397弾: mana_placed_count_this_turn（ドリフト）。

センサス（rejects 1,936件を取り直し）: pure 1,788件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜396弾）は再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021 と
battle_opponent_reference の残り1件 dmr01-049 は
先行弾の評価を覆す根拠が無く再提案しない。本弾で
個別に評価して見送った候補: destroyed_this_turn_
condition（pure 1、dm26ex2-mc012。第392〜396弾の次点
だが依然として最小ではない: 素行の呪文3条項＋手札
ゾーンのターン終了時無償詠唱の付与が未検証。次点と
して残す）、count_cards_drawn_this_turn（pure 1、
dm12-010。turn_count {kind: draw} は式としては既存
だが、本件は「相手が2枚以上引いたターンの終わりに
相手自身が手札をすべて捨てる」という相手ターン終了時
誘発＋相手の全手札破棄で、ターン終了時誘発の player
スコープと discard の all 形の組み合わせ検証が要り、
ord の登録先例がそのまま使える本弾より重い。次点と
して残す）、power_set（pure 2件、dm26rp3-or001 /
dm26rp3-sec001。同名カードの別刷り2件だが、条項は
power_set だけでなく「各ターン、相手のクリーチャーが
はじめて攻撃する時」の初回攻撃誘発と「パワーが
0以下の間離れない」の条件付き no_leave が同居する
複合で、本 gap 単独では最小にならない）、double_power
（pure 1、dmex19-m5。アバレチェーンのテキスト書き換え
条項が同居する）、static_double_power（pure 1、
dmrp19-008。バトル中のパワー2倍は battle_power の
倍率形が未検証で、本弾の ord 形より重い）、
each_player_mana_put（pure 1、dm24bd5-040。「マナに
置いた相手1人につき」の相手側実行数の数え上げが
未検証）、exclude_ref（pure 3件。アバレチェーン等の
複合）、fixed_breaks_plus_one（pure 1、dmrp07-052。
name・text・partial が無い素行で評価不能＝dmr01-049
と同じ扱い）。範囲内・最小の **mana_placed_count_
this_turn（pure 1件、multi にも現れない）** を選定した。

対象は pure 1件すべて: dmrp06-027 マ・スクメーロ・
タンク（自然のクリーチャー / コスト4 / パワー8000 /
種族 グランセクト）。partial は骨格完備で、構築済みは
keywords [double_breaker, enters_tapped] と static
{affects: self, mod: {deny: [untap_at_start]}}、
未解決は unsupported の mana_placed_count_this_turn
1件だけ。partial の text は行の公式テキスト全文と
一致するため**補完なし**。alias は無い（identity
実測で canon_id(dmrp06-027) = dmrp06-027、
aliases_for = []）。第397弾時点で real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも登録なし。
単面カードで未検証の面は無い。

条項「自分のマナゾーンにカードを置く時、それが
そのターンに自分のマナゾーンに置く最初のカードで
なければ、このクリーチャーをアンタップする」の
確立形は trigger 1件:

- trigger {when: {event: move, to: mana, subject:
  {owner: you}, ord: {kind: mana_put, ge: 2}},
  effect: [untap {select: {ref: self}}]}

登録先例 dm23rp2x-047（推出の超人。「各ターン2枚目の
カードを自分のマナゾーンに置いた時」）が同じ when
{event: move, to: mana, subject: {owner: you}} に
ord {kind: mana_put, eq: 2} を付けた形で登録されて
おり、本件は「最初のカードでなければ」＝2枚目以降
すべてが対象のため、ord の比較を ge: 2 に変えるだけ
のドリフト。ord は履歴基盤が move レコードへ刻む
そのターンでの通し番号（第3段・共通基盤その2a。
defs の ORD_KINDS に mana_put があり、比較は
eq/ge/gt/le/lt のいずれか1つ。test_vocab_hist_
counters の T238 が ord {kind: mana_put, ge: 2} の
実挙動〔チャージ＝1回目では発火せず、CIP の2回目・
3回目で発火〕を検証済み）。untap {select: {ref: self}}
は登録先例多数の素の op。ord / untap / deny は
defs と schema.py（生成済み card.schema.json）の
両側に定義済みを確認（第408ラウンドの教訓）。
partial の注記「そのターンにマナゾーンへ置いた
枚数を数える式が無い」は、ord 基盤（第159弾）の
実装より前の陳腐化だった。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (['double_breaker'], 条項テキスト,
[]) を返し、定型所有する abilities は空（part[2] = []）
のため merge_split が二重付与する対象は無い
（本弾で実測）。

proto T1164（dmrp06-027 型）。判別役は既存 proto を
流用: T002（CIP で自分の山札の上から1枚をマナゾーンに
置く＝2枚目以降のマナ置き役）/ T001（自然クリーチャー
＝マナ役・チャージ役）。

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

STATIC = {"kind": "static", "affects": "self",
          "mod": {"deny": ["untap_at_start"]}}
TRIGGER = {"kind": "trigger",
           "when": {"event": "move", "to": "mana",
                    "subject": {"owner": "you"},
                    "ord": {"kind": "mana_put", "ge": 2}},
           "effect": [{"op": "untap", "select": {"ref": "self"}}]}
FORM = [STATIC, TRIGGER]
FULL_TEXT = ("W・ブレイカー（このクリーチャーはシールドを２つブレイクする）\n"
             "このクリーチャーはタップしてバトルゾーンに置かれ、"
             "自分のターンのはじめにアンタップしない。\n"
             "自分のマナゾーンにカードを置く時、それがそのターンに"
             "自分のマナゾーンに置く最初のカードでなければ、"
             "このクリーチャーをアンタップする。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1164")
    assert c["name"] == "マ・スクメーロ・タンク"
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 4 and c["power"] == 8000 and c["mana"] == 1
    assert c["races"] == ["グランセクト"]
    assert c["keywords"] == ["double_breaker", "enters_tapped"]
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(copy.deepcopy(c), TABLES)
    assert TRIGGER in d.abilities
    assert STATIC in d.abilities
    for tid in ("T002", "T001"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX397", "name": "x",
                    "types": ["creature"], "civs": ["nature"],
                    "cost": 4, "power": 8000, "mana": 1,
                    "keywords": ["double_breaker", "enters_tapped"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert TRIGGER in d.abilities


def test_bad_forms_rejected(rules):
    # ord の kind は ORD_KINDS の列挙で検証され、
    # shield_put（turn_count にはあるが ord には無い）は DefError
    bad = copy.deepcopy(proto_card("T1164"))
    bad["abilities"][1]["when"]["ord"] = {"kind": "shield_put", "eq": 1}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # ord の比較は1つだけ（eq と ge の併記は DefError）
    bad2 = copy.deepcopy(proto_card("T1164"))
    bad2["abilities"][1]["when"]["ord"] = {"kind": "mana_put",
                                           "eq": 2, "ge": 2}
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)
    # ord の値は正の整数（0 は DefError）
    bad3 = copy.deepcopy(proto_card("T1164"))
    bad3["abilities"][1]["when"]["ord"] = {"kind": "mana_put", "ge": 0}
    with pytest.raises(DefError):
        parse_card(bad3, TABLES)
    # 未知のイベント名は DefError
    bad4 = copy.deepcopy(proto_card("T1164"))
    bad4["abilities"][1]["when"] = {"event": "mana_placed",
                                    "subject": {"owner": "you"}}
    with pytest.raises(DefError):
        parse_card(bad4, TABLES)


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


def _mine(e, defn="T1164"):
    return next(c for c in e.zlist("bz", 0)
                if e.s.cards[c].defn == defn)


def _drive(e, script, max_steps=6000):
    """script(e, d, state) が True を返したらその判断を
    処理済みとして次へ進む。state['done'] が立ったら終了。"""
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


def test_first_put_does_not_untap_second_does(rules):
    # 実フロー: 召喚するとタップして出て（enters_tapped）、
    # 次の自分のターンのはじめにもアンタップしない
    # （deny untap_at_start）。そのターンのチャージ
    # （1枚目のマナ置き＝ord 1）ではアンタップせず、
    # T002 の CIP（2枚目＝ord 2）でアンタップする。
    # あわせて、カウンタがターン開始にリセットされること
    # （前ターンの置きを引き継げばチャージが ord 2 に
    # なって発火してしまう）もチャージ時点の不発で判別する
    e = _build(rules,
               {"hand": ["T1164", "T002", "T002"],
                "mana": ["T001"] * 6},
               {"bz": []})
    cid_box = {}

    def script(e, d, st):
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and not st.get("summoned"):
            assert "play:T1164" in keys, keys
            st["summoned"] = True
            e.answer([keys.index("play:T1164")])
            return True
        if st.get("summoned") and not st.get("entered"):
            st["entered"] = True
            cid_box["cid"] = _mine(e)
            # タップして出る（enters_tapped）
            assert e.s.cards[cid_box["cid"]].tapped is True
            return False
        if d["kind"] == "charge" and d.get("player") == 0 \
                and st.get("entered") and not st.get("charged2"):
            # 自分の2ターン目のはじめ: アンタップステップを
            # 過ぎてもタンクはタップしたまま（deny の判別）
            assert e.s.cards[cid_box["cid"]].tapped is True
            st["charged2"] = True
            charges = [k for k in keys if k.startswith("charge:")]
            assert charges, keys
            e.answer([keys.index(charges[0])])
            return True
        if d["kind"] == "main" and d.get("player") == 0 \
                and st.get("charged2") and not st.get("played2"):
            # チャージ直後の main: 1枚目（ord 1）では
            # 発火していないことを確認してから T002 を出す
            assert e.s.turn_counters.get("hist:mana_put:0") == 1
            assert e.s.cards[cid_box["cid"]].tapped is True
            assert "play:T002" in keys, keys
            st["played2"] = True
            e.answer([keys.index("play:T002")])
            return True
        if st.get("played2") and not st.get("after_cip"):
            if d["kind"] in ("main", "attack"):
                st["after_cip"] = True
                # 2枚目（ord 2）で発火してアンタップする
                assert e.s.turn_counters.get("hist:mana_put:0") == 2
                assert e.s.cards[cid_box["cid"]].tapped is False
                st["done"] = True
                return True
            return False
        return False

    _drive(e, script)


def test_third_put_also_untaps_ge_not_eq(rules):
    # ge: 2 の判別: 3枚目のマナ置きでも発火する
    # （登録先例 dm23rp2x-047 の eq: 2 では発火しない）。
    # 2枚目でアンタップした後にタップ状態へ戻し
    # （状態ポークで分離）、3枚目の CIP で再び
    # アンタップすることを見る
    e = _build(rules,
               {"hand": ["T1164", "T002", "T002"],
                "mana": ["T001"] * 6},
               {"bz": []})
    cid_box = {}

    def script(e, d, st):
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and not st.get("summoned"):
            st["summoned"] = True
            e.answer([keys.index("play:T1164")])
            return True
        if st.get("summoned") and not st.get("entered"):
            st["entered"] = True
            cid_box["cid"] = _mine(e)
            return False
        if d["kind"] == "charge" and d.get("player") == 0 \
                and st.get("entered") and not st.get("charged2"):
            st["charged2"] = True
            charges = [k for k in keys if k.startswith("charge:")]
            e.answer([keys.index(charges[0])])
            return True
        if d["kind"] == "main" and d.get("player") == 0 \
                and st.get("charged2") and not st.get("played1"):
            st["played1"] = True
            e.answer([keys.index("play:T002")])
            return True
        if d["kind"] == "main" and d.get("player") == 0 \
                and st.get("played1") and not st.get("played2"):
            # 2枚目の CIP でアンタップしていることを確認し、
            # 3枚目の判別のためタップ状態へ戻してから
            # 2体目の T002 を出す
            assert e.s.cards[cid_box["cid"]].tapped is False
            e.s.cards[cid_box["cid"]].tapped = True
            assert "play:T002" in keys, keys
            st["played2"] = True
            e.answer([keys.index("play:T002")])
            return True
        if st.get("played2") and not st.get("after3"):
            if d["kind"] in ("main", "attack"):
                st["after3"] = True
                # 3枚目（ord 3）でも発火する（ge の判別）
                assert e.s.turn_counters.get("hist:mana_put:0") == 3
                assert e.s.cards[cid_box["cid"]].tapped is False
                st["done"] = True
                return True
            return False
        return False

    _drive(e, script)


def test_opponent_mana_put_does_not_untap(rules):
    # owner の判別: 相手が自分のマナゾーンに2枚置いても
    # （相手の ord 2）自分のタンクはアンタップしない
    e = _build(rules,
               {"bz": ["T1164"]},
               {"hand": ["T002", "T002"], "mana": ["T001"] * 4})
    cid = _mine(e)
    e.s.cards[cid].tapped = True   # タップ状態にして観測する

    def script(e, d, st):
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 1 \
                and not st.get("opp_charged"):
            st["opp_charged"] = True
            charges = [k for k in keys if k.startswith("charge:")]
            assert charges, keys
            e.answer([keys.index(charges[0])])
            return True
        if d["kind"] == "main" and d.get("player") == 1 \
                and st.get("opp_charged") and not st.get("opp_played"):
            assert "play:T002" in keys, keys
            st["opp_played"] = True
            e.answer([keys.index("play:T002")])
            return True
        if st.get("opp_played") and not st.get("checked"):
            if d["kind"] in ("main", "attack"):
                st["checked"] = True
                # 相手は2枚置いた（相手のカウンタは2）が、
                # 自分のカウンタは0で、タンクはタップしたまま
                assert e.s.turn_counters.get("hist:mana_put:1") == 2
                assert not e.s.turn_counters.get("hist:mana_put:0")
                assert e.s.cards[cid].tapped is True
                st["done"] = True
                return True
            return False
        return False

    _drive(e, script)
