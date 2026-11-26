"""語彙パイロット第404弾: draw_count_by_card（ドリフト）。

センサス（rejects 1,929件を取り直し）: pure 1,781件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜403弾）は再提案しない。
graveyard_replacement の残り1件 dm25ex2-cho021、
battle_opponent_reference の残り1件 dmr01-049、
untap_restriction の残り2件（dm26rp1-td004 /
dmx15-011、形が異なると判定済み）、
cast_limit_once_per_turn の multi 2件
（dm26ex2-pr006 / dm26ex4-cho031）は先行弾の評価を
覆す根拠が無く再提案しない。
destroyed_this_turn_condition と
count_cards_drawn_this_turn は次点のまま残置。
enters_tapped_rule（dmex11-005、静的効果3件）は
後続候補のまま残置。本弾で個別に評価して見送った候補:
draw_until_equal（pure 1、dm24bd6-005。ツインパクトで
partial が素〈ブロッカーも未構築〉、呪文面の
「相手のマナが多ければ上から2枚を裏向きにマナへ」も
未構築で、差分式の検証以前に面の組立てから要り
本弾より重い）、mirror_opponent_draw（pure 1、
dm23bd7-029。「相手が引いた時、同じ枚数」の誘発は
引いた枚数を参照するドローイベント誘発が未確立で、
draw_mirror / mirror_draw_except_turn_draw /
turn_draw_trigger も同根）、turn_history_attacked
（pure 1、dmd27-016。turn_count {kind: attack} は
所有者単位の集計で、「このクリーチャーが攻撃して
いたら」という個体単位の攻撃履歴の条件形が無い）、
fury_charge（pure 1、dmx12b-015。「出たターンに
タップしているクリーチャーを攻撃できる」は
召喚酔いの対象限定解除で、mach_fighter（タップ・
アンタップ両方可）とは範囲が違い確立形が無い）、
untap_unless_destroy（pure 1、dmrp03-042。
「他のクリーチャーを1体破壊しなければアンタップ
しない」はアンタップステップでの支払い型条件で
確立形が無い）、keyword_exists_condition（pure 1、
dmr07-010。攻撃時誘発2件の複合で、T・ブレイカー側が
W・ブレイカー側を「かわりに」で上書きする優先関係の
検証が要り本弾より重い）、shield_faceup_trigger
（pure 1、dmd11-006。「表向きのシールドがブレイク
された時」の誘発はブレイクされるシールドの表向き
条件の照合が未検証）、no_shield_broken_this_turn_
condition（pure 1、dmrp13-s04。name・partial の無い
素行で、マジボンバーが同居し評価不能）。
範囲内・未評価で最小の **draw_count_by_card
（pure 1件、multi にも現れない）** を選定した。

対象は pure 1件すべて: dmr05-021 知識の包囲網
（水の呪文、コスト7）。partial は骨格のみ（types /
civs / cost / mana、spell・abilities ともに無し）で、
text は断片（「そのカードのコストと同じ枚数」）だけ、
未解決は unsupported の draw_count_by_card 1件だけ
（partial の注記「カードのコスト分のドローを表す
語彙が無い」は、第368弾の cost_of 一般式で解消済み
だった）。単面カードで未検証の面は無く、alias は
無い（identity 実測で canon_id は対象自身、
aliases_for = []）。条項「自分の手札を１枚見せる。
そのカードのコストと同じ枚数のカードを引く」は
すべて確立済みの部品で表せる（追加語彙なし）:

- 「自分の手札を1枚見せる」は第385弾の手札 choose:
  choose {select: {zone: hand, owner: you, count: 1},
  as: pick}。公開自体に追加の機械的効果はなく、
  選んだカードは手札に留まる（登録先例 dmr05-046 の
  may 内 choose と同系統。本件は文面に任意性が無い
  ため may で包まないのが第385弾との差）。
- 「そのカードのコストと同じ枚数引く」は第368弾の
  呪文形 draw {count: {cost_of: pick}}。候補が
  無ければ（手札がこの呪文以外に無い）cost_of は
  0 で引かない（第368弾と同じ読み。本弾で実挙動固定）。

確立形: spell = [choose {select: {zone: hand,
owner: you, count: 1}, as: pick},
draw {count: {cost_of: pick}}] の2 op。

**補完あり: spell と text**（partial は骨格のみで
text は断片のため、提出形では spell を構築し、
text に行の公式テキスト全文を入れる。ラウンド439
への注意に明記）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い。
choose / draw / cost_of は defs の検証と schema.py
の両方に定義済みであることを第408ラウンドの教訓
どおり確認済み（スキーマ再生成不要・Rust ミラー
不要・rust_stamp への影響なし）。

proto T1171（dmr05-021 型）。判別役の手札カードと
マナは既存 proto を流用: T1109（コスト3・水。
第368弾。水マナ役も兼ねる）、T1110（コスト5。
第368弾）。

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

SPELL = [{"op": "choose",
          "select": {"zone": "hand", "owner": "you", "count": 1},
          "as": "pick"},
         {"op": "draw", "count": {"cost_of": "pick"}}]
FORM = SPELL
FULL_TEXT = "自分の手札を１枚見せる。そのカードのコストと同じ枚数のカードを引く。"
MANA = ["T1109"] * 7   # 水7（コスト7の支払い）


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1171")
    assert c["name"] == "知識の包囲網"
    assert c["types"] == ["spell"]
    assert c["civs"] == ["water"]
    assert c["cost"] == 7 and c["mana"] == 1
    assert c["text"] == FULL_TEXT
    assert c["spell"] == SPELL
    d = parse_card(c, TABLES)
    assert [op["op"] for op in d.spell] == ["choose", "draw"]
    assert d.spell[0]["select"] == {"zone": "hand", "owner": "you",
                                    "count": 1}
    assert d.spell[0]["as"] == "pick"
    assert d.spell[1]["count"] == {"cost_of": "pick"}
    for tid in ("T1109", "T1110"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX404", "name": "x",
                    "types": ["spell"], "civs": ["water"],
                    "cost": 7, "mana": 1,
                    "spell": copy.deepcopy(SPELL)}, TABLES)
    assert [op["op"] for op in d.spell] == ["choose", "draw"]


def test_bad_draw_expr_rejected(rules):
    # draw の count 式は既知の式キーしか許さない
    # （defs の検証）。未知キーは DefError
    bad = copy.deepcopy(proto_card("T1171"))
    bad["spell"][1]["count"] = {"bogus_of": "pick"}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def test_bad_choose_select_key_rejected(rules):
    # choose の select は既知キーしか許さない
    bad = copy.deepcopy(proto_card("T1171"))
    bad["spell"][0]["select"]["bogus"] = 1
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def test_bad_choose_zone_rejected(rules):
    # choose の zone は既知ゾーンしか許さない
    bad = copy.deepcopy(proto_card("T1171"))
    bad["spell"][0]["select"]["zone"] = "nowhere"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def _build(rules, p0, p1=None):
    return scenario.build(rules, {"p0": p0, "p1": p1 or {},
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _boring(d):
    keys = [o["key"] for o in d["options"]]
    for want in ("pass", "end_turn", "end_attack", "end_phase"):
        if want in keys:
            return [keys.index(want)]
    return [0]


def _cast(rules, p0, p1=None, choose_defn=None):
    """p0 が T1171 を唱え、choose が出たら choose_defn を
    選んで解決まで進める。（engine, 唱えたか, choose の
    min, 唱える直前の手札数, 解決後の手札数）を返す。"""
    e = _build(rules, p0, p1)
    cast = False
    chose_min = None
    hand_before = None
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not cast and d["kind"] == "main" and d.get("player") == 0 \
                and "play:T1171" in keys:
            hand_before = len(e.zlist("hand", 0))
            cast = True
            e.answer([keys.index("play:T1171")])
            continue
        if cast and d["kind"] == "choose_cards":
            chose_min = d["min"]
            if choose_defn is not None:
                idx = [i for i, o in enumerate(d["options"])
                       if choose_defn in o["key"]]
                assert idx, f"{choose_defn} が選択肢に無い: {keys}"
                e.answer(idx[:1])
            else:
                e.answer([0])
            continue
        if cast and d["kind"] in ("main", "charge", "attack"):
            break          # 解決が終わり次の通常判断に戻った
        e.answer(_boring(d))
    return e, cast, chose_min, hand_before, len(e.zlist("hand", 0))


def test_cast_show_cost5_draws_5(rules):
    """手札のコスト5を見せると5枚引く。見せたカードは
    手札に留まる。唱えた呪文は墓地に置かれる。"""
    e, cast, chose_min, hb, ha = _cast(
        rules, {"hand": ["T1171", "T1110"], "mana": MANA},
        choose_defn="T1110")
    assert cast
    assert ha == hb - 1 + 5
    assert "T1110" in [e.cdef(c).id for c in e.zlist("hand", 0)]
    assert "T1171" in [e.cdef(c).id for c in e.zlist("graveyard", 0)]


def test_cast_show_choice_is_mandatory(rules):
    """候補が2枚あれば選択は必須（min=1）で、コスト3を
    選べば3枚引く（文面に任意性は無い）。"""
    e, cast, chose_min, hb, ha = _cast(
        rules, {"hand": ["T1171", "T1109", "T1110"], "mana": MANA},
        choose_defn="T1109")
    assert cast
    assert chose_min == 1
    assert ha == hb - 1 + 3
    assert "T1109" in [e.cdef(c).id for c in e.zlist("hand", 0)]


def test_cast_no_other_hand_draws_0(rules):
    """手札がこの呪文だけなら見せるカードが無く、
    0枚で解決して墓地に置かれる（cost_of は未束縛で
    0。第368弾と同じ読み）。"""
    e, cast, chose_min, hb, ha = _cast(
        rules, {"hand": ["T1171"], "mana": MANA})
    assert cast
    assert ha == hb - 1
    assert "T1171" in [e.cdef(c).id for c in e.zlist("graveyard", 0)]


def test_cast_opponent_hand_not_a_candidate(rules):
    """範囲判別: 見せられるのは自分の手札だけ
    （owner: you）。相手の手札にコスト5があっても
    引けない。"""
    e, cast, chose_min, hb, ha = _cast(
        rules, {"hand": ["T1171"], "mana": MANA},
        p1={"hand": ["T1110"]})
    assert cast
    assert ha == hb - 1
