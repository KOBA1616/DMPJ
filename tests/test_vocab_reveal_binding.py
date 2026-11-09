"""第3段その2b: 公開集合の保持（バンドC1 U39）。

- choose の as で束ねた集合（公開した3枚など）を、後続の効果が {total_cost: {ref:}} /
  {total_power: {ref:}} で参照できる（reveal_until の前提）
- choose の reveal: true で公開が s.pub に残る
- 合計式は mod の count でも使える（マナゾーンのコスト合計でパワー修整）

proto: T258 公開合計試験呪文 / T259 合計パワー門試験呪文 / T260 マナ合計強化試験獣。
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


def _boring(d):
    if d["kind"] in ("charge", "main", "attack"):
        keys = [o["key"] for o in d["options"]]
        for want in ("pass", "end_turn", "end_attack", "end_phase"):
            if want in keys:
                return [keys.index(want)]
        return [0]
    return [0]


def _go(e, pick=None, limit=600):
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return
        if d["kind"] in ("main", "charge", "attack"):
            return
        ans = pick(d) if pick else None
        e.answer(ans if ans is not None else _boring(d))
    raise AssertionError("decisions did not settle")


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


def _set_top(e, p, defns):
    z = e.s.zones["deck"][p]
    chosen = []
    for dfn in defns:
        chosen.append(next(c for c in z if e.s.cards[c].defn == dfn and c not in chosen))
    e.s.zones["deck"][p] = chosen + [c for c in z if c not in chosen]
    return chosen


def test_proto_parse(rules):
    for cid in ("T258", "T259", "T260"):
        parse_card(_proto_card(cid), TABLES)
    bad = _proto_card("T258")
    bad["spell"][1]["cond"] = {"cmp": [{"total_cost": {"zone": "nowhere", "owner": "you"}}, "<=", 6]}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def test_total_cost_threshold_and_public_reveal(rules):
    """U39: 公開した3枚のコスト合計で分岐し、公開は s.pub に残る。"""
    e = setup(rules, {"hand": ["T258"], "mana": ["T253", "T253"]}, {})
    top = _set_top(e, 0, ["T001", "T001", "T001"])   # コスト2×3 = 合計6（境界）
    d = _to_main(e, 0)
    _play(e, d, "play:T258")
    _go(e)
    assert len(e.zlist("hand", 0)) == 2              # 合計6以下なので2枚引く
    revealed = {x["cid"] for x in e.s.pub if x["kind"] == "reveal"}
    assert revealed == set(top)                      # 公開した3枚が公開情報に残っている

    e = setup(rules, {"hand": ["T258"], "mana": ["T253", "T253"], "deck": ["T271"]}, {})
    _set_top(e, 0, ["T271", "T001", "T001"])         # 7+2+2 = 合計11
    d = _to_main(e, 0)
    _play(e, d, "play:T258")
    _go(e)
    assert len(e.zlist("hand", 0)) == 1              # 合計6を超えるので1枚だけ引く（判別）


def test_total_power_gate(rules):
    """U39: 選んだクリーチャーのパワー合計で分岐する。"""
    e = setup(rules, {"bz": ["T001", "T004"], "hand": ["T259"], "mana": ["T277", "T277"]}, {})
    d = _to_main(e, 0)
    _play(e, d, "play:T259")
    _go(e, pick=lambda dd: [i for i, o in enumerate(dd["options"])] if dd["kind"] == "choose_cards" else None)
    assert len(e.zlist("hand", 0)) == 2              # 2000+3000 = 5000以上なので2枚引く

    e = setup(rules, {"bz": ["T001", "T004"], "hand": ["T259"], "mana": ["T277", "T277"]}, {})

    def pick_one(dd):
        if dd["kind"] == "choose_cards":
            return [next(i for i, o in enumerate(dd["options"]) if ":T001:" in o["key"])]
        return None
    d = _to_main(e, 0)
    _play(e, d, "play:T259")
    _go(e, pick_one)
    assert len(e.zlist("hand", 0)) == 1              # 2000だけなので1枚（判別）


def test_total_cost_in_mod_count(rules):
    """U39: 合計式は mod の count でも使える（マナのコスト合計ぶんパワーが上がる）。"""
    e = setup(rules, {"bz": ["T260"], "mana": ["T001", "T004", "T277"]}, {})
    cid = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T260")
    assert e.chars(cid)["power"] == 2000 + (2 + 3 + 2)

    e = setup(rules, {"bz": ["T260"]}, {})
    cid = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T260")
    assert e.chars(cid)["power"] == 2000             # マナが無ければ合計0（判別）


def test_expr_empty_set_totals_zero(rules):
    """U39: 空集合の合計は 0（未束縛の ref でもエラーにならない）。"""
    e = setup(rules, {}, {})
    env = {"you": 0, "vars": {}}
    assert e.eval_expr({"total_cost": {"ref": "missing"}}, env) == 0
    assert e.eval_expr({"total_power": {"ref": "missing"}}, env) == 0
