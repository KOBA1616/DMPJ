"""語彙パイロット第406弾: distinct_race_count（pure 1件）—
第405弾の式 distinct_race_count への構造化形
{selector, exclude_races} の追加（最小語彙追加）。

センサス（rejects 1,927件を取り直し）: pure 1,779 /
multi 系 203 家族 / 空 gaps 18。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数。評価済み却下
（第316〜320・355〜405弾）は再提案しない。
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
- distinct_civ_count（pure 1、dmx19-s45）: 第405弾でも
後続候補のまま。3条項の複合（CIP の任意ドロー＋
パワー＋全文明でのワールド・ブレイカー獲得）で、
文明の種類数を数える式（civ_count は重複を数えるため
種類数にはならない）以前に条項の組立てが要り本弾より
重い。
- e_soul（pure 1、dm24ex3-td06）: unsupported は
だけだが、partial には CIP の山札操作
（見て3枚選び残りを墓地、選んだ3枚を順序付けて上へ）
が未構築のまま同居しておらず、行の gaps と partial の
対応が取れていない。山札の順序付け直しの検証から
要り本 gap 単独では登録形が定まらない。
- civ_all_present（pure 1、dmex08-252）: 第405弾で
text・partial が断片のみで評価不能と記録済み。
G・ゼロと破壊置換の2条項でもある。
- blocker_dies_after_battle_even_if_wins（pure 1、
dm01-028）: 「自分のクリーチャーをブロックした相手
クリーチャー」を対象にバトル勝利時も破壊する呪文で、
ブロックした側へのスレイヤー付与の範囲限定形が
未確立（partial の注記どおり全面スレイヤー付与では
広すぎる）。
- battle_does_not_occur_when_blocking（pure 1、
dm06-072）: バトルそのものの取消しが未確立。
- battle_loser_not_destroyed_vs_self（pure 1、
dm20-025）: 「このクリーチャーとのバトルに負けた
相手」を置換対象として参照する形が未確立。
- first_battle_win（pure 1、dm26sd1-g004）/
first_won_battle（pure 1、dm30-055）/
trigger_when_battle_won（pure 1、dm26ex4-052）:
バトル勝利の照合・初回性の追跡が未確立（第382弾の
battle_win は「このターンまだ勝っていない」条件の
turn_count で、勝利時誘発そのものは無い）。対象行も
複数条項の複合。
- same_name_count（pure 1、dm28-006）: 同名カードの
枚数を数える式が無い。常在型の自己破壊条件も同居。
- cost_per_type_count（pure 1、dm25ex2-020）/
type_count_cost（pure 1、dmex18-020）: カードタイプの
種類数（distinct_type_count は第405弾で観察された
count_spec 未同期があり mod の count 位置では検証を
通らない）によるコスト軽減で、対象行はいずれも
他条項の複合。
- turn_count_cost_reduction（pure 1、dmex14-054）:
召喚と詠唱の合算回数による軽減で、2種の履歴の合算形
が未確立。

選定: distinct_race_count（pure 1件、multi にも
現れない）— dmx12b-058 口寄の化身。単一条項で partial
は骨格完備。不足は「ミステリー・トーテム以外の種族」
という種族名単位の除外だけであり、第405弾の式への
最小の拡張で正確に表せる。なお除外はカード単位では
表せない: ミステリー・トーテムを含む多種族クリーチャー
（dm27-051 等が実在）では、カードごと除外すると
他の種族まで落ちて文面とずれる。not_race_has
（部分文字列・カード単位）での代用はしない。

結論: 新規語彙（最小）— 式 **distinct_race_count** の
値に構造化形 **{selector, exclude_races?}** を追加
（数えた種族名の集合から exclude_races を差し引く）。
素のセレクタ形（第405弾）はそのまま使える。追加箇所:
- dmsim/cards/defs.py: expr() の distinct_race_count
分岐で構造化形を受理（exclude_races は文字列の
リストのみ）
- dmsim/engine/selectors.py: 評価分岐で selector を
取り出し、集合から exclude_races を差し引く
- dmsim/cards/schema.py: expr の distinct_race_count を
anyOf [selector, {selector, exclude_races}] にし、
data/schema/card.schema.json を再生成
式の評価は Python 側のみ（distinct 系の既存2式と
同じ）。新規の状態フィールドは無いため state.rs
ミラーは不要で、rust_stamp は第364弾以来の先例どおり
据え置き（この環境では Python のみで動作）。

公式テキスト:
「このクリーチャーをバトルゾーンに出した時、
バトルゾーンにある自分の、ミステリー・トーテム
以外の種族１種類につき１枚、カードを引いてもよい。」
partial は骨格完備（クリーチャー / 自然 / コスト6 /
パワー4000 / 種族 ミステリー・トーテム、mana 1、
keywords・abilities ともに無し）で、未解決は
unsupported の distinct_race_count 1件だけ。
partial の text は断片（「種族１種類につき」）のため
**補完あり: text のみ**（公式全文を入れる）。alias は
dm14-010 / dmc42-015 / dmc57-015 / dmc61-010 の4件で、
いずれも rejects に独自行は無く、identity 実測で
canon_id は対象・全 alias とも dmx12b-058。
第406弾時点で real.yaml / real_akashic.yaml /
real_vocab.yaml / real_zone.yaml / proto.yaml /
converted.yaml のいずれにも登録なし。単面カードで
未検証の面は無い。

確立形:
- trigger {when: {event: move, to: bz, subject: self},
effect: [may {body: [draw {count:
{distinct_race_count:
{selector: {zone: bz, owner: you},
exclude_races: [ミステリー・トーテム]}}}]}]}
文面に「クリーチャー」の限定は無いため selector に
types フィルタは付けない（種族を持つタマシード等も
数える。第405弾の対象は文面が「相手のクリーチャーの
種族」のため types [creature] を付けたのと対照的）。

実挙動の判別（本弾で固定）: 自分だけ（種族は
ミステリー・トーテムのみ）では0枚。種族 テスト1種で
1枚、同種族2体でも1枚（種類数読み）。2種族獣で2枚。
多種族トーテム（ミステリー・トーテム＋アース・
ドラゴン）ではアース・ドラゴンが数えられ1枚
（種族名単位の除外の判別。カード単位の除外では
0枚になる）。種族を持つタマシードでも1枚
（クリーチャー限定なしの判別）。相手の種族は
数えない（owner: you）。may を断れば引かない。
混成（テスト＋2種族獣＋多種族トーテム）で4枚。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い。

プロト: T1173 = dmx12b-058 型、T1174 = 多種族
トーテム判別役（新規追加）。既存 proto の流用:
T001（単一種族役・自然マナ役）/ T787（2種族役＝
アンノウン＋ゼニス）/ T189（種族 テストを持つ
タマシード役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の
作法）。バトルゾーンは共有ゾーンなので所有は
bz_tops(p) / zlist(zone, p) で見る。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402

from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

EXPR = {"distinct_race_count":
        {"selector": {"zone": "bz", "owner": "you"},
         "exclude_races": ["ミステリー・トーテム"]}}
TRIGGER = {"kind": "trigger",
           "when": {"event": "move", "to": "bz", "subject": "self"},
           "effect": [{"op": "may", "body": [
               {"op": "draw", "count": EXPR}]}]}
FORM = [TRIGGER]
FULL_TEXT = ("このクリーチャーをバトルゾーンに出した時、"
             "バトルゾーンにある自分の、ミステリー・トーテム"
             "以外の種族１種類につき１枚、カードを引いてもよい。")
MANA = ["T001"] * 6   # 自然6（対象は自然コスト6）


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1173")
    assert c["name"] == "口寄の化身"
    assert c["types"] == ["creature"]
    assert c["civs"] == ["nature"]
    assert c["cost"] == 6 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ミステリー・トーテム"]
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(c, TABLES)
    assert d.abilities == FORM
    f = proto_card("T1174")
    assert f["races"] == ["ミステリー・トーテム", "アース・ドラゴン"]
    parse_card(f, TABLES)
    for tid in ("T001", "T787", "T189"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX406", "name": "x",
                    "types": ["creature"], "civs": ["nature"],
                    "cost": 6, "power": 4000, "mana": 1,
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert d.abilities == FORM


def test_plain_selector_form_still_parses():
    # 第405弾の素のセレクタ形は後方互換でそのまま使える
    plain = [{"kind": "static", "affects": "self",
              "mod": {"power": {"amount": 2000,
                                "count": {"distinct_race_count":
                                          {"zone": "bz", "owner": "opp",
                                           "filter": {"types": ["creature"]}}}}}}]
    d = parse_card({"id": "TX406b", "name": "x",
                    "types": ["creature"], "civs": ["light"],
                    "cost": 4, "power": 2000, "mana": 1,
                    "abilities": plain}, TABLES)
    assert d.abilities == plain


def _bad_with(expr):
    bad = copy.deepcopy(proto_card("T1173"))
    bad["abilities"][0]["effect"][0]["body"][0]["count"] = expr
    return bad


def test_structured_unknown_key_rejected():
    with pytest.raises(DefError):
        parse_card(_bad_with({"distinct_race_count":
                              {"selector": {"zone": "bz", "owner": "you"},
                               "bogus": 1}}), TABLES)


def test_exclude_races_not_a_list_rejected():
    with pytest.raises(DefError):
        parse_card(_bad_with({"distinct_race_count":
                              {"selector": {"zone": "bz", "owner": "you"},
                               "exclude_races": "ミステリー・トーテム"}}),
                   TABLES)


def test_exclude_races_non_string_rejected():
    with pytest.raises(DefError):
        parse_card(_bad_with({"distinct_race_count":
                              {"selector": {"zone": "bz", "owner": "you"},
                               "exclude_races": [1]}}), TABLES)


def test_exclude_races_without_selector_rejected():
    with pytest.raises(DefError):
        parse_card(_bad_with({"distinct_race_count":
                              {"exclude_races": ["ミステリー・トーテム"]}}),
                   TABLES)


def test_bad_selector_key_in_structured_rejected():
    with pytest.raises(DefError):
        parse_card(_bad_with({"distinct_race_count":
                              {"selector": {"zone": "bz", "owner": "you",
                                            "bogus": 1},
                               "exclude_races": ["ミステリー・トーテム"]}}),
                   TABLES)


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


def _summon(rules, bz0=(), bz1=(), may_yes=True):
    """p0 が T1173 を召喚し、CIP の may に答えて解決まで
    進める。（engine, 召喚したか, may が出たか）を返す。
    bz0 / bz1 は事前に置く判別役。"""
    e = _build(rules,
               {"hand": ["T1173"], "mana": MANA, "bz": list(bz0)},
               {"bz": list(bz1)})
    played = False
    may_seen = False
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and d.get("player") == 0 \
                and "play:T1173" in keys:
            played = True
            e.answer([keys.index("play:T1173")])
            continue
        if played and d["kind"] == "yes_no":
            may_seen = True
            e.answer([keys.index("yes" if may_yes else "no")])
            continue
        if played and d["kind"] in ("main", "charge", "attack"):
            break          # 解決が終わり次の通常判断に戻った
        e.answer(_boring(d))
    return e, played, may_seen


def _hand_count(e):
    return len(e.zlist("hand", 0))


def test_only_self_draws_zero(rules):
    # 自分の種族はミステリー・トーテムのみ → 除外され0枚
    e, played, may_seen = _summon(rules)
    assert played and may_seen
    assert _hand_count(e) == 0
    assert "T1173" in [e.cdef(c).id for c in e.zlist("bz", 0)]


def test_one_distinct_race_draws_one(rules):
    e, played, may_seen = _summon(rules, bz0=["T001"])
    assert played and may_seen
    assert _hand_count(e) == 1


def test_same_race_twice_draws_one(rules):
    # 同種族（テスト）が2体いても種類数は1 → 1枚
    e, played, may_seen = _summon(rules, bz0=["T001", "T001"])
    assert played and may_seen
    assert _hand_count(e) == 1


def test_two_race_creature_draws_two(rules):
    # T787 は2種族（アンノウン＋ゼニス）を持つ → 2枚
    e, played, may_seen = _summon(rules, bz0=["T787"])
    assert played and may_seen
    assert _hand_count(e) == 2


def test_multi_race_totem_other_race_counts(rules):
    # 種族名単位の除外の判別: ミステリー・トーテム＋
    # アース・ドラゴンの多種族獣は、アース・ドラゴンが
    # 数えられ1枚（カード単位の除外では0枚になる）
    e, played, may_seen = _summon(rules, bz0=["T1174"])
    assert played and may_seen
    assert _hand_count(e) == 1


def test_tamaseed_race_counts(rules):
    # クリーチャー限定なしの判別: 種族を持つタマシード
    # （T189、種族 テスト）でも1枚
    e, played, may_seen = _summon(rules, bz0=["T189"])
    assert played and may_seen
    assert _hand_count(e) == 1


def test_opponent_races_do_not_count(rules):
    # owner: you の判別: 相手の2種族獣は数えない
    e, played, may_seen = _summon(rules, bz1=["T787"])
    assert played and may_seen
    assert _hand_count(e) == 0


def test_decline_may_draws_nothing(rules):
    # 引いてもよい = may。断れば種族があっても引かない
    e, played, may_seen = _summon(rules, bz0=["T787"], may_yes=False)
    assert played and may_seen
    assert _hand_count(e) == 0


def test_mixed_board_draws_four(rules):
    # テスト（T001）＋アンノウン・ゼニス（T787）＋
    # アース・ドラゴン（T1174。MT は除外）= 4種 → 4枚
    e, played, may_seen = _summon(rules, bz0=["T001", "T787", "T1174"])
    assert played and may_seen
    assert _hand_count(e) == 4
