"""第3段その2b: 名前つき条件アトム（バンドB U1）の既存可確認。

G・G・G（自分の手札数）/ ラビリンス（シールド数の比較＋相手手札の呪文への deny cast）/
レインボーナス（多色の存在）/ 龍マナ武装（マナゾーンのドラゴン数）は、いずれも既存の
式・フィルタ・mod の組み合わせで書けることをテストで裏を取る（精査で既存可）。
不足アトムの追加は不要だった。

proto: T271 GGG軽減試験獣 / T272 ラビリンス試験獣 / T273 観測試験呪文 /
T274 レインボーナス試験獣 / T275 多色試験獣 / T276 龍マナ武装試験獣 / T277 竜試験兵。
"""
from pathlib import Path

import yaml
from conftest import setup

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def _cid(e, p, defn, zone):
    return next(c for c in e.zlist(zone, p) if e.s.cards[c].defn == defn)


def _boring(d):
    if d["kind"] in ("charge", "main", "attack"):
        keys = [o["key"] for o in d["options"]]
        for want in ("pass", "end_turn", "end_attack", "end_phase"):
            if want in keys:
                return [keys.index(want)]
        return [0]
    return [0]


def _drive(e, handler=None, until=None, limit=900):
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return
        if until is not None and d["kind"] in ("main", "charge", "attack") and until():
            return
        ans = handler(d) if handler else None
        e.answer(ans if ans is not None else _boring(d))
    raise AssertionError("did not settle")


def _to_main(e, player):
    for _ in range(600):
        d = e.advance()
        if d is None:
            raise AssertionError("game ended before main")
        if d["kind"] == "main" and d["player"] == player:
            return d
        e.answer(_boring(d))
    raise AssertionError("main not reached")


def _play(e, d, key_prefix):
    e.answer([next(i for i, o in enumerate(d["options"]) if o["key"].startswith(key_prefix))])


def test_proto_parse(rules):
    for cid in ("T271", "T272", "T273", "T274", "T275", "T276", "T277"):
        parse_card(_proto_card(cid), TABLES)


def test_ggg_cost_reduction(rules):
    """U1: G・G・G は手札数の count 式＋手札ゾーンの常在型で書ける。"""
    e = setup(rules, {"hand": ["T271"], "mana": ["T277"]}, {})
    cid = _cid(e, 0, "T271", "hand")
    assert e.chars(cid)["pay_cost"] == 1            # 手札1枚以下なので 7 - 6

    e = setup(rules, {"hand": ["T271", "T001"], "mana": ["T277"]}, {})
    cid = _cid(e, 0, "T271", "hand")
    assert e.chars(cid)["pay_cost"] == 7            # 手札2枚では軽減しない（判別）


def _main_or_none(e, player):
    """player のメイン判断が来ればそれを返し、ターンが終わってしまったら None を返す
    （唱えられるカードが無いとメイン判断自体が現れないため）。"""
    seen_charge = set()
    for _ in range(600):
        d = e.advance()
        if d is None:
            return None
        if d["kind"] == "main" and d["player"] == player:
            return d
        if d["kind"] == "charge":
            if d["player"] != player and seen_charge:
                return None
            seen_charge.add(d["player"])
        e.answer(_boring(d))
    return None


def test_labyrinth_deny_cast(rules):
    """U1: ラビリンスはシールド数の比較式＋相手の手札ゾーンへの deny cast で書ける。
    バトルゾーンの常在型が相手の手札のカードの chars に届くことの確認を兼ねる。"""
    e = setup(rules, {"bz": ["T272"]},
              {"hand": ["T273"], "mana": ["T253"] * 5, "shield": ["T001"] * 4})
    assert len(e.zlist("shield", 0)) > len(e.zlist("shield", 1))   # 前提: 自分のシールドが多い
    d = _main_or_none(e, 1)
    keys = [o["key"] for o in d["options"]] if d else []
    assert not any(k.startswith("play:T273") for k in keys)         # コスト5の呪文を唱えられない

    # 対照: シールド数が相手以下なら唱えられる
    e = setup(rules, {"bz": ["T272"], "shield": ["T001"] * 4},
              {"hand": ["T273"], "mana": ["T253"] * 5})
    assert len(e.zlist("shield", 0)) <= len(e.zlist("shield", 1))
    d = _main_or_none(e, 1)
    assert d is not None
    keys = [o["key"] for o in d["options"]]
    assert any(k.startswith("play:T273") for k in keys)


def test_rainbow_bonus(rules):
    """U1: レインボーナスは multicolor フィルタの exists 式で書ける。"""
    e = setup(rules, {"bz": ["T275"], "hand": ["T274"], "mana": ["T001"] * 3}, {})
    d = _to_main(e, 0)
    _play(e, d, "play:T274")
    _drive(e, until=lambda: any(e.s.cards[c].defn == "T274" for c in e.zlist("bz", 0)))
    assert len(e.zlist("hand", 0)) == 1             # 多色がいるので1枚引いた

    e = setup(rules, {"hand": ["T274"], "mana": ["T001"] * 3}, {})
    d = _to_main(e, 0)
    _play(e, d, "play:T274")
    _drive(e, until=lambda: any(e.s.cards[c].defn == "T274" for c in e.zlist("bz", 0)))
    assert len(e.zlist("hand", 0)) == 0             # 多色がいなければ引かない（判別）


def test_dragon_mana_busou(rules):
    """U1: 龍マナ武装はマナゾーンの race_has フィルタの count 式で書ける。"""
    e = setup(rules, {"hand": ["T276"], "mana": ["T277"] * 5}, {})
    d = _to_main(e, 0)
    _play(e, d, "play:T276")
    _drive(e, until=lambda: any(e.s.cards[c].defn == "T276" for c in e.zlist("bz", 0)))
    assert len(e.zlist("hand", 0)) == 1             # ドラゴン5体で1枚引いた

    e = setup(rules, {"hand": ["T276"], "mana": ["T277"] * 4 + ["T001"]}, {})
    d = _to_main(e, 0)
    _play(e, d, "play:T276")
    _drive(e, until=lambda: any(e.s.cards[c].defn == "T276" for c in e.zlist("bz", 0)))
    assert len(e.zlist("hand", 0)) == 0             # 4体では引かない（判別）
