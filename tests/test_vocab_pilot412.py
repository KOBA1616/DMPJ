"""語彙パイロット第412弾: turn_count_free（ドリフト）。

センサス（rejects 1,920件を取り直し）: pure 1,772件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜411弾）は原則として再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021、
battle_opponent_reference の残り1件 dmr01-049、
untap_restriction の残り2件（dm26rp1-td004 /
dmx15-011、形が異なると判定済み）、cast_limit_
once_per_turn の multi 2件（dm26ex2-pr006 /
dm26ex4-cho031、他の gaps を併せ持つ）、
summoning_attack_rule の残り1件 dmex07-s01
（partial が素で条項未構築）、entered_turn_attack の
残り1件 dmbd11-d05（J・O・E 等が未構築）、madness の
残り1件 dmx26-028（CIP が look/reorder 系の未確立
機構）は先行弾の評価を覆す根拠が無く再提案しない。
destroyed_this_turn_condition と count_cards_drawn_
this_turn は次点のまま残す。distinct_civ_count
（3条項の複合）は後続候補のまま残す。first_time_tap
（pure 2、第410弾で記録）は新規語彙候補として
残置のまま。
本弾で個別に評価して見送った候補（docs 未記載だった
pure 1件組）: opponents_must_attack_mystery_totems
（攻撃先の種族強制は新機構）、turn_attack_count
（2度目の攻撃の照合＋マナゾーンからの出場の複合）、
first_turn_attack_trigger（同一カード2行・他2条項も
未構築の複合）、battle_win_while_attacking
（battle_win 記録に攻撃側の区別が無い）、
destroyed_by_trigger（破壊者参照の他者誘発が未確立＋
第1条項も未構築）、require_attack_creature（素行＋
ハンティング複合）、untap_replacement（素行＋
アンタップ置換の新機構）、event_broken_cards_reference
（素行＋ブレイクしたシールド群への付与の複合）、
force_specific_block（指定ブロッカー強制の新機構）。
次点として新規に記録: battle_result_destruction
（dmx03-036。trigger {event: battle_win, subject:
self} → destroy {ref: self} の登録先例5件を確認。
敗北・相打ち時はバトル自体で破壊されるため挙動等価の
見込みが高く、次弾以降の選定候補）。

範囲内・最小の **turn_count_free（pure 1件、multi にも
現れない）** を選定した。行の注記は「ターンの行動回数を
条件にする語彙が無い」とするが、G・ゼロの条件フィールド
free_if には条件文法の turn_count 式がそのまま入り、
登録済み dmrp06-038 貝獣 ラリア（free_if {cmp:
[{turn_count: {kind: cast, owner: you}}, ">=", 2]}）と
dmpcd02-b18 魔光騎聖ブラッディ・シャドウ（同形で
">=", 1）が同文面系統の G・ゼロを登録済み。本件は
閾値が3になるだけで完全なドリフト。

対象は dmex19-028 超宮兵 マノミ（水のクリーチャー /
コスト5 / パワー4000 / 種族 ムートピア）。partial は
骨格完備（mana 1、keywords 無し）で、第2条項の CIP
誘発は構築済み、未解決は unsupported の
turn_count_free 1件（第1条項の G・ゼロ）だけ。
partial の text は行の公式テキスト全文と一致するため
**補完なし**。alias は dmrp06-016 の1件で rejects に
独自行は無く、identity 実測で canon_id は対象自身、
aliases_for = [dmrp06-016]。第412弾時点で
real.yaml / real_akashic.yaml / real_vocab.yaml /
real_zone.yaml / proto.yaml / converted.yaml の
いずれにも対象 id・alias とも登録なし。単面カードで
未検証の面は無い。登録ブロッカーの確認（第375弾の
教訓）: rule_convert.split（対象行）は ([], 第1条項の
条項テキスト, [CIP 誘発]) を返し、part[2] の定型所有は
CIP 誘発1件のみで partial の abilities と完全一致する
（G・ゼロは abilities ではなくカードフィールド
free_if のため定型所有の対象外。convert は None）。

結論はドリフト（新規語彙・エンジン・defs・スキーマ
変更なし）。確立形はカードフィールド free_if
{cmp: [{turn_count: {kind: cast, owner: you}},
">=", 3]} ＋ partial 構築済みの CIP 誘発1件。
turn_count の kind: cast は TURN_COUNT_KINDS の
既存種別で、履歴は唱えた側ごとに集計されるため
owner: you で自分の呪文だけを数える。free_if は
defs（chk.cond）と schema.py（ref("cond")）の
両側に定義済み（第408ラウンドの教訓）。

proto T1180（dmex19-028 型）。判別役は既存 proto を
流用: T012（コスト1水呪文役＝唱える判別。相手が
1枚引く効果は無害）/ T009（水マナ役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の
作法）。観測上の注意: 選択肢が pass のみの決定は
エンジンが自動で進めるため、main 決定を観測するには
有料の play 選択肢が残るマナ構成（8枚）にしている。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

FREE_IF = {"cmp": [{"turn_count": {"kind": "cast", "owner": "you"}},
                   ">=", 3]}
CIP = {"kind": "trigger",
       "when": {"event": "move", "to": "bz", "subject": "self"},
       "effect": [{"op": "draw", "count": 2}]}
FORM = [CIP]
FULL_TEXT = ("G・ゼロ：このターン、自分が呪文を３枚以上唱えていれば、"
             "このクリーチャーをコストを支払わずに召喚してもよい。\n"
             "このクリーチャーが出た時、カードを２枚引く。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1180")
    assert c["free_if"] == FREE_IF
    assert c["abilities"] == FORM
    assert c["name"] == "超宮兵 マノミ"
    assert c["types"] == ["creature"] and c["civs"] == ["water"]
    assert c["cost"] == 5 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ムートピア"]
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.free_if == FREE_IF
    assert d.abilities == FORM
    for tid in ("T009", "T012"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX412", "name": "超宮兵 マノミ",
                    "types": ["creature"], "civs": ["water"],
                    "cost": 5, "power": 4000, "mana": 1,
                    "races": ["ムートピア"],
                    "free_if": copy.deepcopy(FREE_IF),
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert d.free_if == FREE_IF
    assert d.abilities == FORM


def _bad(free_if):
    with pytest.raises(DefError):
        parse_card({"id": "TX412B", "name": "x", "types": ["creature"],
                    "civs": ["water"], "cost": 5, "power": 4000,
                    "free_if": free_if,
                    "abilities": copy.deepcopy(FORM)}, TABLES)


def test_bad_unknown_kind():
    _bad({"cmp": [{"turn_count": {"kind": "bogus", "owner": "you"}},
                  ">=", 3]})


def test_bad_unknown_cond_key():
    _bad({"bogus": 1})


def test_bad_operator():
    _bad({"cmp": [{"turn_count": {"kind": "cast", "owner": "you"}},
                  "===", 3]})


def test_bad_owner():
    _bad({"cmp": [{"turn_count": {"kind": "cast", "owner": "bogus"}},
                  ">=", 3]})


def test_bad_missing_kind():
    _bad({"cmp": [{"turn_count": {"owner": "you"}}, ">=", 3]})


def test_bad_unknown_turn_count_key():
    _bad({"cmp": [{"turn_count": {"kind": "cast", "owner": "you",
                                  "bogus": 1}}, ">=", 3]})


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _tapped_mana(e, p):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


def _in_bz(e, p, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist("bz", p))


def _main_keys(e, player, casts):
    """player の main まで進め、casts を順に唱えた後の
    main 選択肢キーを返す（唱える前の main でも使う）。"""
    casts = list(casts)
    for _ in range(900):
        d = e.advance()
        if d is None:
            return None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == player:
            if casts:
                k = f"play:{casts[0]}"
                assert k in keys, f"{k} not in {keys}"
                casts.pop(0)
                e.answer([keys.index(k)])
                continue
            return keys
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return None


def _play_and_settle(e, player, key, done):
    """player の main で key を選び、done() になるまで進める。"""
    played = False
    for _ in range(600):
        if played and done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" \
                and d.get("player") == player and key in keys:
            played = True
            e.answer([keys.index(key)])
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return done()


def test_no_free_without_casts(rules):
    """0枚唱えた状態では無料選択肢は出ず、有料だけが出る。"""
    e = _build(rules, {"hand": ["T1180"], "mana": ["T009"] * 8}, {})
    keys = _main_keys(e, 0, [])
    assert "play:T1180" in keys
    assert "play:T1180:free" not in keys


def test_no_free_after_two_spells(rules):
    """2枚では閾値3に届かず、無料選択肢は出ない
    （有料は残る＝main 決定そのものは観測できる）。"""
    e = _build(rules,
               {"hand": ["T1180", "T012", "T012"], "mana": ["T009"] * 8},
               {})
    keys = _main_keys(e, 0, ["T012", "T012"])
    assert "play:T1180" in keys
    assert "play:T1180:free" not in keys
    assert _tapped_mana(e, 0) == 2


def test_free_after_three_spells_and_cip(rules):
    """3枚唱えると無料選択肢が出る。無料で召喚すると
    マナは呪文の3枚分しかタップされず、CIP で2枚引く。"""
    e = _build(rules,
               {"hand": ["T1180", "T012", "T012", "T012"],
                "mana": ["T009"] * 8},
               {})
    keys = _main_keys(e, 0, ["T012", "T012", "T012"])
    assert "play:T1180:free" in keys
    assert _tapped_mana(e, 0) == 3
    hand_before = len(e.zlist("hand", 0))
    assert hand_before == 1            # 手札は T1180 のみ
    ok = _play_and_settle(e, 0, "play:T1180:free",
                          lambda: _in_bz(e, 0, "T1180"))
    assert ok
    assert _tapped_mana(e, 0) == 3     # 無料召喚で追加タップなし
    # CIP: 召喚で -1、ドローで +2
    assert len(e.zlist("hand", 0)) == hand_before - 1 + 2


def test_paid_summon_and_cip(rules):
    """通常の支払いでも召喚でき、CIP は同様に発火する
    （free_if は支払い経路を妨げない）。"""
    e = _build(rules, {"hand": ["T1180"], "mana": ["T009"] * 5}, {})
    ok = _play_and_settle(e, 0, "play:T1180",
                          lambda: _in_bz(e, 0, "T1180"))
    assert ok
    assert _tapped_mana(e, 0) == 5
    assert len(e.zlist("hand", 0)) == 2   # CIP の2ドロー


def test_opponent_casts_do_not_enable(rules):
    """相手が自分のターンに呪文を3枚唱えても、自分の
    次のターンでは無料にならない（owner: you の判別）。"""
    e = _build(rules,
               {"hand": ["T1180"], "mana": ["T009"] * 5},
               {"hand": ["T012", "T012", "T012"], "mana": ["T009"] * 3})
    keys = _opp_casts_then_my_main(e)
    assert keys is not None
    assert "play:T1180" in keys
    assert "play:T1180:free" not in keys


def _opp_casts_then_my_main(e):
    """自分の1ターン目の main は pass で終え、相手
    （player 1）に T012 を3枚唱えさせ、その後の自分
    （player 0）の main 選択肢キーを返す。"""
    casts = ["T012", "T012", "T012"]
    phase = "first"    # 自分の1ターン目 → 相手 → 自分の2ターン目
    for _ in range(1200):
        d = e.advance()
        if d is None:
            return None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == 0 \
                and phase == "first":
            phase = "opp"            # 何もせずターンを終える
        elif d["kind"] == "main" and d.get("player") == 1 \
                and phase == "opp":
            if casts:
                k = f"play:{casts[0]}"
                assert k in keys, f"{k} not in {keys}"
                casts.pop(0)
                e.answer([keys.index(k)])
                if not casts:
                    # 唱え終わり。次の main 決定は pass のみで
                    # 自動進行しうるため、ここで遷移させる
                    phase = "mine"
                continue
        elif d["kind"] == "main" and d.get("player") == 0 \
                and phase == "mine":
            return keys
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return None
