"""再変換ラウンド339（第304弾 evolution_cross_gear）の記録テスト。

- 新規登録4件: dmc42-017（ツナミ・カタストロフィー、civs形）/
  dmc45-017（龍刃 ヤマト・スピリット、races形＋クルー・
  ブレイカー）/ dm17-s05（グランドクロス・カタストロフィー、
  civs形）/ dmc42-001（レオパルド・グローリーソード、許可2つ。
  第2ギャップ evolution_base_any_race は第232弾で実装済み）。
- alias 畳み込み・stale 解消・converted 是正は0件。alias は
  登録カードの source.aliases に記録されただけ（dm17-003 →
  dmc42-017、promoy4-024 → dmc42-001。どちらも reject 行は
  元々無かった）。
- 正本判定は identity の実データ照合による: 対象4件はいずれも
  canon_id が自身＝独立正本。canon_id(dm17-003) = dmc42-017、
  canon_id(promoy4-024) = dmc42-001 で、partial の
  source.aliases とも一致する。
- 差し戻し0件。converted 10,237→10,241 / rejects
  2,084→2,080、重なり0・漏れ0。evolution_cross_gear の
  純粋行は解消（ギャップ名自体は他ギャップ併記の3行
  dmc66-034 / dm17-004 / dm17-s04 に残る）。

登録形は第304弾の確立形（partial ＋ types [cross_gear,
evolution] ＋ evolve_from、dmc45-017 はクルー常在型を追加、
dmc42-001 は types 据え置きで常在型2つ）と完全一致（submit の
連結・merge_split 由来の混入なし）。text は reject 行の正式
本文へ復元した（partial は「マナゾーンに置く時」行が欠落）。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない（第319弾以降の
作法）。進化元ギアには第304弾プロト T928（水ギア）/ T929
（サムライ・ギア）、サムライ獣に T930 を使う。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402


TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

G42 = "dmc42-017"
G45 = "dmc45-017"
S05 = "dm17-s05"
L01 = "dmc42-001"
TARGETS = (G42, G45, S05, L01)

CREW_STATIC = {"kind": "static", "affects": "crossed",
               "mod": {"breaks": {"count": {
                   "zone": "bz", "owner": "you", "other": True,
                   "filter": {"race_has": "サムライ",
                              "types": ["creature"]}}}}}

ABILITIES = {
    G42: [
        {"kind": "static", "affects": "crossed", "mod": {"power": 2000}},
        {"kind": "trigger",
         "when": {"event": "attack", "subject": "crossed"},
         "effect": [
             {"op": "repeat", "times": 2,
              "body": [{"op": "may", "body": [{"op": "draw", "count": 1}]}]},
             {"op": "discard",
              "select": {"zone": "hand", "owner": "opp", "count": 2,
                         "chooser": "opp"}}]}],
    G45: [
        {"kind": "trigger",
         "when": {"event": "battle_win", "subject": "crossed"},
         "effect": [{"op": "may",
                     "body": [{"op": "untap",
                               "select": {"ref": "crossed"}}]}]},
        CREW_STATIC],
    S05: [
        {"kind": "static", "affects": "crossed",
         "mod": {"grant": ["blocker"]}},
        {"kind": "replace",
         "when": {"event": "move", "from": "bz", "to": "graveyard",
                  "reason": "destroy", "subject": "crossed"},
         "instead": []},
        {"kind": "trigger",
         "when": {"event": "turn_end", "player": "you"},
         "effect": [{"op": "untap", "select": {"ref": "crossed"}}]}],
    L01: [
        {"kind": "static", "affects": "crossed",
         "mod": {"allow": ["evolve_base_any"]}},
        {"kind": "static", "affects": "self",
         "mod": {"allow": ["evolve_civ_any"]}}],
}

TYPES = {G42: ["cross_gear", "evolution"],
         G45: ["cross_gear", "evolution"],
         S05: ["cross_gear", "evolution"],
         L01: ["cross_gear"]}
EVO_FROM = {G42: {"civs": ["water", "darkness"]},
            G45: {"races": ["サムライ"]},
            S05: {"civs": ["light", "nature"]},
            L01: None}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_round339_disposition():
    rej = _reject_rows()
    assert len(rej) == 2080
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10241
    assert not (ids & set(rej))          # canonical 重なり0
    for tid in TARGETS:
        c = _conv(tid)
        assert c is not None, tid
        assert not (c.get("source") or {}).get("unsupported"), tid
        assert c["types"] == TYPES[tid], tid
        assert c.get("evolve_from") == EVO_FROM[tid], tid
        # 登録形の完全一致（連結・merge_split 由来の混入なし）
        assert c["abilities"] == ABILITIES[tid], tid
        assert c.get("keywords") is None, tid
        parse_card(c, TABLES)
        assert tid not in rej, tid       # 漏れ0
    # text は reject 行の正式本文（「マナゾーンに置く時」行を含む）
    assert _conv(G42)["text"].startswith("マナゾーンに置く時")
    assert _conv(G45)["text"].startswith("マナゾーンに置く時")
    assert _conv(S05)["text"].startswith("このクロスギアはマナゾーンに")
    assert _conv(L01)["text"].startswith("クロスギア")
    # alias は source.aliases に記録（独立エントリ・reject 行なし）
    assert (_conv(G42).get("source") or {}).get("aliases") == ["dm17-003"]
    assert (_conv(L01).get("source") or {}).get("aliases") == ["promoy4-024"]
    for a in ("dm17-003", "promoy4-024"):
        assert _conv(a) is None, a
        assert a not in rej, a
    assert (_conv(G45).get("source") or {}).get("aliases") is None
    assert (_conv(S05).get("source") or {}).get("aliases") is None
    # 純粋行は解消。ギャップ名は他ギャップ併記の3行にだけ残る
    holders = {rid for rid, r in rej.items()
               if "evolution_cross_gear" in (r.get("gaps") or [])}
    assert holders == {"dmc66-034", "dm17-004", "dm17-s04"}, holders


# ---------- 実挙動ドライバ ----------

def _defns(e, zone, p=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _cid(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p) if e.s.cards[c].defn == defn)


def _build(rules, p0, p1):
    spec0 = dict(p0)
    spec1 = dict(p1)
    spec0.setdefault("deck", ["T002"] * 6)
    spec1.setdefault("deck", ["T002"] * 6)
    return scenario.build(
        rules, {"p0": spec0, "p1": spec1, "filler": "T001", "seed": 1,
                "deck_exact": [True, True]})


def _answer_default(e, d):
    keys = [o["key"] for o in d["options"]]
    if d["kind"] in ("pay_mana", "choose_evo_source", "choose_cards"):
        e.answer(list(range(d["min"])))
    elif d["kind"] == "block":
        e.answer([keys.index("no_block")])
    elif d["kind"] == "declare_strigger":
        e.answer([])
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
        if d["kind"] == "main" and any(k.startswith(f"play:{defn}")
                                       for k in keys):
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
                     if e.s.cards[c].defn == gear_defn
                     and e.s.cards[c].top_of < 0)
            if e.s.cards[g].crossed:
                return
    raise AssertionError(f"cross {key} did not complete")


# ---------- 実挙動（登録形） ----------

def test_registered_civs_form_evolves_and_powers_host(rules):
    """dmc42-017: 水ギアへ進化し、クロス先のパワーが +2000 される。"""
    mana = ["T010", "T008", "T001", "T001"]
    e = _build(rules, {"bz": ["T928", "T001"], "hand": [G42],
                       "mana": mana}, {})
    base = _cid(e, "bz", 0, "T928")
    host = _cid(e, "bz", 0, "T001")
    _play_perm(e, G42)
    top = _cid(e, "bz", 0, G42)
    assert e.s.cards[base].top_of == top
    assert e.s.cards[top].under == [base]
    _cross(e, G42, "T001")
    assert e.s.cards[top].crossed[0] == host
    assert e.chars(host)["power"] == 4000     # 2000（素）+ 2000


def test_registered_crew_breaker_counts_other_samurai(rules):
    """dmc45-017: クロス先のブレイク数は他のサムライ獣の数だけ増える。"""
    mana = ["T034", "T001", "T034"]
    e = _build(rules, {"bz": ["T929", "T001", "T930", "T930"],
                       "hand": [G45], "mana": mana}, {})
    host = _cid(e, "bz", 0, "T001")
    _play_perm(e, G45)
    _cross(e, G45, "T001")
    assert e.chars(host)["breaks"] == 3      # 1 + 他のサムライ獣2体


def test_registered_leopald_permits(rules):
    """dmc42-001: 自身に evolve_civ_any、クロス先に evolve_base_any。"""
    e = _build(rules, {"bz": [L01, "T001"], "mana": ["T001"] * 2}, {})
    gear = _cid(e, "bz", 0, L01)
    host = _cid(e, "bz", 0, "T001")
    e.advance()
    assert e.permits(gear, "evolve_civ_any")
    assert not e.permits(host, "evolve_base_any")
    _cross(e, L01, "T001")
    assert e.permits(host, "evolve_base_any")


def test_registered_leopald_civ_any_accepts_water_darkness_gear(rules):
    """dmc42-001 条項(b): 文明の合わない進化クロスギアも上に置ける。"""
    mana = ["T010", "T008", "T001", "T001"]
    e = _build(rules, {"bz": [L01], "hand": [G42], "mana": mana}, {})
    gear = _cid(e, "bz", 0, L01)
    _play_perm(e, G42)
    top = _cid(e, "bz", 0, G42)
    assert e.s.cards[gear].top_of == top     # 自然ギアの上に水/闇ギア
    assert e.s.cards[top].under == [gear]
