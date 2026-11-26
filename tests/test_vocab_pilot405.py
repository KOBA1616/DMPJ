"""語彙パイロット第405弾: count_distinct_races（種族の種類数）—
新式 distinct_race_count（最小語彙追加）。

センサス（rejects 1,928件を取り直し）: pure 1,780 /
multi 130 / 空 gaps 18。pure の大半は範囲外（gr_summon
147 / aura 108＝未承認 / hyperdimensional_zone 105 /
dragheart 45 / psychic_filter 45 / hyperdimensional_summon
41 / out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。残りは pure 1〜4件の小家族が多数。
評価済み却下（第316〜320・355〜404弾）は再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021、
battle_opponent_reference の残り1件 dmr01-049、
untap_restriction の残り2件（dm26rp1-td004 /
dmx15-011、形が異なると判定済み）、
cast_limit_once_per_turn の multi 2件（dm26ex2-pr006 /
dm26ex4-cho031、他の gaps を併せ持つ）は先行弾の評価を
覆す根拠が無く再提案しない。destroyed_this_turn_condition
と count_cards_drawn_this_turn は次点のまま残す。
enters_tapped_rule（dmex11-005、静的効果3件）は後続候補
のまま残す。本弾で個別に評価して見送った候補:
- distinct_civ_count（pure 1、dmx19-s45）: 第396弾で
  3条項の複合として後続候補に残されたまま。文明の種類数
  自体は既存の civ_count で数えられる。
- turn_destroyed_count（pure 1、dm26rp2-std008）:
  条件部は turn_count {kind: destroyed, owner: any} で
  届く可能性があるが、partial にジャストダイバー／
  T・ブレイカーが未構築で、攻撃時誘発（5枚見て2枚まで
  手札＋残りは下＋パワー6000以下すべて破壊してもよい）
  も残り、本 gap 単独では登録形が定まらない。
- turn_history_entry（pure 1、dmc55-061）: 「そのターン
  中に出していなければ」は種族フィルタつきの登場履歴が
  要る。turn_count の filter は attack / enter_unpaid
  kind 専用で、登場履歴の種族条件形は未確立。
- turn_history_discard（pure 1、dm23ex3-040）: 条件部
  より効果部（自分のマナを裏向きにする）が face_down
  系の未確立機構。
- castle_count（pure 1、dm31-036）: CIP が「城1枚に
  つき（山札上を裏向きにシールド追加＋相手獣1体を
  タップしてもよい）」の回数反復で、count 分の反復合成
  の確立形が無い。条件つき S・トリガー付与条項も同居。
- cost_less_than_destroyed（pure 1、dm24ex1-031）:
  破壊されたカード（イベント主体）のコストを墓地召喚の
  フィルタ式で受ける形の検証が要り本弾より重い。
- arithmetic_count（pure 1、dmex17-087）／
  cost_eq_count（pure 1、dmex08-135）／
  shield_count_tiers（pure 1、dm32-079）／
  same_power_destroy（pure 1、dm29-013）／
  reveal_count_draw（pure 1、dm29-010）／
  under_count（pure 1、dmrp07-s04）／
  civ_all_present（pure 1、dmex08-252）: いずれも行の
  text・partial ともに条項の断片のみで、効果全体が
  行データから評価不能。
- compare_mana_count_with_opponents（pure 1、
  dm23bd7-007）: 多人数戦前提の「相手1人につき」の
  数えで、2人戦での縮退形が文面と一致するかの判断が要る。
- empty_hand_player_count（pure 1、dm26sd1-m008）:
  プレイヤー数の数えに加え、相手ターン開始時の捨て
  誘発・相手が捨てた時のドロー誘発が partial に
  未構築で本 gap 単独では登録形が定まらない。
- tap_each_civilization（pure 1、dm27-018）:
  文明ごとに1枚ずつタップする選択の合成が未確立。
- each_player_mana_put（pure 1、dm24bd5-040）:
  各プレイヤーの任意選択と「置いた相手の人数」の
  追跡が未確立。
- bottom_deck_mill（pure 1、dmx13-010）: 山札下からの
  ミルの検証に加え、破壊時の墓地召喚条項も partial に
  未構築で2条項の組立てが要る。
- smallest_cost_all_destroy（pure 1、dmrp21-005）／
  select_min_power（pure 1、dm23rp2x-021）: extremal
  は min_power / max_power のみで最小コストの選択・
  全体破壊とは形が違う。後者は付与誘発＋相手選択の複合。
- per_civ_selection（pure 1、dmc34-s04）: 5枚公開から
  文明ごとに選ぶ選択の合成が未確立。
- draw_until_count（pure 1、dm24ex3-rp1s03）:
  ハイパー化の面の攻撃時誘発で、ハイパー機構の複合。
- all_mana_multicolor_cond（pure 1、dmrp10-030）:
  ツインパクトの partial の面が x / y の仮置きで
  データ不完全。
- look_top_pick_and_destroy_by_cost（pure 1、
  dm26ex2-002）: スター進化＋公開したカードのコスト
  以下の破壊の複合で本弾より重い。

選定: count_distinct_races（pure 1件、multi にも
現れない）— dm20-037 反骨鉄拳バーニアン。単一条項で
partial は骨格完備、不足は「種族の種類数」を数える式
だけ。既存の distinct_cost_count（第145弾）／
distinct_type_count（第212弾）の種族版として最小の
新規語彙で正確に表せる。

結論: 新式 **distinct_race_count {selector}** を追加
（対象カード群にある種族の種類数。多重種族はすべて
数える）。追加箇所は distinct_type_count と同じ4点:
- dmsim/cards/defs.py: expr() の受理分岐＋
  count_spec() の式キー（mod の count で使うため。
  なお distinct_type_count は count_spec の式キーに
  無い既存の未同期を本弾で観察したが、本弾の対象外
  として未修正のまま記録する）
- dmsim/engine/selectors.py: eval_expr の評価分岐
  （distinct_cost_count / distinct_type_count と同じ
  再入回避の作法: 評価中のカードは印刷特性で見る）
  ＋ count_of の _EXPR_KEYS
- dmsim/cards/schema.py: expr の properties に
  "distinct_race_count": ref("selector") を追加し、
  data/schema/card.schema.json を再生成（差分3行）
式の評価は Python 側のみで、distinct_cost_count /
distinct_type_count と同様に Rust 側の式ミラーは無い
（test_rust_schema_sync は Card / GameState の状態
フィールドのみを対象とする）。selectors.py は
エンジンコードだが、rust_stamp は第364弾以来の先例
どおり据え置きで、この環境では Python のみで動作する。
新規の状態フィールドは無いため state.rs ミラーは不要。

公式テキスト:
「このクリーチャーのパワーは、バトルゾーンにある
相手のクリーチャーの種族ひとつにつき+2000される。」
partial は骨格完備（クリーチャー / 光 / コスト4 /
パワー2000 / 種族 グレートメカオー、mana 1、
keywords・abilities ともに無し）で、未解決は
unsupported の count_distinct_races 1件だけ。
partial の text は行の公式テキスト全文と一致する
ため**補完なし**。alias は無い（identity 実測で
canon_id(dm20-037) = dm20-037、aliases_for = []）。
第405弾時点で real.yaml / real_akashic.yaml /
real_vocab.yaml / real_zone.yaml / proto.yaml /
converted.yaml のいずれにも登録なし。単面カードで
未検証の面は無い。

確立形:
- static {affects: self, mod: {power: {amount: 2000,
  count: {distinct_race_count: {zone: bz, owner: opp,
          filter: {types: [creature]}}}}}}

実挙動の判別（本弾で固定）: 相手クリーチャーが
無ければ 2000（素）。種族1種で 4000。同種族が2体
いても 4000（種類数読みの判別）。2種族を持つ
クリーチャー1体で 6000（多重種族はすべて数える）。
1種＋2種の2体で 8000（3種）。自分のクリーチャーの
種族は数えない（owner: opp の判別）。バトルでも効く
（素2000ではパワー3000ブロッカーに負ける計算が、
ブロッカーの種族1種で 4000 になり勝つ）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い。

プロト: T1172 = dm20-037 型。判別役は既存 proto を
流用: T001（単一種族役＝種族 テスト）/ T787（2種族役
＝アンノウン＋ゼニス）/ T371（3種族役＝ゴッド＋
ダークロード＋ナイト）/ T004（パワー3000ブロッカー役
＝種族 テスト）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
バトルゾーンは共有ゾーンなので所有は bz_tops(p) /
zlist(zone, p) で見る。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

STATIC = {"kind": "static", "affects": "self",
          "mod": {"power": {"amount": 2000,
                            "count": {"distinct_race_count":
                                      {"zone": "bz", "owner": "opp",
                                       "filter": {"types": ["creature"]}}}}}}
FORM = [STATIC]
FULL_TEXT = ("このクリーチャーのパワーは、バトルゾーンにある"
             "相手のクリーチャーの種族ひとつにつき+2000される。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form():
    proto = proto_card("T1172")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    d = parse_card(proto, TABLES)
    assert STATIC in d.abilities
    assert d.types == ["creature"]
    assert d.civs == ["light"]
    assert d.cost == 4 and d.power == 2000
    assert d.races == ["グレートメカオー"]
    assert d.keywords == []
    for tid in ("T001", "T787", "T371", "T004"):
        parse_card(proto_card(tid), TABLES)


def test_bad_expr_key_in_count_rejected():
    bad = dict(proto_card("T1172"))
    bad["abilities"] = [{"kind": "static", "affects": "self",
                         "mod": {"power": {"amount": 2000,
                                           "count": {"distinct_race_counter":
                                                     {"zone": "bz",
                                                      "owner": "opp"}}}}}]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def test_bad_selector_key_in_distinct_race_count_rejected():
    bad = dict(proto_card("T1172"))
    bad["abilities"] = [{"kind": "static", "affects": "self",
                         "mod": {"power": {"amount": 2000,
                                           "count": {"distinct_race_count":
                                                     {"zone": "bz",
                                                      "owner": "opp",
                                                      "bogus": 1}}}}}]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def test_distinct_race_count_non_selector_rejected():
    bad = dict(proto_card("T1172"))
    bad["abilities"] = [{"kind": "static", "affects": "self",
                         "mod": {"power": {"amount": 2000,
                                           "count": {"distinct_race_count": 5}}}}]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _powers(e, tid, p):
    return [e.chars(c)["power"] for c in e.bz_tops(p)
            if e.cdef(c).id == tid]


def test_power_no_opponent_creatures(rules):
    e = _build(rules, {"bz": ["T1172"]}, {"bz": []})
    assert _powers(e, "T1172", 0) == [2000]


def test_power_one_distinct_race(rules):
    e = _build(rules, {"bz": ["T1172"]}, {"bz": ["T001"]})
    assert _powers(e, "T1172", 0) == [4000]


def test_power_same_race_twice_counts_once(rules):
    # 同種族（テスト）が2体いても種類数は1 → 4000
    e = _build(rules, {"bz": ["T1172"]}, {"bz": ["T001", "T001"]})
    assert _powers(e, "T1172", 0) == [4000]


def test_power_multi_race_creature_counts_each_race(rules):
    # T787 は2種族（アンノウン＋ゼニス）を持つ → 2種で 6000
    e = _build(rules, {"bz": ["T1172"]}, {"bz": ["T787"]})
    assert _powers(e, "T1172", 0) == [6000]
    # T371 は3種族を持つ → 3種で 8000
    e = _build(rules, {"bz": ["T1172"]}, {"bz": ["T371"]})
    assert _powers(e, "T1172", 0) == [8000]


def test_power_mixed_opponents(rules):
    # 1種（T001）＋2種（T787）の2体で合計3種 → 8000
    e = _build(rules, {"bz": ["T1172"]}, {"bz": ["T001", "T787"]})
    assert _powers(e, "T1172", 0) == [8000]


def test_own_creatures_do_not_count(rules):
    # 自分の2種族獣（T787）は数えない（owner: opp の判別）
    e = _build(rules, {"bz": ["T1172", "T787"]}, {"bz": []})
    assert _powers(e, "T1172", 0) == [2000]
    # 自分の種族は相手の種族と重なっても影響しない
    e = _build(rules, {"bz": ["T1172", "T001"]}, {"bz": ["T001"]})
    assert _powers(e, "T1172", 0) == [4000]


def _keys(d):
    return [o["key"] for o in d["options"]]


def _battle(e, attacker_p, attacker, blocker):
    """attacker_p の attacker がプレイヤーを攻撃し、相手が
    blocker でブロックする。バトルが終わって attacker_p の
    次の charge が来たら戻る。"""
    state = {}
    for _ in range(3000):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == attacker_p \
                and state.get("blocked"):
            return state
        if d["kind"] == "yes_no":
            e.answer([keys.index("yes")] if "yes" in keys
                     else list(range(d["min"])))
        elif d["kind"] == "attack" and d.get("player") == attacker_p \
                and not state.get("attacked"):
            tgt = [k for k in keys if k == f"attack:{attacker}:player"]
            if tgt:
                state["attacked"] = True
                e.answer([keys.index(tgt[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "block":
            pick = [i for i, k in enumerate(keys)
                    if k.startswith(f"bz:{blocker}")]
            if pick:
                state["blocked"] = True
                e.answer([pick[0]])
            else:
                e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("battle never finished")


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _tops(e, p):
    return [e.s.cards[c].defn for c in e.bz_tops(p)]


def test_battle_wins_by_counted_power(rules):
    # ブロッカー T004（パワー3000・種族 テスト1種）で
    # T1172 は 2000+2000=4000 になり勝つ（素2000では負ける判別）
    e = _build(rules, {"bz": ["T1172"]}, {"bz": ["T004"]})
    state = _battle(e, 0, "T1172", "T004")
    assert state.get("attacked") and state.get("blocked"), state
    assert "T004" in _defns(e, "graveyard", 1)
    assert "T1172" in _tops(e, 0)
