"""語彙パイロット第385弾: cost_amount_draw（ドリフト）。

センサス（rejects 1,948件を取り直し）: pure 1,800件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜384弾）は再提案しない。本弾で個別に
評価して見送った候補: enters_tapped_grant（pure 1、
dm26ex3-010。第384弾の grant [enters_tapped] 形で
「相手のクリーチャーはタップして出る」自体は書けるが、
第4条項「相手のクリーチャーの能力または呪文によって
自分の手札から捨てられる時、墓地に置くかわりに出して
もよい」が partial に未構築で、捨て札の置換照合
（第379弾で madness を却下したのと同根）が残るため
本 gap 単独では登録形が定まらない）、
chosen_creature_can_be_attacked_while_untapped
（pure 1、dm01-034。攻撃側の allow {attack_creature,
other: {tapped: false}} とは向きが違い、選んだ
クリーチャー側に「タップされていなくても攻撃できる」
を付ける対象側の mod が無い＝新語彙が要る）、
battle_loser_not_destroyed_vs_self（pure 1、dm20-025。
「このクリーチャーとのバトルに負けたクリーチャーは
破壊されず留まる」はバトル相手を条件とする破壊置換で、
battle_indestructible は自己スコープのみ。第384弾の
blocker_dies_after_battle_even_if_wins 却下と同根）、
count_distinct_races（pure 1、dm20-037。count は
カードの枚数を数える機構で、種族の種類数を数える
distinct な式が無い。distinct_civ_count /
distinct_race_count も同根）、shuffle_own_shields
（pure 1、dm22-029。自分のシールドのシャッフルと
裏向き化を行う op が無い）、trigger_when_battle_won
（pure 1、dm26ex4-052。バトル勝利誘発自体は第377・
378弾で確立したが、マナ枚数パワーと「各ターン、相手が
はじめて攻撃するなら、このクリーチャーを攻撃する」の
初回攻撃の強制条項が未構築で複合）、leave_trigger
（pure 1、dm37-045。離脱誘発に加え、名前の部分一致で
公開したカードを選ぶ＋残りを墓地に置く複合効果で
最小でない）、next_shield_grant（pure 1、dm39-007。
「次に自分の手札に加えるシールド」への一回限りの
遅延付与で、ラウンド392の dynamic allow 形
（シールドゾーン滞在中に効く）とは対象ゾーンと回数が
異なり確立形が無い）、conditional_tapped_state
（pure 1、dmrp01-008。自分自身のタップ／アンタップ
状態を static の if で参照する確立形が無く、第383弾の
s_trigger_lock 却下と同根の条件が残る）、
vortex_evolution（pure 1、31-sec001。進化Vと
メテオバーンの複合機構）、force_block（pure 1、
dmr09-004。ブロッカーの付与は書けるが「可能であれば
ブロックする」のブロック強制の mod が無い。
must_be_attacked は攻撃先の強制で別機構）。
範囲内・未評価で最小の cost_amount_draw（pure 1件、
multi にも現れない）を選定した。

対象は pure 1件すべて: promoy18-087 リッチ警官
キャッシュ！（光/水のクリーチャー、コスト8、パワー
2500、ヒューマノイド）。partial は骨格（types /
civs / cost / mana / power / races のみ、abilities・
keywords ともに無し）で、未解決は unsupported の
cost_amount_draw 1件だけ（partial の注記「コスト値を
参照するドローを表す語彙が無いため unsupported に
残した」は、第368弾の cost_of 一般式で解消済みだった）。
単面カードで未検証の面は無く、alias は無い。条項
「このクリーチャーがバトルゾーンに出た時、自分の
手札を１枚、相手に見せてもよい。そうしたら、その
カードのコストと同じ枚数のカードを引く」はすべて
確立済みの部品で表せる（追加語彙なし）:

- 「見せてもよい」は登録先例 dmr05-046 の形そのもの:
  may の中で手札から選ぶ（choose {select: {zone: hand,
  owner: you, count: 1}, as: pick}）。公開自体に追加の
  機械的効果はなく、選んだカードは手札に留まる
  （dmr05-046 の notes どおり）。任意性は may が担い、
  見せると決めたら選択は必須（候補2枚で min=1 を実測）。
- 「そのカードのコストと同じ枚数引く」は第368弾の
  確立形 draw {count: {cost_of: pick}}。cost_of は
  selectors の一般式で、束縛した手札カードのコストを
  読む。候補が無ければ（手札が空）cost_of は 0 で
  引かない（第368弾と同じ読み。本弾で実挙動固定）。

確立形: abilities = [trigger {when: {event: move,
to: bz, subject: self}, effect: [may [choose
{select: {zone: hand, owner: you, count: 1},
as: pick}, draw {count: {cost_of: pick}}]]}] の1件。

partial の text は条項の断片（「コストと同じ枚数
引く」）だけのため、提出形では text に行の公式
テキスト全文を入れる（補完あり。ラウンド420への
注意に明記）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い。choose /
draw / cost_of は defs の検証と schema.py の両方に
定義済みであることを第408弾の教訓どおり確認済み
（スキーマ再生成不要・Rust ミラー不要・rust_stamp
への影響なし）。

proto T1148（promoy18-087 型）。判別役の手札カードと
マナは既存 proto を流用: T1109（コスト3・水。
第368弾）、T1110（コスト5。第368弾）、T1146
（光・コスト3。第384弾。マナ用）。マナは水4＋光4に
する: 多色カードの支払いには文明ごとに少なくとも
1枚の同文明マナが要るため、水だけでは play 選択肢が
出ない（本弾で実測）。

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

TRIGGER = {"kind": "trigger",
           "when": {"event": "move", "to": "bz", "subject": "self"},
           "effect": [{"op": "may", "body": [
               {"op": "choose",
                "select": {"zone": "hand", "owner": "you", "count": 1},
                "as": "pick"},
               {"op": "draw", "count": {"cost_of": "pick"}}]}]}
FORM = [TRIGGER]
FULL_TEXT = ("このクリーチャーがバトルゾーンに出た時、自分の手札を"
             "１枚、相手に見せてもよい。そうしたら、そのカードの"
             "コストと同じ枚数のカードを引く。")
MANA = ["T1109"] * 4 + ["T1146"] * 4   # 水4＋光4（多色の支払い）


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1148")
    assert c["name"] == "リッチ警官 キャッシュ！"
    assert c["types"] == ["creature"]
    assert c["civs"] == ["light", "water"]
    assert c["cost"] == 8 and c["power"] == 2500 and c["mana"] == 1
    assert c["races"] == ["ヒューマノイド"]
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(c, TABLES)
    assert d.abilities == FORM
    for tid in ("T1109", "T1110", "T1146"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX385", "name": "x",
                    "types": ["creature"], "civs": ["light", "water"],
                    "cost": 8, "power": 2500, "mana": 1,
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert d.abilities == FORM


def test_bad_draw_expr_rejected(rules):
    # draw の count 式は既知の式キーしか許さない
    # （defs の検証）。未知キーは DefError
    bad = copy.deepcopy(proto_card("T1148"))
    bad["abilities"][0]["effect"][0]["body"][1]["count"] = \
        {"bogus_of": "pick"}
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


def _summon(rules, p0, may_yes, choose_defn=None):
    """p0 が T1148 を召喚し、CIP の may / choose に答えて
    解決まで進める。（engine, 召喚したか, may が出たか,
    choose の min）を返す。"""
    e = _build(rules, p0)
    played = False
    may_seen = False
    chose_min = None
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and d.get("player") == 0 \
                and "play:T1148" in keys:
            played = True
            e.answer([keys.index("play:T1148")])
            continue
        if played and d["kind"] == "yes_no":
            may_seen = True
            e.answer([keys.index("yes" if may_yes else "no")])
            continue
        if played and d["kind"] == "choose_cards":
            chose_min = d["min"]
            idx = [i for i, o in enumerate(d["options"])
                   if choose_defn in o["key"]]
            assert idx, f"{choose_defn} が選択肢に無い: {keys}"
            e.answer(idx[:1])
            continue
        if played and d["kind"] in ("main", "charge", "attack"):
            break          # 解決が終わり次の通常判断に戻った
        e.answer(_boring(d))
    return e, played, may_seen, chose_min


def _hand_defns(e):
    return [e.cdef(c).id for c in e.zlist("hand", 0)]


def test_show_cost5_draws_five(rules):
    """見せることを選び、手札のコスト5（T1110）を見せると
    5枚引く。見せたカード自体は手札に留まる。候補が1枚
    だけの時は選択判断が出ず自動で決まる（第368弾と同じ
    作法。選択が必須であることは候補2枚のテストで固定）。"""
    e, played, may_seen, _ = _summon(
        rules, {"hand": ["T1148", "T1110"], "mana": MANA}, True, "T1110")
    assert played and may_seen
    hand = _hand_defns(e)
    assert len(hand) == 1 + 5          # 見せた1枚＋引いた5枚
    assert hand[0] == "T1110"          # 見せたカードは手札に留まる
    assert "T1148" in [e.cdef(c).id for c in e.zlist("bz", 0)]


def test_decline_may_draws_nothing(rules):
    """見せないことを選べば何も引かない（任意性は may が
    担う）。"""
    e, played, may_seen, _ = _summon(
        rules, {"hand": ["T1148", "T1110"], "mana": MANA}, False, "T1110")
    assert played and may_seen
    assert _hand_defns(e) == ["T1110"]


def test_choose_cost3_among_two_draws_three(rules):
    """候補が2枚（コスト3とコスト5）あれば選択は必須
    （min=1）で、コスト3を選べば3枚引く（cost_of は
    束縛したカードのコストを読む判別）。"""
    e, played, may_seen, chose_min = _summon(
        rules, {"hand": ["T1148", "T1109", "T1110"], "mana": MANA},
        True, "T1109")
    assert played and may_seen
    assert chose_min == 1
    hand = _hand_defns(e)
    assert len(hand) == 2 + 3          # 残り2枚＋引いた3枚
    assert "T1109" in hand and "T1110" in hand


def test_empty_hand_resolves_without_draw(rules):
    """召喚後に手札が無ければ、may に同意しても選ぶ
    候補が無く0枚引く（cost_of は 0。第368弾と同じ読み）。
    解決は通常どおり終わる。"""
    e, played, may_seen, chose_min = _summon(
        rules, {"hand": ["T1148"], "mana": MANA}, True, "T1109")
    assert played and may_seen
    assert chose_min is None           # 選択判断自体が出ない
    assert _hand_defns(e) == []
    assert "T1148" in [e.cdef(c).id for c in e.zlist("bz", 0)]
