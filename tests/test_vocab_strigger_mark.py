"""第3段その2b: S・トリガーの印（バンドC2 U68）。

- op move の strigger: "off"（この移動で手札に加わるカードは S・トリガーを使えない。
  エメラル型／エスケープ）と "on"（S・トリガーを得る）
- カード側の印 strigger_off / strigger_on（手札にいる間だけ有効。手札を離れると消える）
- op strigger（対象に印を付ける）／常在型 mod deny: [s_trigger]（シールドゾーンの chars に届く）

proto: T261 エメラル型試験呪文 / T262 帰還試験呪文（対照）/ T263 印付与試験呪文 /
T264 無印の盾兵 / T265 付与誘発試験獣 / T266 非光封じ試験獣 / T278 逃避試験獣 / T279 闇盾試験兵。
既存 proto: T207（光の S・トリガー持ち）/ T256 除去試験呪文。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, load_tables, parse_card

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


def _drive(e, handler=None, until=None, kinds=None, limit=900):
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return
        if until is not None and d["kind"] in ("main", "charge", "attack") and until():
            return
        if kinds is not None:
            kinds.append(d["kind"])
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


def _shield_idx(e, d, cid):
    for i, o in enumerate(d["options"]):
        if o.get("cid") == cid:
            return i
    return e.zlist("shield", e.s.cards[cid].owner).index(cid)


def _attack_handler(e, atk_key, shield_cid, declare=None, declared_keys=None):
    """P1 が atk_key でプレイヤー攻撃し、shield_cid のシールドを割り、宣言判断に答える。
    declare: None=既定 / []=すべて辞退 / キーの集合=それだけ宣言。"""
    def h(d):
        if d["kind"] == "attack" and d["player"] == 1:
            ks = [o["key"] for o in d["options"]]
            return [ks.index(atk_key)] if atk_key in ks else None
        if d["kind"] == "choose_shields":
            return [_shield_idx(e, d, shield_cid)]
        if d["kind"] == "declare_strigger":
            if declared_keys is not None:
                declared_keys.extend(o["key"] for o in d["options"])
            if declare is None:
                return None
            return [i for i, o in enumerate(d["options"]) if o["key"] in declare]
        return None
    return h


def test_proto_parse(rules):
    for cid in ("T261", "T262", "T263", "T264", "T265", "T266", "T278", "T279"):
        parse_card(_proto_card(cid), TABLES)
    bad = _proto_card("T261")
    bad["spell"][0]["strigger"] = 3
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def test_move_off_suppresses_declaration(rules):
    """U68: strigger: "off" 付きで手札に加わったカードは宣言できず、印が残る。"""
    e = setup(rules, {"hand": ["T261"], "mana": ["T253", "T253"],
                      "shield": ["T207", "T001", "T001", "T001", "T001"]}, {})
    t207 = _cid(e, 0, "T207", "shield")
    kinds = []
    d = _to_main(e, 0)
    _play(e, d, "play:T261")

    def h(dd):
        if dd["kind"] == "choose_cards":
            return [_shield_idx(e, dd, t207)]
        return None
    _drive(e, h, until=lambda: e.s.cards[t207].zone == "hand", kinds=kinds)
    assert e.s.cards[t207].zone == "hand"
    assert "declare_strigger" not in kinds          # 宣言の機会自体が無い
    assert e.s.cards[t207].strigger_off is True     # 印がカードに残っている

    # 対照: 印なしの帰還では宣言判断が出る（辞退する）
    e = setup(rules, {"hand": ["T262"], "mana": ["T253", "T253"],
                      "shield": ["T207", "T001", "T001", "T001", "T001"]}, {})
    t207 = _cid(e, 0, "T207", "shield")
    kinds = []
    d = _to_main(e, 0)
    _play(e, d, "play:T262")

    def h2(dd):
        if dd["kind"] == "choose_cards":
            return [_shield_idx(e, dd, t207)]
        if dd["kind"] == "declare_strigger":
            return []
        return None
    _drive(e, h2, until=lambda: e.s.cards[t207].zone == "hand", kinds=kinds)
    assert "declare_strigger" in kinds
    assert e.s.cards[t207].strigger_off is False


def test_escape_off_suppresses_declaration(rules):
    """U68: エスケープで手札に加えたシールドも S・トリガーを使えない（キーワード側の印）。"""
    e = setup(rules, {"bz": ["T278"], "shield": ["T207", "T001", "T001", "T001", "T001"]},
              {"hand": ["T256"], "mana": ["T266"] * 3})
    t207 = _cid(e, 0, "T207", "shield")
    kinds = []
    d = _to_main(e, 1)
    _play(e, d, "play:T256")

    def h(dd):
        if dd["kind"] == "choose_replacement":
            rep = [i for i, o in enumerate(dd["options"]) if o["key"].startswith("replace:")]
            return rep[:1] or None
        if dd["kind"] == "choose_cards":
            return [_shield_idx(e, dd, t207)]
        return None
    _drive(e, h, until=lambda: e.s.cards[t207].zone == "hand", kinds=kinds)
    assert e.s.cards[t207].zone == "hand"
    assert "declare_strigger" not in kinds
    assert e.s.cards[t207].strigger_off is True
    assert any(e.s.cards[c].defn == "T278" for c in e.zlist("bz", 0))   # 破壊を免れた


def test_grant_on_allows_declaration(rules):
    """U68: op strigger で付けた印により、S・トリガーを持たないカードが宣言できる。"""
    e = setup(rules, {"hand": ["T263"], "mana": ["T265", "T265"],
                      "shield": ["T264", "T001", "T001", "T001", "T001"]},
              {"bz": ["T001"]})
    t264 = _cid(e, 0, "T264", "shield")
    d = _to_main(e, 0)
    _play(e, d, "play:T263")

    def h(dd):
        if dd["kind"] == "choose_cards":
            return [_shield_idx(e, dd, t264)]
        return None
    _drive(e, h, until=lambda: e.s.cards[t264].strigger_on)
    assert e.s.cards[t264].zone == "shield"
    assert e.s.cards[t264].strigger_on is True

    h2 = _attack_handler(e, "attack:T001:player", t264, declare={"strigger:T264"})
    _drive(e, h2, until=lambda: e.s.cards[t264].zone == "bz")
    assert e.s.cards[t264].zone == "bz"             # 印で得た S・トリガーで召喚できた


def test_no_mark_no_declaration(rules):
    """U68: 印が無ければ S・トリガーを持たないカードは宣言できない（判別）。"""
    e = setup(rules, {"shield": ["T264", "T001", "T001", "T001", "T001"]}, {"bz": ["T001"]})
    t264 = _cid(e, 0, "T264", "shield")
    seen = []
    h = _attack_handler(e, "attack:T001:player", t264, declared_keys=seen)
    _drive(e, h, until=lambda: e.s.cards[t264].zone == "hand")
    assert e.s.cards[t264].zone == "hand"           # 場には出ず手札に加わっただけ
    assert "strigger:T264" not in seen


def test_mark_clears_after_leaving_hand(rules):
    """U68: 誘発で付けた印は手札にいる間だけ有効で、手札を離れると消える。"""
    e = setup(rules, {"bz": ["T265"], "shield": ["T207", "T001", "T001", "T001", "T001"],
                      "mana": ["T004", "T004", "T004"]},
              {"bz": ["T001"]})
    t207 = _cid(e, 0, "T207", "shield")
    h = _attack_handler(e, "attack:T001:player", t207, declare=[])
    _drive(e, h, until=lambda: e.s.cards[t207].strigger_on)
    assert e.s.cards[t207].zone == "hand"
    assert e.s.cards[t207].strigger_on is True      # T265 の誘発で印が付いた

    d = _to_main(e, 0)
    _play(e, d, "play:T207")
    _drive(e, until=lambda: e.s.cards[t207].zone == "bz")
    assert e.s.cards[t207].zone == "bz"
    assert e.s.cards[t207].strigger_on is False     # 手札を離れたので印は消えた
    assert e.s.cards[t207].strigger_off is False


def test_static_deny_strigger(rules):
    """U68: 常在型の deny: [s_trigger] はシールドゾーンのカードの chars に届く。"""
    e = setup(rules, {"bz": ["T266"], "shield": ["T279", "T001", "T001", "T001", "T001"]},
              {"bz": ["T001"]})
    t279 = _cid(e, 0, "T279", "shield")
    seen = []
    h = _attack_handler(e, "attack:T001:player", t279, declare=[], declared_keys=seen)
    _drive(e, h, until=lambda: e.s.cards[t279].zone == "hand")
    assert e.s.cards[t279].zone == "hand"
    assert "strigger:T279" not in seen              # 闇（光以外）は宣言できない

    # 対照: 光のカードは deny の対象外なので宣言できる
    e = setup(rules, {"bz": ["T266"], "shield": ["T207", "T001", "T001", "T001", "T001"]},
              {"bz": ["T001"]})
    t207 = _cid(e, 0, "T207", "shield")
    seen = []
    h = _attack_handler(e, "attack:T001:player", t207, declare=[], declared_keys=seen)
    _drive(e, h, until=lambda: e.s.cards[t207].zone == "hand")
    assert "strigger:T207" in seen
