"""専用ステージ: 113.6a 待機状態シールドの数え方（エンジン意味論の修正）。

第435弾で実測された乖離: ブレイク処理（combat.py の h_break
phase 1）は、選択済みシールドをシールドゾーンに残したまま
_permits_face を評価するため、S・トリガー宣言時点の
count {zone: shield} がブレイク分を含んでしまう。

公式根拠（総合ルール Ver.1.49・113.6a）: 「プレイヤーの使用
宣言が終わるまでの間、手札に加えられるシールドは待機状態に
なります。待機状態のシールドはシールドゾーンにありますが、
シールドゾーンにあるシールドの数に含まれません。また、
シールドゾーンにあるカードの枚数としても数えません。」
公式 Q&A 44581 は同時ブレイクのケースそのもの（5枚同時
ブレイク → 宣言時点は 0 枚）。

設計: 待機状態は GameState の新フィールドではなく、宣言窓の
間だけブレイクタスク自身が保持する（t["st_waiting"]。窓は
_break_consult で「手札に加わるシールド」が確定した後に開き、
移動シーケンスを積む直前に閉じる。窓の中で評価されるのは
宣言判定と S・バック宣言だけで、他のタスクは割り込まない）。
数え分けは selectors の枚数系だけに効かせる:
- eval_expr {count: sel} / count_of(sel): 待機中のカード
  （束のトップ＋その下のカードすべて）を数えない
- eval_expr {bundles: spec}: 待機中の束を数えない
exists・選択・特性の集合集計（civ_count 等）は従来どおり
（待機中のシールドはシールドゾーンに「ある」）。
_break_consult の評価は窓の外（置換が決まるまでは手札に
加わるかどうか自体が未確定）。

判別シナリオは dm28-025 ヤミノリミット型（proto T1239、
第435弾の形そのもの）: static {affects: {zone: shield,
owner: opp}, if: {cmp: [count {zone: shield, owner: opp}
>= 4]}, mod: {deny: [s_trigger]}}。相手シールド4枚から
1枚ブレイク → 宣言時点は3枚で条件不成立（使える）はずが、
修正前は4枚と数えて使えなかった。

判別役: T006（S・トリガー呪文＝パワー4000以下を破壊）/
T1107（パワー2000・1ブレイク）/ T005（W・ブレイカー・
パワー3000・2ブレイク）/ T001（盾役・対照役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接包む（第319弾以降の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

FORM = [{"kind": "static",
         "affects": {"zone": "shield", "owner": "opp"},
         "if": {"cmp": [{"count": {"zone": "shield", "owner": "opp"}},
                        ">=", 4]},
         "mod": {"deny": ["s_trigger"]}}]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1239")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature"] and c["civs"] == ["darkness"]
    assert c["cost"] == 4 and c["power"] == 4000
    assert c["races"] == ["ダーク・モンスター"]
    d = parse_card(copy.deepcopy(c), TABLES)
    assert FORM[0] in d.abilities
    for tid in ("T006", "T1107", "T005", "T001"):
        parse_card(proto_card(tid), TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _find(e, zone, p, defn, skip=0):
    hits = [c for c in e.zlist(zone, p) if e.cdef(c).id == defn]
    return hits[skip]


def test_chars_at_rest_denied_at_4(rules):
    """窓の外（特性レベル）: 相手シールド4枚では deny が付き、
    3枚では付かない。従来どおりの評価（対照）。"""
    e = _build(rules, {"bz": ["T1239"]},
               {"shield": ["T006", "T001", "T001", "T001"]})
    assert "s_trigger" in e.chars(_find(e, "shield", 1, "T006"))["deny"]
    e = _build(rules, {"bz": ["T1239"]},
               {"shield": ["T006", "T001", "T001"]})
    assert "s_trigger" not in e.chars(_find(e, "shield", 1, "T006"))["deny"]


def _drive(e, attacker, player, break_defns, use_strigger=False):
    """player の attacker でプレイヤーを攻撃し、break_defns の
    順でシールドを選んでブレイクする。declare_strigger の
    判断ログ [(kind, player, keys), ...] を返す（第374弾の作法）。"""
    log = []
    attacked = False
    for _ in range(1500):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack" and d.get("player") == player and not attacked:
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit:
                attacked = True
                e.answer([hit[0]])
                continue
        if kind == "choose_shields" and break_defns:
            shields = e.zlist("shield", 1 - player)
            want = list(break_defns)
            idx = []
            for i, c in enumerate(shields):
                if e.cdef(c).id in want:
                    idx.append(i)
                    want.remove(e.cdef(c).id)
            e.answer(idx)
            continue
        if kind == "declare_strigger":
            log.append((kind, d.get("player"), keys))
            e.answer(list(range(len(keys))) if use_strigger else [])
            continue
        if kind == "choose_cards":
            hit = [i for i, k in enumerate(keys) if attacker in k]
            if hit:
                e.answer(hit[:1])
                continue
        if kind == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
            continue
        e.answer(list(range(d.get("min", 0))))
        if attacked and kind == "main" and d.get("player") == player:
            break
    return log


def test_break_from_4_usable(rules):
    """判別: 相手シールド4枚から1枚ブレイク → 宣言時点は
    3枚で条件不成立となり、S・トリガーを宣言できる。
    使えば攻撃側（パワー2000）が破壊される。解決後の特性
    評価も残り3枚で deny が付かない（解決時の評価は従来
    どおり実際のゾーンで数える）。"""
    e = _build(rules,
               {"bz": ["T1239", "T1107"]},
               {"shield": ["T006", "T006", "T001", "T001"]})
    log = _drive(e, "T1107", 0, ["T006"], use_strigger=True)
    st = [x for x in log if x[0] == "declare_strigger"]
    assert st and st[0][1] == 1 and "strigger:T006" in st[0][2]
    assert "T1107" in _defns(e, "graveyard", 0)
    assert "T006" in _defns(e, "graveyard", 1)
    assert len(e.zlist("shield", 1)) == 3
    rest = _find(e, "shield", 1, "T006")
    assert "s_trigger" not in e.chars(rest)["deny"]


def test_break_from_5_denied(rules):
    """対照: 相手シールド5枚から1枚ブレイク → 宣言時点は
    4枚で条件成立のまま、宣言判断自体が出ずカードは手札へ。"""
    e = _build(rules,
               {"bz": ["T1239", "T1107"]},
               {"shield": ["T006", "T001", "T001", "T001", "T001"]})
    log = _drive(e, "T1107", 0, ["T006"], use_strigger=True)
    assert not [x for x in log if x[0] == "declare_strigger"]
    assert "T006" in _defns(e, "hand", 1)
    assert "T1107" in _defns(e, "bz", 0)
    assert len(e.zlist("shield", 1)) == 4


def test_break_two_from_5_usable(rules):
    """判別（同時ブレイク）: W・ブレイカーで5枚から2枚同時
    ブレイク → 宣言時点は3枚で条件不成立、宣言できる。
    公式 Q&A 44581 の同時ブレイクの読みと同方向。"""
    e = _build(rules,
               {"bz": ["T1239", "T005"]},
               {"shield": ["T006", "T001", "T001", "T001", "T001"]})
    log = _drive(e, "T005", 0, ["T006", "T001"], use_strigger=True)
    st = [x for x in log if x[0] == "declare_strigger"]
    assert st and st[0][1] == 1 and "strigger:T006" in st[0][2]
    assert "T005" in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 1)) == 3


def test_break_two_from_6_denied(rules):
    """対照（同時ブレイク）: 6枚から2枚同時ブレイク →
    宣言時点は4枚で条件成立のまま、宣言できない。"""
    e = _build(rules,
               {"bz": ["T1239", "T005"]},
               {"shield": ["T006", "T001", "T001", "T001", "T001", "T001"]})
    log = _drive(e, "T005", 0, ["T006", "T001"], use_strigger=True)
    assert not [x for x in log if x[0] == "declare_strigger"]
    assert "T006" in _defns(e, "hand", 1)
    assert len(e.zlist("shield", 1)) == 4
