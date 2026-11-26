"""語彙パイロット第389弾: mill_count_variable（ドリフト）。

センサス（rejects 1,944件を取り直し）: pure 1,796件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜388弾）は再提案しない。本弾で個別に
評価して見送った候補: shield_count_break（pure 1、
dm34-012。自分のシールド全墓地置き→置いた枚数分の
「相手が自身のクリーチャーを破壊する、できない場合
このクリーチャーが1枚ブレイク」の反復分岐で複合）、
turn_count_cost_reduction（pure 1、dmex14-054。
「召喚したクリーチャー1体または唱えた呪文1枚につき」
は summon と cast の合算カウントが要り、cost の
count 枠での合算式の意味論（召喚履歴の数え方含む）
の検証が本弾の対象より重い）、reveal_count_draw
（pure 1、dm29-010。好きな枚数の公開＋各プレイヤーの
任意ドローで複合）、draw_until_equal（pure 1、
dm24bd6-005。手札枚数の差分を引く式が無く、ツイン
パクト呪文面も未構築）、break_replacement_mill /
break_replacement_shield_charge（各 pure 1。
ブレイクする時／バトルに勝つ時の置換照合の確立形が
無い）、same_cost_bounce（pure 1、dm26sd1-q003。
公開カードと同コストのフィルタ参照に加え6枚見て
2枚加える等の複合条項が残る）。範囲内・未評価で最小の
mill_count_variable（pure 1件、multi にも現れない）を
選定した。

対象は pure 1件すべて: dmex10-014 死罠の杖
（闇/自然のクリーチャー、コスト4、パワー5000、
ビーストフォーク/不死樹王国）。partial は骨格のみ
（types / civs / cost / mana / power / races のみ、
abilities・keywords ともに無し）で、未解決は
unsupported の mill_count_variable 1件だけ。alias は
無い。単面カードで未検証の面は無い。条項「この
クリーチャーがバトルゾーンに出た時、相手の
クリーチャーを１体選び、持ち主のマナゾーンに置く。
そのクリーチャーのコストと同じ枚数のカードを、
自分の山札の上から墓地に置く」はすべて確立済みの
部品で表せる（追加語彙なし）:

- 「相手のクリーチャーを１体選び」は choose
  {select: {zone: bz, owner: opp, filter:
  {types: [creature]}, count: 1}, as: pick}
  （第368・385弾の choose 確立形。所有者は opp）。
- 「持ち主のマナゾーンに置く」は mana_put マクロ
  {select: {ref: pick}}（move {to: mana} への展開。
  登録先例多数）。置かれる側は選んだカードの
  持ち主＝相手のマナゾーンで、タップ状態は移動前の
  状態を引き継ぐ（エンジンの move 既定）。
- 「そのクリーチャーのコストと同じ枚数」は mill
  マクロの count に第368弾の一般式 {cost_of: pick}
  を渡す形。mill は move {select: {zone: deck,
  owner: $owner, from_top: $count}, to: graveyard}
  へ展開され、from_top は selectors が eval_expr で
  評価し schema.py でも ref("expr") と定義済み
  （第408ラウンドの教訓どおり両側を確認）。mill の
  count へ式を渡す登録先例は無く、本弾で実挙動を
  検証した（選んだカードのコストがマナゾーンへの
  移動後も cost_of で読めること、候補が無ければ
  cost_of は 0 で0枚＝第368・385弾と同じ読み）。

確立形: abilities = [trigger {when: {event: move,
to: bz, subject: self}, effect: [choose, mana_put,
mill]}] の1件。

partial の text は条項の断片（「そのクリーチャーの
コストと同じ枚数」）だけのため、提出形では text に
行の公式テキスト全文を入れる（補完あり。ラウンド424
への注意に明記）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い（本弾で
実測）。choose / mana_put / mill / cost_of / from_top
は defs の検証と schema.py の両方に定義済みである
ことを確認済み（スキーマ再生成不要・Rust ミラー
不要・rust_stamp への影響なし）。

proto T1154（dmex10-014 型）。判別役は既存 proto を
流用: T1110（水・コスト5。第368弾。相手のクリーチャー
役: 選ぶとミル5枚）/ T1109（水・コスト3。第368弾。
コスト3役: 2候補から選ぶとミル3枚になる判別）/
T127（闇・マナ用）/ T001（自然・マナ用）。対象は
闇/自然・コスト4のため召喚マナは闇2＋自然2にする
（多色の支払いには文明ごとに同文明マナが要る）。

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
           "effect": [
               {"op": "choose",
                "select": {"zone": "bz", "owner": "opp",
                           "filter": {"types": ["creature"]},
                           "count": 1},
                "as": "pick"},
               {"op": "mana_put", "select": {"ref": "pick"}},
               {"op": "mill", "owner": "you",
                "count": {"cost_of": "pick"}}]}
FORM = [TRIGGER]
# parse_card はマクロを展開するため、検証後の abilities は
# mana_put → move {to: mana, reason: put}、mill → move
# {from_top: {cost_of: pick}, to: graveyard, reason: put}
# の展開形になる（本弾で実測）
EXPANDED = [{"kind": "trigger",
             "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 TRIGGER["effect"][0],
                 {"op": "move", "select": {"ref": "pick"},
                  "to": "mana", "reason": "put"},
                 {"op": "move",
                  "select": {"zone": "deck", "owner": "you",
                             "from_top": {"cost_of": "pick"}},
                  "to": "graveyard", "reason": "put"}]}]
FULL_TEXT = ("このクリーチャーがバトルゾーンに出た時、相手の"
             "クリーチャーを１体選び、持ち主のマナゾーンに置く。"
             "そのクリーチャーのコストと同じ枚数のカードを、"
             "自分の山札の上から墓地に置く。")
MANA = ["T127"] * 2 + ["T001"] * 2   # 闇2＋自然2（多色の支払い）


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1154")
    assert c["name"] == "死罠の杖"
    assert c["types"] == ["creature"]
    assert c["civs"] == ["darkness", "nature"]
    assert c["cost"] == 4 and c["power"] == 5000 and c["mana"] == 1
    assert c["races"] == ["ビーストフォーク", "不死樹王国"]
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(c, TABLES)
    assert d.abilities == EXPANDED      # マクロ展開後の形
    for tid in ("T1109", "T1110", "T127", "T001"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX389", "name": "x",
                    "types": ["creature"], "civs": ["darkness", "nature"],
                    "cost": 4, "power": 5000, "mana": 1,
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert d.abilities == EXPANDED


def test_bad_forms_rejected(rules):
    # 未知の op 名は DefError（expand_ops の検証）
    bad = copy.deepcopy(proto_card("T1154"))
    bad["abilities"][0]["effect"][2] = {"op": "millx", "owner": "you",
                                        "count": 1}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # choose の select の未知キーは DefError
    bad2 = copy.deepcopy(proto_card("T1154"))
    bad2["abilities"][0]["effect"][0]["select"]["bogus"] = 1
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)
    # mill への未知の引数は展開先の move の検証で DefError
    bad3 = copy.deepcopy(proto_card("T1154"))
    bad3["abilities"][0]["effect"][2]["bogus"] = 1
    with pytest.raises(DefError):
        parse_card(bad3, TABLES)


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


def _summon(rules, p1, choose_defn=None):
    """p0 が T1154 を召喚し、CIP の choose に答えて解決まで
    進める。（engine, 召喚したか, choose 判断が出たか）を返す。"""
    e = _build(rules, {"hand": ["T1154"], "mana": MANA}, p1)
    played = False
    chose = False
    for _ in range(800):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not played and d["kind"] == "main" and d.get("player") == 0 \
                and "play:T1154" in keys:
            played = True
            e.answer([keys.index("play:T1154")])
            continue
        if played and d["kind"] == "choose_cards":
            chose = True
            idx = [i for i, o in enumerate(d["options"])
                   if choose_defn in o["key"]]
            assert idx, f"{choose_defn} が選択肢に無い: {keys}"
            e.answer(idx[:1])
            continue
        if played and d["kind"] in ("main", "charge", "attack"):
            break          # 解決が終わり次の通常判断に戻った
        e.answer(_boring(d))
    return e, played, chose


def _mana_defns(e, p):
    return [e.cdef(c).id for c in e.zlist("mana", p)]


def test_cost5_creature_to_mana_and_mill_five(rules):
    """相手のコスト5（T1110）を選ぶと、そのカードは持ち主
    （相手）のマナゾーンに置かれ、自分の山札の上から
    コストと同じ5枚が墓地に置かれる。"""
    e, played, chose = _summon(rules, {"bz": ["T1110"]}, "T1110")
    assert played
    assert chose is False           # 候補1体では選択判断が出ず自動で決まる
    assert _mana_defns(e, 1) == ["T1110"]       # 持ち主のマナへ
    moved = next(c for c in e.zlist("mana", 1)
                 if e.cdef(c).id == "T1110")
    assert e.s.cards[moved].tapped is False     # 状態は引き継ぐ
    assert len(e.zlist("graveyard", 0)) == 5    # コスト5 → 5枚ミル
    assert "T1154" in [e.cdef(c).id for c in e.zlist("bz", 0)]


def test_choose_cost3_among_two_mills_three(rules):
    """候補が2体（コスト3とコスト5）あれば、コスト3を
    選ぶとミルは3枚（cost_of はマナゾーンへ移動した後も
    束縛したカードのコストを読む判別）。残りのコスト5は
    バトルゾーンに留まる。"""
    e, played, chose = _summon(rules, {"bz": ["T1109", "T1110"]},
                               "T1109")
    assert played and chose
    assert _mana_defns(e, 1) == ["T1109"]
    assert len(e.zlist("graveyard", 0)) == 3
    opp_bz = [e.cdef(c).id for c in e.zlist("bz", 1)
              if e.s.cards[c].controller == 1]
    assert opp_bz == ["T1110"]


def test_no_target_resolves_without_mill(rules):
    """相手のクリーチャーが無ければ、選ぶ候補が無く
    ミルも0枚で解決は通常どおり終わる（cost_of は 0。
    第368・385弾と同じ読み）。"""
    e, played, chose = _summon(rules, {})
    assert played
    assert chose is False           # 選択判断自体が出ない
    assert len(e.zlist("graveyard", 0)) == 0
    assert "T1154" in [e.cdef(c).id for c in e.zlist("bz", 0)]
