"""第3段・共通基盤その2a: 宣言プリミティブ（op choose_number / choose_name / choose_civ、
式 {declared:}、modify 生成時の式ベイク、mod の add_names）。

- 宣言の保存先は GameState.declares。後段は式 {declared: 名前} で読む（数・名前・文明）。
  未宣言の読みは 0（どの照合でも「一致しない」側に倒れる既定値）。
- filter の civs / not_civs / name は値に式を書けるようになり（FILTER_EXPR_KEYS）、
  式の結果が文明名の文字列なら単一文明として扱う。name / name_has / not_name は
  主名＋add_names の名前集合に当てる（name_of は主名のまま）。
- modify の生成時ベイク（基盤B4）: mod 内と dynamic の範囲フィルタ内の {declared:} /
  {var:} は生成時点の値へ固定する（特性計算・範囲照合は env を持たないため）。
  add_races（専用処理）と gain（能力そのもの）は対象外。
- choose_civ の player / exclude は統一の未確定事項のため実装していない（選ぶのは常に解決者）。
- proto: T247（数字宣言）／T248（文明宣言。プラトーン型）／T249（名前宣言）／
  T250（封唱宣言。dmart10-005 型）／T251（別名持ち。dm23ex1-039 型）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import DefError, load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _settle_to(e, kind, player=None, answers=None, max_steps=400):
    """指定の判断が来るまで進め、その判断を未回答で返す。answers は {kind: key} の固定回答。"""
    answers = answers or {}
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        if d["kind"] == kind and (player is None or d["player"] == player):
            return d
        keys = [o["key"] for o in d["options"]]
        if d["kind"] in answers:
            e.answer([keys.index(answers[d["kind"]])])
        elif d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        else:
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError(f"decision {kind} (player={player}) not reached")


def _cast(e, defn, answers=None):
    """P0 の main で defn を唱え、宣言などの判断に answers で答えながら解決しきる。
    解決の完了は「呪文が墓地に落ちた後、自分の main / attack 判断が来た」時点で判定する
    （相手ターンに進めるとアンタップ等で盤面が変わってしまうため）。"""
    answers = answers or {}
    d = _settle_to(e, "main", player=0, answers=answers)
    keys = [o["key"] for o in d["options"]]
    assert f"play:{defn}" in keys, f"play:{defn} not in {keys}"
    e.answer([keys.index(f"play:{defn}")])
    for _ in range(400):
        if any(e.s.cards[c].defn == defn for c in e.zlist("graveyard", 0)):
            return   # 解決が終わった（呪文は解決の最後に墓地へ落ちる）。ターンはまだ自分の番
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] in answers:
            e.answer([keys.index(answers[d["kind"]])])
        elif d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        else:
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("cast did not settle")


def test_proto_parse(rules):
    """T247〜T251 が parse でき、declared / add_names の検証が効く。"""
    for cid in ("T247", "T248", "T249", "T250", "T251"):
        parse_card(_proto_card(cid), TABLES)
    bad = _proto_card("T247")
    bad["spell"][1]["count"] = {"declared": 5}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    for bad_v in ("別名試験獣", [], [5]):
        bad = _proto_card("T251")
        bad["abilities"][0]["mod"] = {"add_names": bad_v}
        with pytest.raises(DefError):
            parse_card(bad, TABLES)


def test_choose_number_draws_declared(rules):
    """T247: 言った数だけ引く。0 と言えば引かない（宣言値がそのまま式に届く判別）。"""
    e = setup(rules, {"hand": ["T247"], "mana": ["T003", "T003"]}, {})
    _cast(e, "T247", answers={"choose_one": "num:2"})
    assert e.s.declares.get("n") == 2
    assert len(e.zlist("hand", 0)) == 2   # 呪文を唱えて 0 → 2 枚引く

    e = setup(rules, {"hand": ["T247"], "mana": ["T003", "T003"]}, {})
    _cast(e, "T247", answers={"choose_one": "num:0"})
    assert e.s.declares.get("n") == 0
    assert len(e.zlist("hand", 0)) == 0


def test_choose_civ_taps_others(rules):
    """T248: 選んだ文明でないクリーチャーをすべてタップする（filter の not_civs に宣言式）。
    選んだ文明のクリーチャーはタップされないことが判別条件。"""
    e = setup(rules, {"bz": ["T001", "T005"], "hand": ["T248"], "mana": ["T004", "T001", "T001"]},
              {"bz": ["T001"]})
    _cast(e, "T248", answers={"choose_civ": "civ:fire"})
    assert e.s.declares.get("c") == "fire"
    tapped = {c: e.s.cards[c].tapped for c in e.zlist("bz", 0) + e.zlist("bz", 1)}
    by_defn = {}
    for c, t in tapped.items():
        by_defn.setdefault(e.s.cards[c].defn, []).append(t)
    assert by_defn["T001"] == [True, True]   # 自然（自分と相手）はタップ
    assert by_defn["T005"] == [False]        # 火はタップされない


def test_choose_name_draws_when_present(rules):
    """T249: 言った名前のカードが自分の場にあれば引く。場に無い名前では引かない（判別）。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T249"], "mana": ["T003", "T003"]}, {})
    _cast(e, "T249", answers={"choose_name": "name:試験用ダミー"})
    assert e.s.declares.get("nm") == "試験用ダミー"
    assert len(e.zlist("hand", 0)) == 1   # 唱えて 0 → 条件成立で 1 枚引く

    e = setup(rules, {"bz": ["T001"], "hand": ["T249"], "mana": ["T003", "T003"]}, {})
    _cast(e, "T249", answers={"choose_name": "name:知識の泉"})   # マナにはあるが場には無い
    assert len(e.zlist("hand", 0)) == 0


def test_declare_bake_denies_that_cost(rules):
    """T250: 言ったコストの呪文だけが唱えられなくなる（modify の生成時ベイク＋dynamic 範囲ベイク）。
    ベイクが効かなければ宣言は範囲照合に届かず、コスト2も唱えられてしまう（判別）。"""
    e = setup(rules, {"hand": ["T250"], "mana": ["T008"] * 3},
              {"hand": ["T003", "T241"]})
    _cast(e, "T250", answers={"choose_one": "num:2"})
    assert e.s.declares.get("n") == 2
    t003 = next(c for c in e.zlist("hand", 1) if e.s.cards[c].defn == "T003")
    t241 = next(c for c in e.zlist("hand", 1) if e.s.cards[c].defn == "T241")
    assert not e.permits(t003, "cast")   # コスト2は封じられた
    assert e.permits(t241, "cast")       # コスト5は唱えられる

    e = setup(rules, {"hand": ["T250"], "mana": ["T008"] * 3},
              {"hand": ["T003", "T241"]})
    _cast(e, "T250", answers={"choose_one": "num:3"})   # 別の数字ならコスト2は封じられない
    t003 = next(c for c in e.zlist("hand", 1) if e.s.cards[c].defn == "T003")
    assert e.permits(t003, "cast")


def test_add_names(rules):
    """T251: 名前の集合に別名が入り、filter の name で引ける。主名（name_of）は変わらない。"""
    e = setup(rules, {"bz": ["T251"]}, {})
    cid = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T251")
    ch = e.chars(cid)
    assert ch["name"] == "別名持ち試験獣"
    assert ch["names"] == ["別名持ち試験獣", "別名試験獣"]
    assert e.filter_match(cid, {"name": "別名試験獣"})
    assert e.filter_match(cid, {"name": "別名持ち試験獣"})
    assert not e.filter_match(cid, {"not_name": "別名試験獣"})
    env = {"you": 0, "self": e.s.ref(cid), "vars": {}}
    assert e.eval_expr({"name_of": "self"}, env) == "別名持ち試験獣"
