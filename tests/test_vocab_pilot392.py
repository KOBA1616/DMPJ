"""語彙パイロット第392弾: civilization_breaker（ドリフト）。

対象は pure 1件すべて: dm27-010 彩強の巨人
（自然 / コスト9 / パワー11000 / ジャイアント）。
公式テキストは単一条項:
「文明ブレイカー(このクリーチャーは、自分のマナゾーンに
ある文明ひとつにつき１枚、シールドをブレイクする)」

既存部品の確認（すべて確立済みで、新規語彙・エンジン・
defs・スキーマ変更なし）:
- 「〜ひとつにつき１枚ブレイクする」は mod **breaks** の
  式形式 {civ_count: セレクタ}（第79弾）: 登録先例
  dmc34-025 は「バトルゾーンにある相手の文明ひとつに
  つき１枚、シールドを**追加で**ブレイクする」で、
  base 既定1の base＋式値になっている。
- 本弾の条項は「追加で」ではなく総数そのものなので、
  第145弾で実挙動検証済みの **base: 0**（バラエティ・
  ブレイカーの {distinct_cost_count: ..., base: 0} と
  同機構。core の集約は dict 形式すべて base＋値で、
  base: 0 でちょうど式の値になる）を組み合わせる。
  breaks の {civ_count ＋ base: 0} の組み合わせ自体は
  本弾が初の実挙動検証で、登録も初になる見込み
  （ラウンド427の回帰に data_audit を含めること）。
- civ_count は「対象カード群にある文明の種類数
  （多色はそれぞれ数える）」式（selectors の確立形）。
  セレクタ {zone: mana, owner: you} で自分のマナゾーン
  の文明種類数を数える。
- breaks / civ_count / base は defs の検証と schema.py
  の両方に定義済みであることを第408ラウンドの教訓
  どおり確認済み（schema.py の mod breaks は dict を
  許容。スキーマ再生成不要・Rust ミラー不要・
  rust_stamp への影響なし）。文明ブレイカーは
  keywords.yaml にキーワード定義が無く、クルー・
  ブレイカー（第130弾）等と同じく static mod で表す。

確立形: abilities = [static {affects: self, mod:
{breaks: {civ_count: {zone: mana, owner: you},
base: 0}}}] の1件。keywords は無し。

partial は骨格完備（クリーチャー / 自然 / コスト9 /
パワー11000 / 種族 ジャイアント、mana 1、keywords・
abilities 無し）と unsupported の civilization_breaker
1件だけ。text は「文明ブレイカー」だけのため、提出形
では text に行の公式テキスト全文を入れる（補完あり。
ラウンド427への注意に明記）。alias は無い。単面
カードで未検証の面は無い。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い
（第392弾で実測）。

proto: T1159（dm27-010 型）。判別役は既存 proto を
流用: マナ役 T001（自然）/ T004（光）/ T005（火）/
T008（闇）/ T009（水）/ T030（光・水の多色）。

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
    {"kind": "static", "affects": "self",
     "mod": {"breaks": {"civ_count": {"zone": "mana", "owner": "you"},
                        "base": 0}}},
]
FULL_TEXT = ("文明ブレイカー(このクリーチャーは、自分のマナゾーンにある"
             "文明ひとつにつき１枚、シールドをブレイクする)")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1159")
    assert c["name"] == "彩強の巨人"
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 9 and c["power"] == 11000 and c["mana"] == 1
    assert c["races"] == ["ジャイアント"]
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 1
    assert d.abilities[0]["kind"] == "static"
    assert d.abilities[0]["mod"] == {"breaks": {
        "civ_count": {"zone": "mana", "owner": "you"}, "base": 0}}


def test_bad_forms_rejected(rules):
    base = copy.deepcopy(proto_card("T1159"))
    # base は 0 以上の int のみ（負値は DefError）
    bad = copy.deepcopy(base)
    bad["abilities"][0]["mod"]["breaks"] = {
        "civ_count": {"zone": "mana", "owner": "you"}, "base": -1}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # 式形式は civ_count / distinct_cost_count 単独のみ
    # （未知キーの混入は DefError）
    bad2 = copy.deepcopy(base)
    bad2["abilities"][0]["mod"]["breaks"] = {
        "civ_count": {"zone": "mana", "owner": "you"}, "bogus": 1}
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)
    # count 形式と式形式の混在は DefError
    bad3 = copy.deepcopy(base)
    bad3["abilities"][0]["mod"]["breaks"] = {
        "count": {"zone": "mana", "owner": "you"},
        "civ_count": {"zone": "mana", "owner": "you"}}
    with pytest.raises(DefError):
        parse_card(bad3, TABLES)
    # 未知の mod キーは DefError
    bad4 = copy.deepcopy(base)
    bad4["abilities"][0]["mod"] = {
        "breaks": {"civ_count": {"zone": "mana", "owner": "you"},
                   "base": 0},
        "breakz": 1}
    with pytest.raises(DefError):
        parse_card(bad4, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn, n=0):
    return [c for c in e.zlist("bz", p)
            if e.s.cards[c].defn == defn][n]


def _breaks(e, p, defn, n=0):
    ch = e.chars(_cid(e, p, defn, n))
    return ch["breaks"], ch["break_opts"]


def test_breaks_civ_count_chars(rules):
    # マナが無ければ文明0種 → ブレイク選択肢は [0]
    # （base: 0 の判別: 既定 base 1 なら [1] になる）。
    # chars の breaks は集約テンプレートの既定1との max
    # 要約値で、実際に使う数は攻撃時に break_opts から
    # 選ぶ（509.2b/509.2c。combat の counts は break_opts
    # 由来）。実挙動は test_attack_breaks_zero で固定する
    e = _build(rules, {"bz": ["T1159"]}, {})
    assert _breaks(e, 0, "T1159") == (1, [0])
    # 自然1種 → 1枚
    e = _build(rules, {"bz": ["T1159"], "mana": ["T001"]}, {})
    assert _breaks(e, 0, "T1159") == (1, [1])
    # 同じ文明2枚でも種類数は1 → 1枚
    e = _build(rules, {"bz": ["T1159"], "mana": ["T001", "T001"]}, {})
    assert _breaks(e, 0, "T1159") == (1, [1])
    # 自然＋火の2種 → 2枚
    e = _build(rules, {"bz": ["T1159"], "mana": ["T001", "T005"]}, {})
    assert _breaks(e, 0, "T1159") == (2, [2])
    # 多色1枚（光・水）はそれぞれ数えて2種 → 2枚
    e = _build(rules, {"bz": ["T1159"], "mana": ["T030"]}, {})
    assert _breaks(e, 0, "T1159") == (2, [2])
    # 5文明すべて → 5枚
    e = _build(rules, {"bz": ["T1159"],
                       "mana": ["T001", "T004", "T005", "T008", "T009"]}, {})
    assert _breaks(e, 0, "T1159") == (5, [5])


def test_breaks_counts_only_own_mana(rules):
    # owner: you の判別: 相手のマナの文明は数えない
    e = _build(rules, {"bz": ["T1159"], "mana": ["T001"]},
               {"mana": ["T004", "T005", "T008"]})
    assert _breaks(e, 0, "T1159") == (1, [1])
    # zone: mana の判別: バトルゾーンの文明は数えない
    # （dmc34-025 の bz 数えとの対比）
    e = _build(rules, {"bz": ["T1159", "T005", "T008"],
                       "mana": ["T001"]}, {})
    assert _breaks(e, 0, "T1159") == (1, [1])


def _drive_attack(e, attacker):
    """p0 の attacker でプレイヤーを攻撃し、攻撃した
    ターンの2つ先のターンまで進める（第383弾の作法）。"""
    state = {"attacked": False, "attack_turn": None}
    for _ in range(1500):
        if state["attacked"] and e.s.turn >= state["attack_turn"] + 2:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack":
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and not state["attacked"]:
                state["attacked"] = True
                state["attack_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return state


def test_attack_breaks_civ_count_shields(rules):
    # マナ3種（自然・火・闇）: 実際にシールドを3枚
    # ブレイクする（5→2）
    e = _build(rules, {"bz": ["T1159"],
                       "mana": ["T001", "T005", "T008"]}, {})
    st = _drive_attack(e, "T1159")
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 2
    # マナ1種（自然のみ）: 1枚だけブレイクする（5→4）
    e = _build(rules, {"bz": ["T1159"], "mana": ["T001"]}, {})
    st = _drive_attack(e, "T1159")
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 4


def test_attack_breaks_zero_without_mana_civs(rules):
    # マナに文明が無ければ（マナゾーンが空）ブレイクは
    # 0枚: 攻撃してもシールドは減らない（5→5）。
    # break_opts [0] が実際に解決へ届くことの固定
    e = _build(rules, {"bz": ["T1159"]}, {})
    st = _drive_attack(e, "T1159")
    assert st["attacked"]
    assert len(e.zlist("shield", 1)) == 5
