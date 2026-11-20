"""語彙パイロット第304弾: evolution_cross_gear（進化クロスギア）。

センサス（rejects 2,084件）: 純粋3件（dmc42-017 ツナミ・
カタストロフィー / dmc45-017 龍刃 ヤマト・スピリット / dm17-s05
グランドクロス・カタストロフィー）＋第2ギャップが実装済みの
dmc42-001（evolution_base_any_race は第232弾）。共通条項は
「進化-自分のXクロスギア１枚の上に置く」。見守り側の設計メモ
（pilot297-evolution-cross-gear-design.md）の実装。

詰まりは4点で、いずれも最小変更で解消した:
1. 進化元プールがクリーチャー限定だった。進化する面が
   cross_gear の時はプールをクロスギアのトップだけに替える
   （turn.py の _evo_pool_zone に for_gear をスレッド。
   クリーチャーはギアの進化元にならない。ベースはクロス
   済みでなくてよい＝本文に条件なし）。
2. h_play の permanent 分岐が進化重ね（stack_on）を扱って
   いなかった。クリーチャー形と同じ印を載せる。
3. _stack で crossed（クロス先）は束のトップだけが持つ。
   進化元がクロスしていたら進化後のギアへ引き継ぎ、元の
   ギアからは外す（そうしないと affects: crossed が壊れる）。
4. _rebuild（トップだけ card_only で離れる時）はクリーチャー
   しか残さなかった。クロスギアも単独で存在できるので残し、
   crossed を新しいトップへ引き継ぐ。

加えて dmc42-001 の条項(b)用に新許可 evolve_civ_any
（permissions.yaml）: _evo_match に _evo_race_waived と対の
_evo_civ_waived（civs / civs_all を除いて照合）を追加した。
条項(a)は既存イディオム（static {affects: crossed, mod:
{allow: [evolve_base_any]}}、第232弾・ラウンド268 dm32-110）。
dmc45-017 のクルー・ブレイカーも既存イディオム（static
{affects: crossed, mod: {breaks: {count: {zone: bz, owner:
you, other: true, filter: {race_has: サムライ, types:
[creature]}}}}}、第130弾・converted のジョーカーズ形）。
スキーマ再生成の差分は allow/deny enum への evolve_civ_any
追加4箇所のみ。

proto: T925 civs形（dmc42-017型）/ T926 races形＋クルー・
ブレイカー（dmc45-017型）/ T927 許可形（dmc42-001型）/
T928 水ギア（進化元）/ T929 サムライ・ギア（進化元）/
T930 サムライ獣 / T931 card_only 回収呪文（再構築の検証用）。
"""
import os

os.environ.setdefault("DMSIM_SKIP_CONVERTED", "1")

import pytest  # noqa: E402

from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402
from tests.conftest import setup  # noqa: E402

TABLES = load_tables()
IDS = ("T925", "T926", "T927", "T928", "T929", "T930", "T931")
OPP = {"deck": ["T002"] * 4}


def _rules():
    return load_rules()


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _cid(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p) if e.s.cards[c].defn == defn)


def _can_play(e, defn, p=0):
    cid = _cid(e, "hand", p, defn)
    return e._can_play_face(cid, p, None)


def _sources(e, defn, p=0):
    cid = _cid(e, "hand", p, defn)
    return e._evo_sources(cid, p, None)


def _answer_default(e, d):
    keys = [o["key"] for o in d["options"]]
    if d["kind"] in ("pay_mana", "choose_evo_source", "choose_cards"):
        e.answer(list(range(d["min"])))
    elif "pass" in keys:
        e.answer([keys.index("pass")])
    else:
        e.answer(list(range(d.get("min", 0))))


def _play_perm(e, defn, max_steps=300):
    """手札から defn（パーマネント）を出し切り、次の main 決定まで進める。"""
    played = False
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith(f"play:{defn}") for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if k.startswith(f"play:{defn}"))])
            played = True
            continue
        if played and d["kind"] == "main" and defn in _defns(e, "bz", 0):
            return
        _answer_default(e, d)
    raise AssertionError(f"{defn} did not complete")


def _cross(e, gear_defn, target_defn, max_steps=200):
    """main で gear_defn を target_defn にクロスし、crossed が付くまで進める。"""
    key = f"cross:{gear_defn}:{target_defn}"
    crossed = False
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and key in keys:
            e.answer([keys.index(key)])
            crossed = True
            continue
        _answer_default(e, d)
        if crossed:
            g = next(c for c in e.zlist("bz", 0)
                     if e.s.cards[c].defn == gear_defn and e.s.cards[c].top_of < 0)
            if e.s.cards[g].crossed:
                return
    raise AssertionError(f"cross {key} did not complete")


def _cast_pick(e, defn, pick_cid, max_steps=300):
    """手札から呪文 defn を唱え、choose_cards では pick_cid を選ぶ。"""
    cast = False
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith(f"play:{defn}") for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if k.startswith(f"play:{defn}"))])
            cast = True
            continue
        if d["kind"] == "choose_cards" and cast:
            idx = next(i for i, o in enumerate(d["options"])
                       if o.get("cid") == pick_cid)
            e.answer([idx])
            continue
        if cast and defn in _defns(e, "graveyard", 0):
            return
        _answer_default(e, d)
    raise AssertionError(f"cast {defn} did not complete")


# ---- parse / 許可の登録 ----

def test_parse_and_permission_registered():
    for cid in IDS:
        parse_card(proto_card(cid), TABLES)
    assert "evolve_civ_any" in _rules().actions
    d = parse_card(proto_card("T925"), TABLES)
    assert d.types == ["cross_gear", "evolution"]
    assert d.evolve_from == {"civs": ["water", "darkness"]}
    d = parse_card(proto_card("T926"), TABLES)
    assert d.evolve_from == {"races": ["サムライ"]}
    # 未知の許可名は検証で弾かれる（permissions.yaml 登録が必須なことの固定）
    bad = proto_card("T927")
    bad["abilities"][1]["mod"] = {"allow": ["evolve_civ_bogus"]}
    with pytest.raises(Exception):
        parse_card(bad, TABLES)


# ---- 進化元プール（civs形） ----

def test_pool_civs_form_requires_matching_cross_gear():
    mana = ["T010", "T008", "T001", "T001"]
    # クリーチャーはギアの進化元にならない（文明が合っていても）
    e = setup(_rules(), {"bz": ["T010"], "hand": ["T925"], "mana": mana}, OPP)
    assert _sources(e, "T925") == [] and not _can_play(e, "T925")
    # 文明の合わないギアは進化元にならない
    e = setup(_rules(), {"bz": ["T062"], "hand": ["T925"], "mana": mana}, OPP)
    assert _sources(e, "T925") == [] and not _can_play(e, "T925")
    # 相手のギアは進化元にならない
    e = setup(_rules(), {"hand": ["T925"], "mana": mana},
              {"bz": ["T928"], "deck": ["T002"] * 4})
    assert _sources(e, "T925") == [] and not _can_play(e, "T925")
    # 水ギアがあれば出せる
    e = setup(_rules(), {"bz": ["T928"], "hand": ["T925"], "mana": mana}, OPP)
    assert _sources(e, "T925") == [_cid(e, "bz", 0, "T928")]
    assert _can_play(e, "T925")


def test_pool_race_form_requires_samurai_cross_gear():
    mana = ["T034", "T001", "T034"]
    # サムライ・クリーチャーはギアの進化元にならない
    e = setup(_rules(), {"bz": ["T930"], "hand": ["T926"], "mana": mana}, OPP)
    assert _sources(e, "T926") == [] and not _can_play(e, "T926")
    # 種族の合わないギアは進化元にならない
    e = setup(_rules(), {"bz": ["T928"], "hand": ["T926"], "mana": mana}, OPP)
    assert _sources(e, "T926") == [] and not _can_play(e, "T926")
    # サムライ・ギアがあれば出せる
    e = setup(_rules(), {"bz": ["T929"], "hand": ["T926"], "mana": mana}, OPP)
    assert _sources(e, "T926") == [_cid(e, "bz", 0, "T929")]
    assert _can_play(e, "T926")


# ---- 実挙動: 重ねてからクロス（civs形） ----

def test_evolve_onto_uncrossed_gear_then_cross():
    mana = ["T010", "T008", "T001", "T001", "T010", "T008", "T001", "T001"]
    e = setup(_rules(), {"bz": ["T928", "T001"], "hand": ["T925"],
                         "mana": mana}, OPP)
    base = _cid(e, "bz", 0, "T928")
    host = _cid(e, "bz", 0, "T001")
    _play_perm(e, "T925")
    top = _cid(e, "bz", 0, "T925")
    assert e.s.cards[base].top_of == top          # 進化元は下になった
    assert base not in e.bz_tops(0)               # 束のトップは進化ギアだけ
    assert e.s.cards[top].under == [base]
    _cross(e, "T925", "T001")
    assert e.s.cards[top].crossed[0] == host
    assert e.chars(host)["power"] == 4000         # 2000（素）+ 2000（T925）


# ---- 実挙動: クロス済みギアへ進化（crossed の引き継ぎ） ----

def _stacked_crossed():
    mana = ["T010", "T008"] + ["T001"] * 8
    e = setup(_rules(), {"bz": ["T928", "T001"], "hand": ["T925", "T931"],
                         "mana": mana}, OPP)
    base = _cid(e, "bz", 0, "T928")
    host = _cid(e, "bz", 0, "T001")
    _cross(e, "T928", "T001")
    assert e.chars(host)["power"] == 3000         # 2000 + 1000（T928）
    _play_perm(e, "T925")
    top = _cid(e, "bz", 0, "T925")
    return e, top, base, host


def test_crossed_inherited_by_evolution_gear():
    e, top, base, host = _stacked_crossed()
    assert e.s.cards[top].crossed[0] == host      # クロス先はトップへ
    assert e.s.cards[base].crossed is None        # 元のギアからは外れる
    assert e.chars(host)["power"] == 4000         # トップの +2000 だけが及ぶ


# ---- 実挙動: トップだけ離れる（_rebuild がギアを残す） ----

def test_rebuild_keeps_base_gear_still_crossed():
    e, top, base, host = _stacked_crossed()
    _cast_pick(e, "T931", top)
    assert e.s.cards[top].zone == "hand"          # トップだけが手札へ
    assert e.s.cards[base].zone == "bz"           # 下のギアは場に残る
    assert e.s.cards[base].top_of < 0             # 束のトップに戻る
    assert e.s.cards[base].crossed[0] == host     # クロスしたまま残る
    assert e.chars(host)["power"] == 3000         # +1000（T928）が再び及ぶ


# ---- 実挙動: クルー・ブレイカー（races形） ----

def _crew_breaks(extra_bz):
    mana = ["T034", "T001", "T034", "T001", "T034", "T001"]
    e = setup(_rules(), {"bz": ["T929", "T001"] + extra_bz,
                         "hand": ["T926"], "mana": mana}, OPP)
    host = _cid(e, "bz", 0, "T001")
    _play_perm(e, "T926")
    _cross(e, "T926", "T001")
    return e.chars(host)["breaks"]


def test_crew_breaker_counts_other_samurai_creatures():
    assert _crew_breaks(["T930", "T930"]) == 3    # 1 + 他のサムライ獣2体
    assert _crew_breaks([]) == 1                 # 数える対象が無ければ1


# ---- 実挙動: レオパルド形（許可2つ） ----

def test_leopald_permits():
    e = setup(_rules(), {"bz": ["T927"], "mana": ["T001"] * 2}, OPP)
    gear = _cid(e, "bz", 0, "T927")
    assert e.permits(gear, "evolve_civ_any")
    e2 = setup(_rules(), {"bz": ["T062"], "mana": ["T001"] * 2}, OPP)
    plain = _cid(e2, "bz", 0, "T062")
    assert not e2.permits(plain, "evolve_civ_any")   # 既定は false


def test_leopald_grants_race_any_to_crossed_creature():
    e = setup(_rules(), {"bz": ["T927", "T001"], "mana": ["T001"] * 4}, OPP)
    host = _cid(e, "bz", 0, "T001")
    assert not e.permits(host, "evolve_base_any")
    _cross(e, "T927", "T001")
    assert e.permits(host, "evolve_base_any")     # クロス先は種族不問の進化元になる


def test_civ_any_lets_evolution_gear_stack_on_nature_gear():
    mana = ["T010", "T008", "T001", "T001"]
    e = setup(_rules(), {"bz": ["T927"], "hand": ["T925"], "mana": mana}, OPP)
    gear = _cid(e, "bz", 0, "T927")
    assert _sources(e, "T925") == [gear]          # 文明（自然）は肩代わりされる
    _play_perm(e, "T925")
    top = _cid(e, "bz", 0, "T925")
    assert e.s.cards[gear].top_of == top
    # 種族指定は肩代わりしない: サムライ形はレオパルド（種族なし）に重ならない
    e2 = setup(_rules(), {"bz": ["T927"], "hand": ["T926"],
                          "mana": ["T034", "T001", "T034"]}, OPP)
    assert _sources(e2, "T926") == [] and not _can_play(e2, "T926")
