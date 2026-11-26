"""語彙パイロット第419弾: turn_count_cost_reduction（ドリフト）。

対象は pure 1件すべて: dmex14-054 捧程者 アコギエレキ
（火 / コスト5 / パワー5000 / 種族 ムートピア、美孔麗王国）。
公式テキスト:
「このターンに自分が召喚したクリーチャー１体または
唱えた呪文１枚につき、このクリーチャーの召喚コストを
２少なくする。ただし、コストは０以下にはならない。
スピードアタッカー（このクリーチャーは召喚酔いしない）」

行の注記は「ターンの行動回数による軽減を表す語彙が無い」
だが、これは turn_count 基盤（第159・214・382・387弾）より
前の評価で、決定的な登録先例がある: 登録済み
dm24ex3-rp2003 深淵の瘴炉 インシネ＝ロウ /
dm24ex3-rp2004 ネオ・アルティメット・ドラゴンは同文型を
static {kind: static, zone: hand, affects: self,
mod: {cost: {amount: -2, count: {sum: [{turn_count:
{kind: untap_creature, owner: you}}, {turn_count:
{kind: untap_creature, owner: opp}}]}, cost_min: 1}}}
で登録済み。本件は2つの turn_count の kind を
summon / cast（いずれも文面どおり owner: you）に
差し替えただけの完全なドリフト（新規語彙・エンジン・
defs・スキーマ変更すべてなし）。

部品の裏付け（実測）:
- TURN_COUNT_KINDS に summon / cast の両方がある。
- 記録側: events._record_history は summon レコード
  （reason: summon の bz 参入からのみ生成）で
  hist:summon を、cast レコードで hist:cast を数える。
  効果による「出す」は enter として別に数えられ、
  summon には入らない（文面の「召喚した」と一致。
  実挙動でも T538 の復活で判別する）。
- 式の sum は selectors の eval_expr が要素の和として
  評価し、defs の count_spec は sum / turn_count の
  両方を式として受理する。schema.py 側も sum（expr の
  配列）と turn_count（kind は文字列）を既に定義して
  おり、第408ラウンド型の未同期は無い。
- 下限は「0以下にはならない」＝ cost_min: 1
  （rp2003 / rp2004、第415弾の dm24ex1-087 /
  dm24bd2-016 の先例どおり）。

partial は骨格＋keywords [speed_attacker] まで構築済みで
text は公式全文（補完なし）。提出形は static 1件を足す
だけ。alias は無し（identity 実測で canon は対象自身、
aliases_for = []）。単面カードで未検証の面は無い。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は ([speed_attacker], 軽減条項の
テキスト, []) を返し、定型所有はキーワードのみで
part[2] の能力所有は空＝二重付着ブロッカー無し。

proto: T1190（dmex14-054 型）。判別役は既存 proto を
流用: T277（火・コスト2バニラ＝召喚役／マナ役）/
T962（火・コスト2ドロー呪文＝詠唱役）/ T538（火・
コスト2復活呪文＝「出す」は召喚でないことの判別役）。

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

FORM = [{"kind": "static", "zone": "hand", "affects": "self",
         "mod": {"cost": {"amount": -2,
                          "count": {"sum": [
                              {"turn_count": {"kind": "summon",
                                              "owner": "you"}},
                              {"turn_count": {"kind": "cast",
                                              "owner": "you"}}]}},
                 "cost_min": 1}}]
FULL_TEXT = ("このターンに自分が召喚したクリーチャー１体または唱えた"
             "呪文１枚につき、このクリーチャーの召喚コストを２少なく"
             "する。ただし、コストは０以下にはならない。\n"
             "スピードアタッカー（このクリーチャーは召喚酔いしない）")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1190")
    assert c["name"] == "捧程者 アコギエレキ"
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 5 and c["power"] == 5000 and c["mana"] == 1
    assert c["races"] == ["ムートピア", "美孔麗王国"]
    assert c["keywords"] == ["speed_attacker"]
    assert c["text"] == FULL_TEXT
    assert c["abilities"] == FORM
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 2   # static 1件＋キーワード展開1件


def _static_with(count):
    return [{"kind": "static", "zone": "hand", "affects": "self",
             "mod": {"cost": {"amount": -2, "count": count},
                     "cost_min": 1}}]


def test_validation(rules):
    base = copy.deepcopy(proto_card("T1190"))
    base["abilities"] = copy.deepcopy(FORM)
    parse_card(base, TABLES)
    # 未知の kind は DefError
    bad = copy.deepcopy(base)
    bad["abilities"] = _static_with({"sum": [
        {"turn_count": {"kind": "bogus", "owner": "you"}},
        {"turn_count": {"kind": "cast", "owner": "you"}}]})
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    # kind の欠落は DefError
    bad2 = copy.deepcopy(base)
    bad2["abilities"] = _static_with({"sum": [
        {"turn_count": {"owner": "you"}},
        {"turn_count": {"kind": "cast", "owner": "you"}}]})
    with pytest.raises(DefError):
        parse_card(bad2, TABLES)
    # turn_count の未知キーは DefError
    bad3 = copy.deepcopy(base)
    bad3["abilities"] = _static_with({"sum": [
        {"turn_count": {"kind": "summon", "owner": "you", "bogus": 1}},
        {"turn_count": {"kind": "cast", "owner": "you"}}]})
    with pytest.raises(DefError):
        parse_card(bad3, TABLES)
    # sum の要素の未知の式キーは DefError
    bad4 = copy.deepcopy(base)
    bad4["abilities"] = _static_with({"sum": [
        {"bogus_expr": {"kind": "summon"}},
        {"turn_count": {"kind": "cast", "owner": "you"}}]})
    with pytest.raises(DefError):
        parse_card(bad4, TABLES)
    # owner の不正値は DefError
    bad5 = copy.deepcopy(base)
    bad5["abilities"] = _static_with({"sum": [
        {"turn_count": {"kind": "summon", "owner": "bogus"}},
        {"turn_count": {"kind": "cast", "owner": "you"}}]})
    with pytest.raises(DefError):
        parse_card(bad5, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _answer_default(e, d):
    keys = _keys(d)
    if d["kind"] == "yes_no":
        e.answer([keys.index("yes")] if "yes" in keys
                 else list(range(d["min"])))
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d["min"])))


def _hand_cid(e, player=0, defn="T1190"):
    return next(c for c in e.zlist("hand", player)
                if e.s.cards[c].defn == defn)


def _pay(e, player=0):
    return e.chars_ro(_hand_cid(e, player))["pay_cost"]


def _tapped_mana(e, p):
    return sum(1 for c in e.zlist("mana", p) if e.s.cards[c].tapped)


def _main(e, player, play=None):
    """player の main まで進める。play があればその key を
    選んで解決し、次の main まで進めてから選択肢キーを返す。"""
    for _ in range(900):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == player:
            if play is not None:
                assert play in keys, f"{play} not in {keys}"
                e.answer([keys.index(play)])
                play = None
                continue
            return keys
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        _answer_default(e, d)
    raise AssertionError("main not reached")


def _settle(e, done):
    """done() になるまで受動的に進める（第412弾の作法）。"""
    for _ in range(600):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        _answer_default(e, d)
    return done()


def test_pay_cost_progression_and_floor(rules):
    # 素のコスト5 → 召喚1回で3 → 詠唱1回で1（合計2件×-2）
    # → さらに召喚1回（合計3件）でも下限1で止まる
    # （cost_min が無ければ 5-6 で 0 になる判別）。
    # 最後に軽減後の1コストで実際に召喚できることも確認する。
    e = _build(rules,
               {"hand": ["T1190", "T277", "T277", "T962"],
                "mana": ["T277"] * 10},
               {})
    _main(e, 0)
    assert _pay(e) == 5
    assert e.s.turn_counters.get("hist:summon:0", 0) == 0
    assert e.s.turn_counters.get("hist:cast:0", 0) == 0
    _main(e, 0, play="play:T277")
    assert e.s.turn_counters.get("hist:summon:0", 0) == 1
    assert _pay(e) == 3
    _main(e, 0, play="play:T962")
    assert e.s.turn_counters.get("hist:cast:0", 0) == 1
    assert _pay(e) == 1
    _main(e, 0, play="play:T277")
    assert e.s.turn_counters.get("hist:summon:0", 0) == 2
    assert _pay(e) == 1          # 合計3件×-2=6 → 下限1
    tapped_before = _tapped_mana(e, 0)
    keys = _main(e, 0)
    assert "play:T1190" in keys
    e.answer([keys.index("play:T1190")])
    assert _settle(e, lambda: any(e.s.cards[c].defn == "T1190"
                                  for c in e.zlist("bz", 0)))
    assert _tapped_mana(e, 0) == tapped_before + 1   # 支払いは1だけ


def test_put_is_not_summon(rules):
    # 効果で墓地から「出す」（reason: put）は召喚ではない:
    # T538 の復活では詠唱ぶん（-2）だけが数えられ、
    # 出したクリーチャーぶんは数えられない（5→3。
    # enter を summon と数える読みなら 5-4=1 になる判別）。
    e = _build(rules,
               {"hand": ["T1190", "T538"], "graveyard": ["T277"],
                "mana": ["T277"] * 6},
               {})
    _main(e, 0)
    assert _pay(e) == 5
    _main(e, 0, play="play:T538")
    assert any(e.s.cards[c].defn == "T277" for c in e.zlist("bz", 0))
    assert e.s.turn_counters.get("hist:cast:0", 0) == 1
    assert e.s.turn_counters.get("hist:summon:0", 0) == 0
    assert _pay(e) == 3


def test_opponent_actions_do_not_count(rules):
    # 相手の召喚は owner: you の数えに入らない:
    # 相手が1体召喚した後でも自分の T1190 は素のコスト5
    # （owner: any の読みなら 3 になる判別）。
    # 履歴カウンタはターン跨ぎで prev_counters へ移るため、
    # 召喚が解決した直後の盤面で読む。
    e = _build(rules,
               {"hand": ["T1190"], "mana": ["T277"] * 3},
               {"hand": ["T277"], "mana": ["T277"] * 3})
    keys = _main(e, 1)
    assert "play:T277" in keys
    e.answer([keys.index("play:T277")])
    assert _settle(e, lambda: any(e.s.cards[c].defn == "T277"
                                  for c in e.zlist("bz", 1)))
    recorded = (e.s.turn_counters.get("hist:summon:1", 0)
                + e.s.prev_counters.get("hist:summon:1", 0))
    assert recorded == 1                     # 相手の召喚は記録された
    assert e.s.turn_counters.get("hist:summon:0", 0) == 0
    assert e.s.prev_counters.get("hist:summon:0", 0) == 0
    assert _pay(e, 0) == 5
