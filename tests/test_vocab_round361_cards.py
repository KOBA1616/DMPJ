"""再変換ラウンド361（第326弾 blocked_break）の記録テスト。

- 新規登録2件: dm39-035 カンクロウ・ブラスター /
  dmc34-030 獣達の挽歌。
- alias 畳み込み1件（dmc34-030 の submit 時に aliases [dm13-025]
  を自動記録）・stale クリーンアップ0件・差し戻し0件。
- 対象2行は gaps = [blocked_break] のため reopen で外してから
  submit（reopen は2件とも外れた）。
- converted 10,273→10,275 / rejects 2,043→2,041、
  canonical 重なり0・漏れ0。blocked_break はファミリーが
  この2件だけだったため完全に解消。

登録形は第326弾の確立形と完全一致（submit の連結・merge_split 由来の
混入なし）:
- dm39-035: 3つの継続的効果（power+4000・breaks_add+1／遅延誘発
  block {attacker: own} -> break 1／deny be_chosen by spells）
- dmc34-030: 1つの継続的効果（power+4000 と gain [trigger
  {event: block, attacker: self} -> break 1]）

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

GAP = "blocked_break"

TRIGGER = {"kind": "trigger",
           "when": {"event": "block", "attacker": "self"},
           "effect": [{"op": "break", "player": "opp", "count": 1}]}

FORM_A = [
    {"op": "modify",
     "select": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}, "count": "all"},
     "mod": {"power": 4000, "breaks_add": 1},
     "duration": "end_of_turn"},
    {"op": "delayed_trigger",
     "when": {"event": "block",
              "attacker": {"owner": "you",
                           "filter": {"types": ["creature"]}}},
     "effect": [{"op": "break", "player": "opp", "count": 1}],
     "duration": "end_of_turn", "once": False},
    {"op": "modify",
     "select": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}, "count": "all"},
     "mod": {"deny": [{"action": "be_chosen",
                       "other": {"types": ["spell"]}}]},
     "duration": "end_of_turn"},
]

FORM_B = [
    {"op": "modify",
     "select": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}, "count": "all"},
     "mod": {"power": 4000, "gain": [TRIGGER]},
     "duration": "end_of_turn"},
]


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


def test_round361_disposition():
    rej = _reject_rows()
    assert len(rej) == 2041
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10275
    assert not (ids & set(rej))          # canonical 重なり0
    for tid in ("dm39-035", "dmc34-030"):
        assert tid in ids and tid not in rej, tid
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None
        assert not (c.get("source") or {}).get("unsupported")
    c035 = _conv_cache.find(CONVERTED, "dm39-035")
    assert c035["spell"] == FORM_A
    assert not (c035.get("source") or {}).get("aliases")
    d = parse_card(c035, TABLES)
    assert len(d.spell) == 3
    c030 = _conv_cache.find(CONVERTED, "dmc34-030")
    assert c030["spell"] == FORM_B
    assert (c030.get("source") or {}).get("aliases") == ["dm13-025"]
    d = parse_card(c030, TABLES)
    assert len(d.spell) == 1
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


def _cast_spell(e, cid, mana_n):
    """main で指定の呪文を唱える（コストは mana_n 枚の T001 で払う。
    自然の呪文には自然のマナが要る）。唱えた時点で戻る。"""
    cast = False
    for _ in range(120):
        d = e.advance()
        assert d is not None, "game ended before cast"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and not cast \
                and f"play:{cid}" in keys:
            e.answer([keys.index(f"play:{cid}")])
            cast = True
            continue
        if cast and d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if cast and d["kind"] in ("charge", "main", "attack"):
            return
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("spell did not resolve")


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


def _drive_combat(e, block=False, max_steps=200):
    for _ in range(max_steps):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main", "attack"):
            return
        keys = _keys(d)
        if d["kind"] == "block":
            if block:
                guard = next((i for i, k in enumerate(keys)
                              if k != "no_block"), None)
                assert guard is not None, keys
                e.answer([guard])
            elif "no_block" in keys:
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


def test_registered_030_granted_trigger_breaks(rules):
    """登録形: dmc34-030 を唱えると自分のクリーチャーはパワー+4000
    され、ブロックされた攻撃で相手のシールドを1枚割る。
    ブロックされなかった攻撃では余分に割らない。"""
    e = _build(rules, {"bz": ["T001", "T002"],
                       "hand": ["dmc34-030"], "mana": ["T001"] * 4},
               {"bz": ["T004"]})
    for dfn in ("T001", "T002"):
        e.s.cards[_bz(e, 0, dfn)].entered_turn = -1
    _cast_spell(e, "dmc34-030", 4)
    assert e.chars(_bz(e, 0, "T001"))["power"] == 6000
    before = len(e.zlist("shield", 1))
    _attack_player(e, "T001")
    _drive_combat(e, block=True)
    assert len(e.zlist("shield", 1)) == before - 1
    before = len(e.zlist("shield", 1))
    _attack_player(e, "T002")
    _drive_combat(e)
    assert len(e.zlist("shield", 1)) == before - 1


def test_registered_035_delayed_trigger_breaks(rules):
    """登録形: dm39-035 を唱えると自分のクリーチャーはパワー+4000・
    さらに1枚ブレイクし、ブロックされた攻撃で相手のシールドを
    1枚割る。2回目のブロックでも割る（once: false）。"""
    e = _build(rules, {"bz": ["T001", "T002"],
                       "hand": ["dm39-035"], "mana": ["T001"] * 6},
               {"bz": ["T004", "T004"]})
    for dfn in ("T001", "T002"):
        e.s.cards[_bz(e, 0, dfn)].entered_turn = -1
    _cast_spell(e, "dm39-035", 6)
    assert e.chars(_bz(e, 0, "T001"))["power"] == 6000
    before = len(e.zlist("shield", 1))
    _attack_player(e, "T001")
    _drive_combat(e, block=True)
    assert len(e.zlist("shield", 1)) == before - 1
    before = len(e.zlist("shield", 1))
    _attack_player(e, "T002")
    _drive_combat(e, block=True)
    assert len(e.zlist("shield", 1)) == before - 1


def test_registered_035_deny_be_chosen_by_spells(rules):
    """登録形: dm39-035 を唱えたターン、自分のクリーチャーは相手の
    呪文に選ばれない。クリーチャーの効果からの選択は妨げない。"""
    e = _build(rules, {"bz": ["T001"], "hand": ["dm39-035"],
                       "mana": ["T001"] * 6},
               {"hand": ["T006"], "bz": ["T004"]})
    t001 = _bz(e, 0, "T001")
    t006 = next(c for c in e.zlist("hand", 1)
                if e.s.cards[c].defn == "T006")
    t004 = _bz(e, 1, "T004")
    assert e.permits(t001, "be_chosen", other=t006)
    _cast_spell(e, "dm39-035", 6)
    assert not e.permits(t001, "be_chosen", other=t006)
    assert e.permits(t001, "be_chosen", other=t004)
