"""語彙パイロット第421弾: move_to_deck_bottom_trigger（ドリフト）。

対象は dmex04-025 ヤッタレ総長（火 / コスト3 / パワー3000 /
種族 ジョーカーズ）。公式テキスト:
「自分のコスト７以上のジョーカーズを召喚するコストを１少なく
してもよい。ただし、コストは０以下にならない。
バトルゾーンにあるカードを１枚、自分の山札の一番下に置いた時、
カードを１枚引く。」

行の注記は「『山札の一番下に置いた時』は when で置き場所
（上／下）を区別できないため、その条項のみ unsupported」と
していたが、これは第290弾より前の陳腐化した評価である。
第290弾で when の position 照合（move レコードへの position
伝播・defs 検証・_match_when 照合・schema.py の when
プロパティ＋スキーマ再生成）が実装され、登録済み
dmrp06-001 の形Dが trigger {when: {event: move, to: deck,
position: bottom, subject: {owner: you}, cause: {by: opp,
kind: [spell, ability]}}, effect: [may [draw 1]]} として
「一番下に置かれた時」の監視誘発を登録済み。本件の第2条項は
同形から cause を外し（文面に原因の限定なし）、文面どおり
from: bz を足し、ドローは必須（「てもよい」が無い）とした
形: trigger {when: {event: move, from: bz, to: deck,
position: bottom, subject: {owner: you}}, effect:
[draw {count: 1}]}。能動態「置いた時」の読みは第418弾の
先例（登録済み dm24bd5-033 が同型の能動態文面を cause
無し・subject {owner: you} で登録）に従う。

公式 QA の裏付け:
- QA 32439（2019.9.30）: 《ヤッタレ総長》自身がバトル
  ゾーンから山札の一番下に置かれた時もカードを1枚引ける
  → 発生源自身の移動でも誘発が立つ（lki 発生源経路）。
- QA 31661（2019.7.2）: 下にカードが2枚ある進化
  クリーチャー（計3枚）を一番下に置くと3枚引く
  → 置かれたカード1枚ごとの move レコードで数える。
  本弾では「自分の獣2体を一度に一番下」で2枚引くことを
  同じ機構（カードごとのレコード＋発生源が場に残る間の
  収集）で固定する。

第1条項は partial 構築済みの static {affects: {owner: you,
zone: hand, filter: {types: [creature], race_has:
ジョーカーズ, cost_ge: 7}}, mod: {cost_may: {amount: 1,
min: 1}}}（cost_may は登録先例のある既存キー）。

partial は骨格＋第1条項まで構築済みで text は公式全文
（補完なし）。alias は dmex02-041 / dmrp04s-050 /
promoy16-087 の3件（rejects に独自行なし、canon は
対象自身）。登録ブロッカーの確認（第375弾の教訓）:
rule_convert.split（対象行）は None を返し定型所有は
無い＝ツール側ブロッカーなし。

proto: T1192（dmex04-025 型）＋ T1193（墓地から一番下
＝from 判別役）＋ T1194（自分の獣2体を一度に一番下
＝枚数判別役）。既存 proto の流用: T844（自分の呪文で
自分の獣を一番下へ＝駆動役）/ T842（相手の呪文で一番上へ
＝位置の対照役）/ T841（相手の呪文で自分の獣を一番下へ
＝原因の判別役）/ T1185（コスト7ジョーカーズ＝第1条項の
対象役）/ T001（自然バニラ＝移動対象役）/ T008（闇マナ役）/
T009（水マナ役）。

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
    {"kind": "static",
     "affects": {"owner": "you", "zone": "hand",
                 "filter": {"types": ["creature"],
                            "race_has": "ジョーカーズ", "cost_ge": 7}},
     "mod": {"cost_may": {"amount": 1, "min": 1}}},
    {"kind": "trigger",
     "when": {"event": "move", "from": "bz", "to": "deck",
              "position": "bottom", "subject": {"owner": "you"}},
     "effect": [{"op": "draw", "count": 1}]},
]
FULL_TEXT = ("自分のコスト７以上のジョーカーズを召喚するコストを"
             "１少なくしてもよい。ただし、コストは０以下にならない。\n"
             "バトルゾーンにあるカードを１枚、自分の山札の一番下に"
             "置いた時、カードを１枚引く。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1192")
    assert c["name"] == "ヤッタレ総長"
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 3 and c["power"] == 3000 and c["mana"] == 1
    assert c["races"] == ["ジョーカーズ"]
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(copy.deepcopy(c), TABLES)
    for ab in FORM:
        assert ab in d.abilities
    for tid in ("T1193", "T1194", "T844", "T842", "T841", "T1185",
                "T001", "T008", "T009"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX421", "name": "x",
                    "types": ["creature"], "civs": ["fire"],
                    "cost": 3, "power": 3000, "mana": 1,
                    "races": ["ジョーカーズ"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    for ab in FORM:
        assert ab in d.abilities


def test_bad_forms_rejected(rules):
    base = proto_card("T1192")
    # position の未知値は DefError（第290弾の検証）
    bad = copy.deepcopy(base)
    bad["abilities"][1]["when"]["position"] = "middle"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # when の未知の from ゾーンは DefError
    bad2 = copy.deepcopy(base)
    bad2["abilities"][1]["when"]["from"] = "bogus"
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)
    # effect の未知 op は DefError
    bad3 = copy.deepcopy(base)
    bad3["abilities"][1]["effect"] = [{"op": "draww", "count": 1}]
    with pytest.raises(DefError):
        parse_card(bad3, TABLES)
    # 第1条項フィルタの未知キーは DefError
    bad4 = copy.deepcopy(base)
    bad4["abilities"][0]["affects"]["filter"]["bogus"] = 1
    with pytest.raises(DefError):
        parse_card(bad4, TABLES)
    # when の未知イベントは DefError
    bad5 = copy.deepcopy(base)
    bad5["abilities"][1]["when"] = {
        "event": "enter", "from": "bz", "to": "deck",
        "position": "bottom", "subject": {"owner": "you"}}
    with pytest.raises(DefError):
        parse_card(bad5, TABLES)


# ---------- 駆動ヘルパ ----------

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


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _counts(e):
    return (len(e.zlist("hand", 0)), len(e.zlist("deck", 0)),
            len(e.zlist("bz", 0)))


def _resolve_cast(e, caster, spell, choose=None):
    """caster の main で spell を唱え、解決（誘発の解決を含む）が
    終わって相手の charge 決定が現れた時点までの p0 の
    (手札, 山札, バトルゾーン) 枚数を (唱える前, 解決後) で返す。
    choose は choose_cards 決定への回答インデックス列を返す関数。"""
    st = {}
    for _ in range(6000):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if not st.get("cast"):
            if d["kind"] == "main" and d.get("player") == caster \
                    and f"play:{spell}" in keys:
                st["before"] = _counts(e)
                st["cast"] = True
                e.answer([keys.index(f"play:{spell}")])
            else:
                _answer_default(e, d)
            continue
        if d["kind"] == "charge" and d.get("player") == 1 - caster:
            st["after"] = _counts(e)
            return st["before"], st["after"]
        if d["kind"] == "choose_cards" and choose is not None:
            e.answer(choose(keys))
            continue
        _answer_default(e, d)
    raise AssertionError(f"cast not resolved: {st}")


MANA_D = ["T008"] * 5   # 闇マナ役（T844 / T1193 の支払い用）
MANA_W = ["T009"] * 5   # 水マナ役（T841 / T842 / T1194 の支払い用）


def test_own_spell_bottom_draws(rules):
    # 第2条項: 自分の呪文で自分の獣を山札の一番下に置くと
    # 1枚引く（呪文消費 -1 と相殺され手札は不変、山札は
    # 置かれたカード +1 とドロー -1 で不変）。
    e = _build(rules,
               {"bz": ["T1192", "T001"], "hand": ["T844"],
                "mana": MANA_D},
               {"bz": []})
    before, after = _resolve_cast(e, 0, "T844")
    assert before == (1, 15, 2)
    assert after == (1, 15, 1)


def test_self_bottom_draws(rules):
    # 公式 QA 32439: 発生源自身が一番下に置かれた時も引ける
    # （lki 発生源経路で誘発が立つ）。
    e = _build(rules,
               {"bz": ["T1192"], "hand": ["T844"], "mana": MANA_D},
               {"bz": []})
    before, after = _resolve_cast(e, 0, "T844")
    assert before == (1, 15, 1)
    assert after == (1, 15, 0)


def test_top_does_not_draw(rules):
    # 対照: 一番「上」に置いた時は引けない（position の判別）。
    # 解決後は相手ターンが終わり自分の charge で測るため、
    # 手札はターンドロー +1、山札はターンドロー -1 と
    # 一番上に置かれたカード +1 で相殺される。
    e = _build(rules,
               {"bz": ["T1192", "T001"], "mana": MANA_D},
               {"bz": [], "hand": ["T842"], "mana": MANA_W})
    before, after = _resolve_cast(e, 1, "T842")
    assert before == (0, 15, 2)
    assert after == (1, 15, 1)


def test_graveyard_bottom_does_not_draw(rules):
    # 対照: 墓地から一番下に置いた時は引けない
    # （from: bz の判別）。手札は呪文消費のみ、山札は
    # 置かれたカード +1。
    e = _build(rules,
               {"bz": ["T1192"], "graveyard": ["T001"],
                "hand": ["T1193"], "mana": MANA_D},
               {"bz": []})
    before, after = _resolve_cast(e, 0, "T1193")
    assert before == (1, 15, 1)
    assert after == (0, 16, 1)


def test_opponent_own_bottom_does_not_draw(rules):
    # 対照: 相手が自分の獣を自分の山札の一番下に置いても
    # 引けない（subject owner: you の判別）。解決後は
    # 自分の charge で測るため手札はターンドロー +1、
    # 山札はターンドロー -1 のみ。バトルゾーンは共有
    # ゾーンのため、3つ目の数字は両者の合計。
    e = _build(rules,
               {"bz": ["T1192"], "mana": MANA_D},
               {"bz": ["T001"], "hand": ["T844"], "mana": MANA_D})
    before, after = _resolve_cast(e, 1, "T844")
    assert before == (0, 15, 2)
    assert after == (1, 14, 1)


def test_opponent_spell_bottom_draws(rules):
    # 原因の判別: 文面に原因の限定は無いため、相手の呪文で
    # 自分の獣が一番下に置かれた時も引く（cause 無し、
    # 第418弾の能動態の読み）。解決後は自分の charge で
    # 測るため、手札はターンドロー +1 と誘発ドロー +1、
    # 山札はターンドロー -1・置かれたカード +1・
    # 誘発ドロー -1。
    e = _build(rules,
               {"bz": ["T1192", "T001"], "mana": MANA_D},
               {"bz": [], "hand": ["T841"], "mana": MANA_W})
    before, after = _resolve_cast(e, 1, "T841")
    assert before == (0, 15, 2)
    assert after == (2, 14, 1)


def test_two_cards_two_draws(rules):
    # 枚数の判別（公式 QA 31661 と同じ機構）: 自分の獣
    # 2体を一度に一番下に置くと、置かれたカード1枚
    # ごとに誘発が立ち2枚引く。発生源は場に残す。
    e = _build(rules,
               {"bz": ["T1192", "T001", "T001"], "hand": ["T1194"],
                "mana": MANA_W},
               {"bz": []})
    before, after = _resolve_cast(
        e, 0, "T1194",
        choose=lambda keys: [i for i, k in enumerate(keys)
                             if "T001" in k])
    assert before == (1, 15, 3)
    assert after == (2, 15, 1)


def test_clause1_cost_may_reduction(rules):
    # 第1条項: 発生源がいれば、コスト7のジョーカーズを
    # マナ6枚（1軽減）で召喚できる。支払い時に reduce /
    # normal の選択肢が出て、reduce を選ぶと6枚タップ。
    e = _build(rules,
               {"bz": ["T1192"], "hand": ["T1185"],
                "mana": ["T001"] * 6},
               {"bz": []})
    st = {}
    for _ in range(6000):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and not st.get("played"):
            assert "play:T1185" in keys, keys
            st["played"] = True
            e.answer([keys.index("play:T1185")])
            continue
        if st.get("played") and d["kind"] == "choose_cards" \
                and "reduce" in keys:
            st["reduce_offered"] = True
            e.answer([keys.index("reduce")])
            continue
        if st.get("played") and any(
                e.s.cards[c].defn == "T1185"
                for c in e.zlist("bz", 0)):
            tapped = sum(1 for c in e.zlist("mana", 0)
                         if e.s.cards[c].tapped)
            assert st.get("reduce_offered") is True
            assert tapped == 6
            return
        _answer_default(e, d)
    raise AssertionError(f"summon not finished: {st}")


def test_clause1_no_source_no_reduction(rules):
    # 対照: 発生源がいなければ、コスト7はマナ6枚では
    # 召喚できない（main の選択肢に出ない）。
    e = _build(rules,
               {"bz": [], "hand": ["T1185"], "mana": ["T001"] * 6},
               {"bz": []})
    for _ in range(6000):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if d["kind"] == "main" and d.get("player") == 0:
            assert "play:T1185" not in _keys(d)
            return
        _answer_default(e, d)
    raise AssertionError("main not reached")
