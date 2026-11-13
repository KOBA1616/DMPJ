"""語彙パイロット第163弾: reveal_until（「〜が出るまで表向きにする」）。

新 op reveal_until: 対象プレイヤー（player。既定 you。player_from = 変数名なら
その最初のカードの持ち主）の山札を上から1枚ずつ公開し、filter に合うカードが
count 枚（既定1）出た時点で止める。合ったカード群を as に、出なかった公開
カード群を rest_as（既定 as + "_rest"）に束縛する。公開したカードは山札に
残るので、行き先は後続の op が決める（move で出す／墓地に置く／山札の下に
置く、shuffle で山札に戻す）。count は式（{var: 破壊した変数} で動的な数）。
相対条件は filter の式値（cost_le: {sum: [{cost_of: {ref: d}}, -1]} など）。
併せて shuffle に player_from を、move の order に shuffle を追加した
（「その持ち主は山札をシャッフルする」「残りをシャッフルし、山札の下に置く」）。
"""
from pathlib import Path

import yaml
from conftest import setup, answer

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    for cid in ("T298", "T299", "T300", "T301"):
        parse_card(_proto_card(cid), TABLES)
    t298 = parse_card(_proto_card("T298"), TABLES)
    op0 = t298.abilities[0]["effect"][0]
    assert op0["op"] == "reveal_until" and op0["as"] == "hit" and op0["rest_as"] == "rest"
    t300 = parse_card(_proto_card("T300"), TABLES)
    assert t300.spell[2]["player_from"] == "d" and t300.spell[4]["player_from"] == "d"


def test_invalid_reveal_until():
    base = {"id": "test-ru-bad", "name": "試験公開不良", "types": ["spell"],
            "civs": ["water"], "cost": 3,
            "source": {"official": "test-ru-bad", "review": "pending"}}
    for bad in ({"op": "reveal_until", "as": "hit"},   # filter が無い
                {"op": "reveal_until", "filter": {"types": ["creature"]}},   # as が無い
                {"op": "reveal_until", "filter": {"types": ["creature"]}, "as": "hit", "player": "any"}):
        try:
            parse_card({**base, "spell": [bad]}, TABLES)
            raise AssertionError(f"should have raised: {bad}")
        except DefError:
            pass


def _settle_until(e, cond, max_steps=300):
    """cond() が成り立つまで既定回答で進める（攻撃フェイズまで進めると次のドローで
    山札の残りが動いてしまうため、効果の解決直後に止める）。"""
    for _ in range(max_steps):
        if cond():
            return
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["kind"] == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("condition not reached")


def _play_and_resolve(e, defn, cond):
    answer(e, "charge", "pass")
    answer(e, "main", f"play:{defn}")
    _settle_until(e, cond)


def _arrange_deck(e, p, top_defns):
    """山札の上から top_defns の順に並べ替え、その cid リストを返す。"""
    rest = list(e.s.zones["deck"][p])
    chosen = []
    for dfn in top_defns:
        c = next(c for c in rest if e.s.cards[c].defn == dfn)
        rest.remove(c)
        chosen.append(c)
    e.s.zones["deck"][p] = chosen + rest
    return chosen


def _zone(e, cid):
    return e.s.cards[cid].zone


def test_basic_hit_to_bz_rest_to_graveyard(rules):
    """T298: 公開は最初の進化ではないクリーチャーで止まり、出なかった公開分は墓地へ。"""
    e = setup(rules, {"hand": ["T298"], "mana": ["T001", "T001", "T001"],
                      "deck": ["T300", "T063"]}, {})
    spell_c, hit_c, below_c = _arrange_deck(e, 0, ["T300", "T001", "T063"])
    _play_and_resolve(e, "T298", lambda: _zone(e, hit_c) == "bz" and _zone(e, spell_c) == "graveyard")
    assert _zone(e, below_c) == "deck"   # ヒットより下は公開されない


def test_count_two_then_shuffle(rules):
    """T299: 2体出るまで公開し、その2体を出す。残りの公開分はシャッフルの対象として山札に残る。"""
    e = setup(rules, {"hand": ["T299"], "mana": ["T005", "T001", "T001", "T001", "T001"],
                      "deck": ["T063", "T063", "T300"]}, {})
    d1, rest_c, d2, below_c = _arrange_deck(e, 0, ["T063", "T300", "T063", "T001"])
    _play_and_resolve(e, "T299", lambda: _zone(e, d1) == "bz" and _zone(e, d2) == "bz")
    assert _zone(e, rest_c) == "deck"   # 出なかった公開分は山札に戻る（シャッフル）
    assert _zone(e, below_c) == "deck"


def test_owner_relative_cost(rules):
    """T300: 破壊したクリーチャーの持ち主が、その破壊したクリーチャーよりコストが小さい
    クリーチャーが出るまで公開する（player_from と cost_of の相対フィルタ）。"""
    e = setup(rules, {"hand": ["T300"], "mana": ["T063", "T001", "T001"], "bz": ["T299"],
                      "deck": ["T299", "T063", "T300"]}, {})
    target = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T299")
    big_c, hit_c, below_c = _arrange_deck(e, 0, ["T299", "T063", "T300"])
    _play_and_resolve(e, "T300", lambda: _zone(e, target) == "graveyard" and _zone(e, hit_c) == "bz")
    assert e.s.cards[hit_c].controller == 0
    assert _zone(e, big_c) == "deck"   # コストが小さくないので出ず、シャッフルで山札に残る
    assert _zone(e, below_c) == "deck"


def test_dynamic_count_from_destroyed(rules):
    """T301: 破壊した数と同じ数だけドラゴンが出るまで公開する（count: {var: d}）。"""
    e = setup(rules, {"hand": ["T301"], "mana": ["T005", "T001", "T001", "T001", "T001", "T001"],
                      "bz": ["T001", "T001"], "deck": ["T063", "T063", "T063"]}, {})
    own = [c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T001"]
    rest_c, d1, d2, d3 = _arrange_deck(e, 0, ["T001", "T063", "T063", "T063"])
    _play_and_resolve(e, "T301", lambda: _zone(e, d1) == "bz" and _zone(e, d2) == "bz")
    assert all(_zone(e, c) == "graveyard" for c in own)   # 自分の非ドラゴン2体を破壊
    assert _zone(e, rest_c) == "graveyard"                # 公開した非ドラゴンは墓地へ
    assert _zone(e, d3) == "deck"                         # 3体目は公開されない


def test_deck_exhausted_without_hit(rules):
    """ヒットが無いまま山札が尽きたら、公開分はすべて残りとして処理される（T298）。"""
    e = setup(rules, {"hand": ["T298"], "mana": ["T001", "T001", "T001"],
                      "deck": ["T300", "T300"]}, {})
    spells = _arrange_deck(e, 0, ["T300", "T300"])
    for c in list(e.s.zones["deck"][0]):
        if c not in spells:
            e._raw_move(c, "graveyard")
    answer(e, "charge", "pass")
    answer(e, "main", "play:T298")
    for _ in range(50):   # 公開分がすべて墓地に落ち、山札が0枚になって敗北する（総合ルール104.2b）
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["kind"] == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        else:
            e.answer(list(range(d["min"])))
    else:
        raise AssertionError("game should have ended by deck-out")
    assert all(_zone(e, c) == "graveyard" for c in spells)
    assert [e.s.cards[c].defn for c in e.zlist("bz", 0)] == ["T298"]   # 何も出てこない
