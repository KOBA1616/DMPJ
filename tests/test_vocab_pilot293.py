"""第293弾: 進化元のゾーン拡張（墓地・マナ・手札・シールドからの進化V/GV、
進化GV・Ωのフィルタ別ゾーン、デッキ進化GV）。

形A（進化V＋ゾーン）: evolve_from リスト形＋evolve_zone（第231弾の V 選択は
_evo_pool 経由でゾーン対応済みだったことを実挙動で固定）。
形B（進化GV＋ゾーン）: evolve_count: 3＋evolve_zone: mana/hand/shield
（graveyard は登録済み先例あり。shield は束のトップだけがプールで、
進化元は「カード」全般＝クリーチャー絞り込みをしない）。
形B'（「N体まで」GV）: 新規フィールド evolve_max（evolve_any の上限）。
形C（進化GV・Ω）: 新規。evolve_from の各フィルタの zone キーを honor する
（従来は検証で剥がすだけで無視されていた）。フィルタごとにそのゾーンの
プールから1体ずつ選ぶ。
形D（デッキ進化GV）: 新規。deck_evolution {stack_all: true} — 山札の上から
count 枚を裏向きのまま全部重ねる（選択・公開なし）。山札が count 枚未満
では出せない。
形E（超無限の各形）: evolve_zones＋evolve_any（Ω）、evolve_zone:
graveyard＋evolve_any（超無限墓地進化）、evolve_total_cost_ge＋
not_types: [evolution] フィルタ（超無限進化・コスト合計）は既存語彙の
ドリフトであることを実挙動で固定。
"""
import copy

import pytest
import yaml
from pathlib import Path

from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _tops(e, p):
    return [c for c in e.zlist("bz", p)
            if e.s.cards[c].controller == p and e.s.cards[c].top_of < 0]


def _play_evo(e, defn, evo_pick=None, seen=None, max_steps=200):
    """main で defn を出し切るまで進める。evo_pick(d) は choose_evo_source
    への答え（None なら最小数）。seen には通過した decision kind を集める。"""
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        if seen is not None:
            seen.append(d["kind"])
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith(f"play:{defn}") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith(f"play:{defn}"))])
        elif d["kind"] == "choose_evo_source" and evo_pick is not None:
            e.answer(evo_pick(d))
        elif d["kind"] in ("pay_mana", "choose_evo_source"):
            e.answer(list(range(d["min"])))
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if defn in _defns(e, "bz", 0) and e.s.turn >= 1 and d["kind"] == "attack":
            return
    raise AssertionError("evolution did not complete")


def _can_play(e, defn, p=0):
    """main の play 選択肢のゲートそのもの（_play_options が使う _can_play_face）。
    出せない場合は main が pass のみになり decision 自体が出ないため、
    否定形の検証はこの述語で固定する（肯定形は実挙動テストが担保）。"""
    cid = next(c for c in e.zlist("hand", p) if e.s.cards[c].defn == defn)
    return e._can_play_face(cid, p, None)


def _top(e, defn):
    return next(c for c in _tops(e, 0) if e.s.cards[c].defn == defn)


# ---------- parse / 検証 ----------

def _proto_raw(tid):
    ps = yaml.safe_load(open(Path(__file__).parent.parent
                             / "data" / "cards" / "proto.yaml",
                             encoding="utf-8"))["cards"]
    return copy.deepcopy(next(p for p in ps if p["id"] == tid))


def test_parse_forms():
    from dmsim.cards.defs import load_tables, parse_card
    tables = load_tables()
    t867 = parse_card(_proto_raw("T867"), tables)
    assert t867.evolve_from[0]["zone"] == "graveyard"
    assert t867.evolve_from[2]["zone"] == "bz"
    t868 = parse_card(_proto_raw("T868"), tables)
    assert t868.deck_evolution == {"count": 3, "blind": True, "stack_all": True}
    t871 = parse_card(_proto_raw("T871"), tables)
    assert t871.evolve_total_cost_ge == 10


def test_validation_rejects_bad_zone_and_bad_stack_all():
    from dmsim.cards.defs import DefError, load_tables, parse_card
    tables = load_tables()
    raw = _proto_raw("T867")
    raw["evolve_from"][0]["zone"] = "nowhere"
    with pytest.raises(DefError):
        parse_card(raw, tables)
    raw = _proto_raw("T868")
    raw["deck_evolution"] = {"count": 3, "blind": True, "stack_all": "yes"}
    with pytest.raises(DefError):
        parse_card(raw, tables)
    raw = _proto_raw("T868")
    raw["deck_evolution"] = {"count": 3, "blind": True, "stack_all": True,
                             "bogus": 1}
    with pytest.raises(DefError):
        parse_card(raw, tables)
    raw = _proto_raw("T880")
    raw["evolve_any"] = False   # evolve_max は evolve_any が前提
    with pytest.raises(DefError):
        parse_card(raw, tables)
    raw = _proto_raw("T880")
    raw["evolve_max"] = 0
    with pytest.raises(DefError):
        parse_card(raw, tables)


# ---------- 形A: 進化V＋ゾーン ----------

def test_graveyard_v():
    e = setup(_rules(), {"graveyard": ["T872", "T872"], "hand": ["T861"],
                         "mana": ["T008"] * 5}, {})
    _play_evo(e, "T861")
    top = _top(e, "T861")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T872", "T872"]
    assert _defns(e, "graveyard", 0) == []


def test_mana_v():
    e = setup(_rules(), {"hand": ["T862"],
                         "mana": ["T873", "T873"] + ["T004"] * 5}, {})
    _play_evo(e, "T862")
    top = _top(e, "T862")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T873", "T873"]
    mana = _defns(e, "mana", 0)
    assert mana == ["T004"] * 5                       # 進化元は支払いに使えない
    assert sum(1 for c in e.zlist("mana", 0) if e.s.cards[c].tapped) == 5


def test_hand_v():
    e = setup(_rules(), {"hand": ["T863", "T874", "T874"],
                         "mana": ["T010"] * 5}, {})
    _play_evo(e, "T863")
    top = _top(e, "T863")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T874", "T874"]
    assert _defns(e, "hand", 0) == []


# ---------- 形B: 進化GV＋ゾーン ----------

def test_mana_gv():
    e = setup(_rules(), {"hand": ["T864"],
                         "mana": ["T875"] * 3 + ["T001"] * 6}, {})
    _play_evo(e, "T864")
    top = _top(e, "T864")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T875"] * 3
    assert _defns(e, "mana", 0) == ["T001"] * 6
    assert sum(1 for c in e.zlist("mana", 0) if e.s.cards[c].tapped) == 6


def test_hand_gv():
    e = setup(_rules(), {"hand": ["T865", "T876", "T876", "T876"],
                         "mana": ["T551"] * 6}, {})
    _play_evo(e, "T865")
    top = _top(e, "T865")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T876"] * 3
    assert _defns(e, "hand", 0) == []


def test_shield_gv():
    e = setup(_rules(), {"hand": ["T866"], "mana": ["T004"] * 6,
                         "shield": ["T872", "T873", "T874", "T001", "T001"]}, {})
    before = set(e.zlist("shield", 0))
    assert len(before) == 5
    _play_evo(e, "T866")
    top = _top(e, "T866")
    under = e.s.cards[top].under
    assert len(under) == 3 and set(under) <= before
    assert len(e.zlist("shield", 0)) == 2


def test_shield_gv_needs_three_creature_shields():
    # シールド5枚のうちクリーチャーは2枚（残りは呪文）では出せない
    e = setup(_rules(), {"hand": ["T866"], "mana": ["T004"] * 6,
                         "shield": ["T872", "T873", "T003", "T003", "T003"]}, {})
    assert not _can_play(e, "T866")
    e = setup(_rules(), {"hand": ["T866"], "mana": ["T004"] * 6,
                         "shield": ["T872", "T873", "T874", "T003", "T003"]}, {})
    assert _can_play(e, "T866")


def test_mana_gv_up_to_three():
    # 「3体まで」: 候補が9体いても選択の上限は3。2体だけ重ねてもよい
    e = setup(_rules(), {"hand": ["T880"],
                         "mana": ["T875"] * 3 + ["T001"] * 6}, {})
    seen = {}

    def pick(d):
        seen["max"] = d["max"]
        return [0, 1]

    _play_evo(e, "T880", evo_pick=pick)
    assert seen["max"] == 3
    top = _top(e, "T880")
    assert len(e.s.cards[top].under) == 2


def test_shield_evo_any_card():
    # シールド進化の進化元は「カード」: 呪文のシールドも重ねられる
    e = setup(_rules(), {"hand": ["T881"], "mana": ["T004"] * 5,
                         "shield": ["T003", "T003", "T001", "T001", "T001"]}, {})

    def pick_spells(d):
        return [i for i, o in enumerate(d["options"])
                if e.s.cards[o["cid"]].defn == "T003"][:2]

    _play_evo(e, "T881", evo_pick=pick_spells)
    top = _top(e, "T881")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T003", "T003"]
    assert len(e.zlist("shield", 0)) == 3


# ---------- 形C: 進化GV・Ω（フィルタ別ゾーン） ----------

def test_gv_omega_one_from_each_zone():
    e = setup(_rules(), {"graveyard": ["T872"], "bz": ["T876"],
                         "hand": ["T867"],
                         "mana": ["T874"] + ["T008"] * 6}, {})
    gy = set(e.zlist("graveyard", 0))
    mn = set(e.zlist("mana", 0))
    bz = {c for c in _tops(e, 0)}
    _play_evo(e, "T867")
    top = _top(e, "T867")
    under = e.s.cards[top].under
    assert len(under) == 3
    assert len(set(under) & gy) == 1      # 墓地から1体
    assert len(set(under) & mn) == 1      # マナから1体
    assert len(set(under) & bz) == 1      # バトルゾーンから1体


def test_gv_omega_zone_is_enforced():
    # 墓地に進化元が無ければ、バトルゾーンに3体いても出せない
    # （zone を無視する旧挙動では bz の3体でフィルタ3件を賄えてしまった）
    e = setup(_rules(), {"bz": ["T876", "T876", "T876"], "hand": ["T867"],
                         "mana": ["T874"] + ["T008"] * 6}, {})
    assert not _can_play(e, "T867")
    # 墓地に1体あれば出せる（対照）
    e = setup(_rules(), {"graveyard": ["T872"], "bz": ["T876", "T876"],
                         "hand": ["T867"],
                         "mana": ["T874"] + ["T008"] * 6}, {})
    assert _can_play(e, "T867")


# ---------- 形D: デッキ進化GV ----------

def test_deck_gv_stacks_top_three_blind():
    e = setup(_rules(), {"hand": ["T868"], "mana": ["T551"] * 6}, {})
    seen = []
    top3 = {}

    def pick(d):
        return list(range(d["min"]))

    # main で出す直前の山札トップ3を記録してから出す
    for _ in range(200):
        d = e.advance()
        assert d is not None
        seen.append(d["kind"])
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:T868") for k in keys):
            top3["cids"] = list(e.zlist("deck", 0)[:3])
            top3["deck_n"] = len(e.zlist("deck", 0))
            e.answer([next(i for i, k in enumerate(keys)
                           if k.startswith("play:T868"))])
        elif d["kind"] in ("pay_mana", "choose_evo_source"):
            e.answer(pick(d))
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if "T868" in _defns(e, "bz", 0) and d["kind"] == "attack":
            break
    else:
        raise AssertionError("deck evolution did not complete")
    assert "choose_evo_source" not in seen and "choose_cards" not in seen
    top = _top(e, "T868")
    assert list(e.s.cards[top].under) == top3["cids"]   # 上の1枚が直下
    assert len(e.zlist("deck", 0)) == top3["deck_n"] - 3


def test_deck_gv_needs_three_cards_in_deck():
    e = setup(_rules(), {"hand": ["T868"], "mana": ["T551"] * 6}, {},
              deck_left=[2, None])
    assert not _can_play(e, "T868")
    e = setup(_rules(), {"hand": ["T868"], "mana": ["T551"] * 6}, {},
              deck_left=[5, None])
    assert _can_play(e, "T868")


# ---------- 形E: 超無限の各形（既存語彙の固定） ----------

def test_inf_omega_from_mana_only():
    e = setup(_rules(), {"hand": ["T869"],
                         "mana": ["T874"] + ["T001"] * 6}, {})
    _play_evo(e, "T869")
    top = _top(e, "T869")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T874"]
    assert sum(1 for c in e.zlist("mana", 0) if e.s.cards[c].tapped) == 6


def test_inf_omega_from_graveyard():
    e = setup(_rules(), {"graveyard": ["T872"], "bz": ["T876"],
                         "hand": ["T869"], "mana": ["T001"] * 6}, {})
    _play_evo(e, "T869")
    top = _top(e, "T869")
    assert [e.s.cards[u].defn for u in e.s.cards[top].under] == ["T872"]
    assert _tops(e, 0) and e.s.cards[_top(e, "T876")].defn == "T876"


def test_inf_graveyard_any_two():
    e = setup(_rules(), {"graveyard": ["T872"] * 3, "hand": ["T870"],
                         "mana": ["T008"] * 6}, {})
    _play_evo(e, "T870", evo_pick=lambda d: [0, 1])
    top = _top(e, "T870")
    assert len(e.s.cards[top].under) == 2
    assert _defns(e, "graveyard", 0) == ["T872"]


def test_inf_total_cost_excludes_evolution_bases():
    e = setup(_rules(), {"bz": ["T877", "T878", "T879"], "hand": ["T871"],
                         "mana": ["T551"] * 7}, {})
    _play_evo(e, "T871")
    top = _top(e, "T871")
    assert {e.s.cards[u].defn for u in e.s.cards[top].under} == {"T877", "T878"}
    assert e.s.cards[_top(e, "T879")].defn == "T879"   # 進化クリーチャーは元にならない
