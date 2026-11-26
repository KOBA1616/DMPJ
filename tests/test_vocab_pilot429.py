"""語彙パイロット第429弾: drew_this_turn_condition（ドリフト）。

センサス（rejects 1,902件を取り直し）: pure 1,754件
（989家族）/ multi 130件 / 空 gaps 18件。pure の大半は
範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。評価済み却下（第316〜320・
355〜428弾）は原則として再提案しない。残置群
（graveyard_replacement 残り dm25ex2-cho021、
battle_opponent_reference 残り dmr01-049、
untap_restriction 残り2件、does_not_untap 残り
dm25ex2-031、cast_limit_once_per_turn の multi 2件、
summoning_attack_rule 残り dmex07-s01、
entered_turn_attack 残り dmbd11-d05、madness 残り
dmx26-028、次点の destroyed_this_turn_condition /
count_cards_drawn_this_turn〔dm12-010 で本件とは別行〕、
後続候補の distinct_civ_count、将来の新規語彙候補
first_time_tap、専用ステージ送りの
power_threshold_keyword_gain）は覆す根拠が無く
再提案しない。本弾で個別に評価して見送った候補:
turn_history_entry（dmc55-061。第427弾の鏡像だが
種族フィルタつき出場数は turn_count の filter が
kind: attack / enter_unpaid 限定で kind: enter は
素カウンタ記録のため照合できず、新規語彙候補として
残す）、force_block_and_trigger_when_blocked
（dm09-018。選択ブロッカー単体への強制＋他者排除と
「ブロックされたとき」誘発の複合で未確立）、
turn_history_free_summon（dm26ex3-dcr011。マナを
タップせずに出した履歴の記録が無い＋複合）、
turn_destroyed_count（dm26rp2-std008。look/reorder
系の未確立機構＋追加ターンの複合）、
override_cannot_attack_for_player_attack（dm02-023。
101.2 で「できない」が勝ち allow では上書きできない）。

範囲内・最小の **drew_this_turn_condition（pure 1件、
multi にも現れない）** を選定した。行の注記「この
ターンのドロー枚数条件を表す語彙が無い」は履歴
カウンタ基盤より前の陳腐化した評価で、確立部品の
組み合わせで表せる（ドリフト。新規語彙・エンジン・
defs・スキーマ変更なし）:
- G・ゼロはカードフィールド free_if（defs は
  chk.cond、schema.py は ref("cond")。第412弾）。
  free_if {cmp: [{turn_count: ...}, ">=", N]} は
  第412弾の登録済み dmex19-028（kind: cast）と同形で、
  本件は kind: draw・閾値6に替えたもの。
- 「自分の同名がバトルゾーンになければ」は
  {not: {exists: {zone: bz, owner: you, filter:
  {name: <同名>}}}} で、登録済み dmex08-226 /
  dm25ex3-rp4tr6 の free_if {all: [cmp, not exists]}
  と同じ合成。filter の name は完全一致照合。
- kind: draw は引いた側ごとに1枚ずつ hist:draw へ
  集約される（events の _record_history）。本弾の
  実測では、先攻1ターン目はドローが無くカウンタは
  空、2ターン目の main では hist:draw:0 = 1、つまり
  ターンドローも「このターン引いた枚数」に含まれる
  （公式の読みと一致）。
- 残りはキーワード speed_attacker / double_breaker。
  「マナゾーンに置く時タップして置く」は多色ルール
  405.1 でエンジンコア適用済みのためテキストのみ
  （第399弾）。abilities は無し。

対象は dmx22b-038 天災超邪 クロスファイア 2nd
（水/火 / コスト7 / パワー7000 / 種族
アウトレイジMAX / mana 1）。partial は骨格のみで
text は断片、keywords・free_if は未構築。
**補完あり: text（公式全文）＋keywords＋free_if**。
alias は dmr11-017 / promoy12-063 の2件で rejects に
独自行は無く、identity 実測で canon_id は対象自身、
aliases_for = 2件。第429弾時点で real.yaml /
real_akashic.yaml / real_vocab.yaml / real_zone.yaml /
proto.yaml / converted.yaml のいずれにも対象 id・
alias とも登録なし。登録ブロッカーの確認（第375弾の
教訓）: rule_convert.split（対象行）は None を返し
定型所有は無い（G・ゼロは free_if フィールドで
定型所有の対象外でもある）。

proto T1208（dmx22b-038 型）。判別役は既存 proto を
流用: T003（水呪文・2ドロー役）/ T705（水呪文・
1ドロー役＝境界判別）/ T009（水マナ役）/ T1207
（火マナ役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の
作法）。観測上の注意: 選択肢が pass のみの決定は
エンジンが自動で進めるため、main 決定を観測するには
有料の play 選択肢が残るマナ構成（14枚）にしている。
マナは水7＋火7（T1207 を火マナ役に流用）: 多色カードの
支払いには文明ごとに1枚ずつ要るため、水だけでは
play 選択肢自体が出ない（本弾で実測）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

NAME = "天災超邪 クロスファイア 2nd"
FREE_IF = {"all": [
    {"cmp": [{"turn_count": {"kind": "draw", "owner": "you"}}, ">=", 6]},
    {"not": {"exists": {"zone": "bz", "owner": "you",
                        "filter": {"name": NAME}}}}]}
KEYWORDS = ["speed_attacker", "double_breaker"]
FULL_TEXT = ("マナゾーンに置く時、このカードはタップして置く。"
             "G・ゼロ―このターン、カードを６枚以上引いていて、"
             "自分の 《天災超邪 クロスファイア ２nd》がバトルゾーンに"
             "なければ、このクリーチャーをコストを支払わずに"
             "召喚してもよい。スピードアタッカーW・ブレイカー")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1208")
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["water", "fire"]
    assert c["cost"] == 7 and c["power"] == 7000 and c["mana"] == 1
    assert c["races"] == ["アウトレイジMAX"]
    assert c["keywords"] == KEYWORDS
    assert c["free_if"] == FREE_IF
    assert c["text"] == FULL_TEXT
    assert not c.get("abilities")
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.free_if == FREE_IF
    assert d.keywords == KEYWORDS
    # キーワード2件が static に展開されるだけ（能力は増えない）
    assert d.abilities == [
        {"kind": "static", "affects": "self",
         "mod": {"allow": ["attack_summoning_sick"]},
         "keyword": "speed_attacker"},
        {"kind": "static", "affects": "self",
         "mod": {"breaks": 2}, "keyword": "double_breaker"}]
    for tid in ("T003", "T705", "T009"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX429", "name": NAME,
                    "types": ["creature"], "civs": ["water", "fire"],
                    "cost": 7, "power": 7000, "mana": 1,
                    "races": ["アウトレイジMAX"],
                    "keywords": copy.deepcopy(KEYWORDS),
                    "free_if": copy.deepcopy(FREE_IF)}, TABLES)
    assert d.free_if == FREE_IF
    assert d.keywords == KEYWORDS


def _bad(free_if):
    with pytest.raises(DefError):
        parse_card({"id": "TX429B", "name": "x", "types": ["creature"],
                    "civs": ["water"], "cost": 7, "power": 7000,
                    "free_if": free_if}, TABLES)


def test_bad_unknown_kind():
    _bad({"cmp": [{"turn_count": {"kind": "bogus", "owner": "you"}},
                  ">=", 6]})


def test_bad_unknown_cond_key():
    _bad({"bogus": 1})


def test_bad_operator():
    _bad({"cmp": [{"turn_count": {"kind": "draw", "owner": "you"}},
                  "===", 6]})


def test_bad_filter_on_draw_count():
    # turn_count の filter は kind: attack / enter_unpaid 限定
    # （kind: draw には付けられない）
    _bad({"cmp": [{"turn_count": {"kind": "draw", "owner": "you",
                                  "filter": {"types": ["creature"]}}},
                  ">=", 6]})


def test_bad_exists_filter_key():
    _bad({"not": {"exists": {"zone": "bz", "owner": "you",
                             "filter": {"bogus": 1}}}})


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


def test_no_free_without_draws(rules):
    """0枚引いた状態では無料選択肢は出ず、有料だけが出る。"""
    e = _build(rules, {"hand": ["T1208"], "mana": ["T009"] * 7 + ["T1207"] * 7}, {})
    keys = _main_keys(e, 0, [])
    assert "play:T1208" in keys
    assert "play:T1208:free" not in keys


def test_no_free_at_five_draws(rules):
    """2ドロー×2＋1ドロー＝5枚では閾値6に届かず、
    無料選択肢は出ない（有料は残る）。"""
    e = _build(rules,
               {"hand": ["T1208", "T003", "T003", "T705"],
                "mana": ["T009"] * 7 + ["T1207"] * 7},
               {})
    keys = _main_keys(e, 0, ["T003", "T003", "T705"])
    assert "play:T1208" in keys
    assert "play:T1208:free" not in keys
    assert _tapped_mana(e, 0) == 5


def test_free_at_six_draws(rules):
    """2ドロー×3＝6枚で無料選択肢が出る。無料で召喚すると
    マナは呪文の6枚分しかタップされない。"""
    e = _build(rules,
               {"hand": ["T1208", "T003", "T003", "T003"],
                "mana": ["T009"] * 7 + ["T1207"] * 7},
               {})
    keys = _main_keys(e, 0, ["T003", "T003", "T003"])
    assert "play:T1208:free" in keys
    assert _tapped_mana(e, 0) == 6
    ok = _play_and_settle(e, 0, "play:T1208:free",
                          lambda: _in_bz(e, 0, "T1208"))
    assert ok
    assert _tapped_mana(e, 0) == 6     # 無料召喚で追加タップなし


def test_no_free_when_same_name_in_bz(rules):
    """6枚引いても、自分の同名がすでにバトルゾーンに
    あれば無料選択肢は出ない（not exists の判別）。"""
    e = _build(rules,
               {"hand": ["T1208", "T003", "T003", "T003"],
                "mana": ["T009"] * 7 + ["T1207"] * 7, "bz": ["T1208"]},
               {})
    keys = _main_keys(e, 0, ["T003", "T003", "T003"])
    assert "play:T1208" in keys
    assert "play:T1208:free" not in keys


def test_turn_draw_counts_on_second_turn(rules):
    """自分の2ターン目: ターンドロー1枚＋2ドロー×2＋
    1ドロー＝6枚で無料選択肢が出る（ターンドローも
    「このターン引いた枚数」に含まれることの判別。
    ターンドローを数えなければ5枚で出ない）。"""
    e = _build(rules,
               {"hand": ["T1208", "T003", "T003", "T705"],
                "mana": ["T009"] * 7 + ["T1207"] * 7},
               {})
    keys = _second_main_keys(e, ["T003", "T003", "T705"])
    assert keys is not None
    assert "play:T1208:free" in keys


def _second_main_keys(e, casts):
    """自分の1ターン目の main は pass で終え、相手ターンも
    pass で流し、自分の2ターン目の main で casts を唱えた
    後の選択肢キーを返す。"""
    casts = list(casts)
    mains = 0
    for _ in range(1500):
        d = e.advance()
        if d is None:
            return None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d.get("player") == 0:
            mains += 1
            if mains >= 2:
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


def test_opponent_draws_do_not_enable(rules):
    """相手が自分のターンに6枚引いても、自分の次のターン
    では無料にならない（owner: you の判別。自分の
    ターンドロー1枚だけでは閾値に届かない）。"""
    e = _build(rules,
               {"hand": ["T1208"], "mana": ["T009"] * 4 + ["T1207"] * 3},
               {"hand": ["T003", "T003", "T003"],
                "mana": ["T009"] * 6})
    keys = _opp_draws_then_my_main(e)
    assert keys is not None
    assert "play:T1208" in keys
    assert "play:T1208:free" not in keys


def _opp_draws_then_my_main(e):
    """自分の1ターン目の main は pass で終え、相手
    （player 1）に T003 を3枚唱えさせ（6ドロー）、
    その後の自分（player 0）の2ターン目の main
    選択肢キーを返す。"""
    casts = ["T003", "T003", "T003"]
    phase = "first"
    for _ in range(1500):
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
