"""再変換ラウンド360（第325弾 breaks_reduction）の記録テスト。

- 新規登録2件: dmr21-007 九極の精霊 マウリエル /
  dm23rp1-004 終納 カボード＝ロウ。
- alias 畳み込み0件・stale クリーンアップ0件・差し戻し0件。
- 対象2行は gaps = [breaks_reduction] のため reopen で外してから
  submit（reopen は2件とも外れた）。
- converted 10,271→10,273 / rejects 2,045→2,043、
  canonical 重なり0・漏れ0。breaks_reduction はファミリーが
  この2件だけだったため完全に解消。

登録形は第325弾の確立形と完全一致（submit の連結・merge_split 由来の
混入なし）:
- dmr21-007: {kind: static,
  affects: {owner: opp, filter: {types: [creature]}},
  mod: {breaks_add: -1}}（keywords [blocker, triple_breaker]）
- dm23rp1-004: {kind: static,
  affects: {owner: opp, filter: {types: [creature], tapped: true}},
  mod: {power: -5000, breaks_add: -1}}＋アビスの常在型
  {owner: you, other: true, filter: {race_has: アビス}}
  {power: 5000, grant: [powered_breaker]}
  （keywords [triple_breaker, abyss_rush]）

実挙動は登録カード自身で固定する。ドライバは scenario.build の薄い包みで、
tests.conftest は import しない（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

GAP = "breaks_reduction"

FORM_A = {"kind": "static",
          "affects": {"owner": "opp", "filter": {"types": ["creature"]}},
          "mod": {"breaks_add": -1}}
FORM_B = {"kind": "static",
          "affects": {"owner": "opp",
                      "filter": {"types": ["creature"], "tapped": True}},
          "mod": {"power": -5000, "breaks_add": -1}}
FORM_B2 = {"kind": "static",
           "affects": {"owner": "you", "other": True,
                       "filter": {"race_has": "アビス"}},
           "mod": {"power": 5000, "grant": ["powered_breaker"]}}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_round360_disposition():
    rej = _reject_rows()
    assert len(rej) == 2043
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10273
    assert not (ids & set(rej))          # canonical 重なり0
    for tid in ("dmr21-007", "dm23rp1-004"):
        assert tid in ids and tid not in rej, tid
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None
        assert not (c.get("source") or {}).get("unsupported")
        assert not (c.get("source") or {}).get("aliases")
    c007 = _conv_cache.find(CONVERTED, "dmr21-007")
    assert c007["abilities"] == [FORM_A]
    assert c007["keywords"] == ["blocker", "triple_breaker"]
    d = parse_card(c007, TABLES)
    assert FORM_A in d.abilities
    c004 = _conv_cache.find(CONVERTED, "dm23rp1-004")
    assert c004["abilities"] == [FORM_B, FORM_B2]
    assert c004["keywords"] == ["triple_breaker", "abyss_rush"]
    d = parse_card(c004, TABLES)
    assert FORM_B in d.abilities and FORM_B2 in d.abilities
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _attack_player(e, attacker_defn, player=0):
    for _ in range(120):
        d = e.advance()
        assert d is not None, "game ended before attack"
        if d["kind"] == "attack" and d.get("player") == player:
            keys = _keys(d)
            e.answer([keys.index(f"attack:{attacker_defn}:player")])
            return
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys
                 else list(range(d["min"])))
    raise AssertionError("attack decision did not appear")


def _drive_combat(e, max_steps=200):
    for _ in range(max_steps):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main", "attack"):
            return
        keys = _keys(d)
        if d["kind"] == "block":
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("combat did not settle")


def test_registered_007_opponent_breaks_zero(rules):
    """登録形: dmr21-007 がいる時、相手の単体ブレイカーはシールドを
    割らない。対照: マウリエル自身は3枚割る。"""
    e = _build(rules, {"bz": ["dmr21-007"]}, {"bz": ["T001"]})
    e.s.cards[_bz(e, 0, "dmr21-007")].entered_turn = -1
    e.s.cards[_bz(e, 1, "T001")].entered_turn = -1
    before = len(e.zlist("shield", 0))
    _attack_player(e, "T001", player=1)
    _drive_combat(e)
    assert len(e.zlist("shield", 0)) == before
    before = len(e.zlist("shield", 1))
    _attack_player(e, "dmr21-007")
    _drive_combat(e)
    assert len(e.zlist("shield", 1)) == before - 3


def test_registered_004_tapped_loses_power(rules):
    """登録形: dm23rp1-004 がいる時、相手のタップしている
    クリーチャーはパワー-5000。アンタップしている同じ
    クリーチャーには効かない。"""
    e = _build(rules, {"bz": ["dm23rp1-004"]}, {"bz": ["T142", "T142"]})
    t142s = [c for c in e.bz_tops(1)
             if e.s.cards[c].defn == "T142"]
    assert len(t142s) == 2
    e.s.cards[t142s[0]].tapped = True
    assert e.chars(t142s[0])["power"] == 8000
    assert e.chars(t142s[1])["power"] == 13000


def test_registered_004_attack_breaks_one_less(rules):
    """登録形: dm23rp1-004 がいる時、相手のクリーチャーが攻撃すると
    攻撃の宣言でタップされるため1枚少なくブレイクする。
    対照: カボード＝ロウがいなければ1枚割る。"""
    e = _build(rules, {"bz": ["dm23rp1-004"]}, {"bz": ["T142"]})
    e.s.cards[_bz(e, 1, "T142")].entered_turn = -1
    before = len(e.zlist("shield", 0))
    _attack_player(e, "T142", player=1)
    _drive_combat(e)
    assert len(e.zlist("shield", 0)) == before
    e = _build(rules, {}, {"bz": ["T142"]})
    e.s.cards[_bz(e, 1, "T142")].entered_turn = -1
    before = len(e.zlist("shield", 0))
    _attack_player(e, "T142", player=1)
    _drive_combat(e)
    assert len(e.zlist("shield", 0)) == before - 1
