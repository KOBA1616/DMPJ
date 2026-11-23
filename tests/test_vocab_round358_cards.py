"""再変換ラウンド358（第323弾 unblocked_condition）の記録テスト。

- 新規登録2件: dmx04-011 ケロディ二郎 / dmx09-049 誕生の祈。
- alias 畳み込み0件（dmx09-049 の同名再録3件 dm09-054 / dmc34-053 /
  dmc39-031 は submit 時に source.aliases へ記録されたが、この3件は
  rejects に元々無く、rejects 行の畳み込みではない）。
  stale クリーンアップ0件・差し戻し0件。
- 対象2行は gaps = [unblocked_condition] のため reopen で外してから
  submit（reopen は2件とも外れた）。
- converted 10,268→10,270 / rejects 2,049→2,047、
  canonical 重なり0・漏れ0。unblocked_condition はファミリーが
  この2件だけだったため完全に解消。

登録形は第323弾の確立形と完全一致（submit の連結・merge_split 由来の
混入なし）:
- dmx04-011: trigger {event: attack_end, subject: self, target: player,
  blocked: false} → may [move {zone: bz, owner: any,
  filter: {types: [creature]}, count: 1} to hand, reason: return]
- dmx09-049: 同じ when → may [choose {zone: deck, owner: you,
  look: true, filter: {types: [creature]}, count: 1} as t;
  move {ref: t, count: all} to hand, reason: draw; shuffle]

実挙動は登録カード自身で固定する。ドライバは scenario.build の薄い包みで、
tests.conftest は import しない（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

GAP = "unblocked_condition"

FORM_A = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "may", "body": [
        {"op": "move",
         "select": {"zone": "bz", "owner": "any",
                    "filter": {"types": ["creature"]}, "count": 1},
         "to": "hand", "reason": "return"}]}]}
FORM_B = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "may", "body": [
        {"op": "choose",
         "select": {"zone": "deck", "owner": "you", "look": True,
                    "filter": {"types": ["creature"]}, "count": 1},
         "as": "t"},
        {"op": "move", "select": {"ref": "t", "count": "all"},
         "to": "hand", "reason": "draw"},
        {"op": "shuffle"}]}]}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_round358_disposition():
    rej = _reject_rows()
    assert len(rej) == 2047
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10270
    assert not (ids & set(rej))          # canonical 重なり0
    for tid in ("dmx04-011", "dmx09-049"):
        assert tid in ids and tid not in rej, tid
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None
        assert not (c.get("source") or {}).get("unsupported")
    c011 = _conv_cache.find(CONVERTED, "dmx04-011")
    assert c011["abilities"] == [FORM_A]
    assert not (c011.get("source") or {}).get("aliases")
    d011 = parse_card(c011, TABLES)
    assert FORM_A in d011.abilities
    c049 = _conv_cache.find(CONVERTED, "dmx09-049")
    assert c049["abilities"] == [FORM_B]
    assert (c049.get("source") or {}).get("aliases") == [
        "dm09-054", "dmc34-053", "dmc39-031"]
    d49 = parse_card(c049, TABLES)
    assert FORM_B in d49.abilities
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


def _attack_player(e, attacker_defn):
    for _ in range(20):
        d = e.advance()
        assert d is not None, "game ended before attack"
        if d["kind"] == "attack":
            keys = _keys(d)
            e.answer([keys.index(f"attack:{attacker_defn}:player")])
            return
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys
                 else list(range(d["min"])))
    raise AssertionError("attack decision did not appear")


def _drive_combat(e, block=False, may_yes=True, choose_key=None,
                  max_steps=200):
    for _ in range(max_steps):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main", "attack"):
            return d
        keys = _keys(d)
        if d["kind"] == "block":
            guard = next((i for i, k in enumerate(keys)
                          if k != "no_block"), None)
            if block and guard is not None:
                e.answer([guard])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("yes" if may_yes else "no")])
        elif d["kind"] == "choose_cards":
            if choose_key is not None:
                hit = [i for i, k in enumerate(keys)
                       if k.startswith(choose_key)]
                assert hit, keys
                e.answer([hit[0]])
            else:
                e.answer(list(range(d["min"])))
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("combat did not settle")


def test_registered_011_bounces_opponent_creature(rules):
    """登録形: dmx04-011 がブロックされずに攻撃すると、相手の
    クリーチャーを手札に戻せる（owner: any のため相手も選べる）。"""
    e = _build(rules, {"bz": ["dmx04-011"]}, {"bz": ["T004"]})
    e.s.cards[_bz(e, 0, "dmx04-011")].entered_turn = -1
    t004 = _bz(e, 1, "T004")
    _attack_player(e, "dmx04-011")
    _drive_combat(e, choose_key="bz:T004:")
    assert e.s.cards[t004].zone == "hand"
    assert e.s.cards[t004].owner == 1
    assert len(e.bz_tops(1)) == 0


def test_registered_011_blocked_no_bounce(rules):
    """登録形: ブロックされた攻撃では発火しない（判別）。"""
    e = _build(rules, {"bz": ["dmx04-011"]}, {"bz": ["T004"]})
    e.s.cards[_bz(e, 0, "dmx04-011")].entered_turn = -1
    _attack_player(e, "dmx04-011")
    _drive_combat(e, block=True)
    assert len(e.bz_tops(1)) == 1


def test_registered_049_searches_creature_to_hand(rules):
    """登録形: dmx09-049 がブロックされずに攻撃すると、山札から
    クリーチャーを1体手札に加えられる（山札は T002 で満たされている）。"""
    e = _build(rules, {"bz": ["dmx09-049"]}, {})
    e.s.cards[_bz(e, 0, "dmx09-049")].entered_turn = -1
    before = len(e.zlist("hand", 0))
    deck_before = len(e.zlist("deck", 0))
    _attack_player(e, "dmx09-049")
    _drive_combat(e)
    assert len(e.zlist("hand", 0)) == before + 1
    assert len(e.zlist("deck", 0)) == deck_before - 1


def test_registered_049_blocked_no_search(rules):
    """登録形: ブロックされた攻撃では発火しない（判別）。"""
    e = _build(rules, {"bz": ["dmx09-049"]}, {"bz": ["T004"]})
    e.s.cards[_bz(e, 0, "dmx09-049")].entered_turn = -1
    before = len(e.zlist("hand", 0))
    deck_before = len(e.zlist("deck", 0))
    _attack_player(e, "dmx09-049")
    _drive_combat(e, block=True)
    assert len(e.zlist("hand", 0)) == before
    assert len(e.zlist("deck", 0)) == deck_before
