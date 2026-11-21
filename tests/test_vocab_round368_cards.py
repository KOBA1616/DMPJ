"""再変換ラウンド368（第333弾 power_transfer）の記録テスト。

- 新規登録2件: dm24rp4-045 ブルーアイズ・ドラゴンフライ /
  dmrp11-zs01 零。いずれも登録形は確立形と完全一致。
- alias 畳み込み0件・差し戻し0件（submit 時の警告なし）。
- converted 10,284→10,286 / rejects 2,030→2,028、
  canonical 重なり0・漏れ0。power_transfer は残り0件で
  ファミリー解消。

実挙動は登録カード自身で固定する（コスト6以上のクリーチャー
が出た時のパワー加算、攻撃時のパワー吸い上げと 0 化、ターン
終わりの手札破棄、零龍がいる間のコスト軽減）。ドライバは
scenario.build の薄い包みで、tests.conftest は import しない
（第319弾以降の作法）。
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

TRIGGER_045 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "you",
                         "filter": {"types": ["creature"],
                                    "cost_ge": 6}}},
    "effect": [{"op": "modify", "select": {"ref": "event.subject"},
                "mod": {"power": {"amount": {"power_of": {"ref": "self"}}}},
                "duration": "until_next_own_turn_start"}]}

TRANSFER = {
    "kind": "trigger", "when": {"event": "attack", "subject": "self"},
    "effect": [
        {"op": "choose",
         "select": {"zone": "bz", "owner": "opp",
                    "filter": {"types": ["creature"]}, "count": 1},
         "as": "victim"},
        {"op": "modify", "select": {"ref": "self"},
         "mod": {"power": {"amount": {"power_of": {"ref": "victim"}}}},
         "duration": "end_of_turn"},
        {"op": "modify", "select": {"ref": "victim"},
         "mod": {"power_set": 0}, "duration": "end_of_turn"}]}

END_DISCARD = {
    "kind": "trigger", "when": {"event": "turn_end"},
    "if": {"is_turn": "you"},
    "effect": [{"op": "discard",
                "select": {"zone": "hand", "owner": "opp",
                           "chooser": "opp", "count": 1}}]}

COST_CUT = {
    "kind": "static",
    "affects": {"zone": "hand", "owner": "you",
                "filter": {"civs": ["darkness"]}},
    "if": {"exists": {"zone": "bz", "owner": "you",
                      "filter": {"race_has": "零龍"}}},
    "mod": {"cost": -1, "cost_min": 0}}

FORM_045 = [TRIGGER_045]
FORM_0S01 = [TRANSFER, END_DISCARD, COST_CUT]


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


def test_round368_disposition():
    rej = _reject_rows()
    assert len(rej) == 2028
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10286
    assert not (ids & set(rej))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dm24rp4-045")
    assert c is not None and c["abilities"] == FORM_045
    assert not (c.get("source") or {}).get("aliases")
    c = _conv_cache.find(CONVERTED, "dmrp11-zs01")
    assert c is not None and c["abilities"] == FORM_0S01
    assert not (c.get("source") or {}).get("aliases")
    for t in ("dm24rp4-045", "dmrp11-zs01"):
        cc = _conv_cache.find(CONVERTED, t)
        assert not (cc.get("source") or {}).get("unsupported")
        parse_card(cc, TABLES)
    left = {rid for rid, r in rej.items()
            if "power_transfer" in (r.get("gaps") or [])}
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


def _in_zone(e, p, zone, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def _drive_to(e, kind, player):
    for _ in range(400):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] == kind and d.get("player") == player:
            return d
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError(f"did not reach {kind} p{player}")


def test_registered_dragonfly_transfers(rules):
    e = _build(rules, {"bz": ["dm24rp4-045"], "hand": ["T142"],
                       "mana": ["T001"] * 7}, {})
    played = False
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and "play:T142" in keys:
            e.answer([keys.index("play:T142")])
            played = True
            continue
        if played and d["kind"] in ("charge", "main", "attack"):
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert played and _in_zone(e, 0, "bz", "T142")
    assert e.chars(_bz(e, 0, "T142"))["power"] == 14000
    _drive_to(e, "main", 0)
    assert e.chars(_bz(e, 0, "T142"))["power"] == 13000


def test_registered_zero_drains(rules):
    e = _build(rules, {"bz": ["dmrp11-zs01"]}, {"bz": ["T004"]})
    t = _bz(e, 0, "dmrp11-zs01")
    e.s.cards[t].entered_turn = -1
    attacked = False
    checked = False
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 and not attacked \
                and "attack:dmrp11-zs01:player" in keys:
            e.answer([keys.index("attack:dmrp11-zs01:player")])
            attacked = True
            continue
        if attacked and not checked:
            assert e.chars(_bz(e, 0, "dmrp11-zs01"))["power"] == 8000
            assert _in_zone(e, 1, "graveyard", "T004")
            checked = True
        if attacked and d["kind"] in ("charge", "main", "attack"):
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert attacked and checked
    _drive_to(e, "charge", 0)
    assert e.chars(_bz(e, 0, "dmrp11-zs01"))["power"] == 5000
