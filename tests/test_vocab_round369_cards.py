"""再変換ラウンド369（第334弾 play_from_deck_top）の記録テスト。

- 新規登録2件: dm22rp2x-002 アカシック・ヴィジョン /
  dm26sd1-j009 斬龍電融 オロチリュウセイ。いずれも登録形は
  確立形と完全一致。
- alias 畳み込み0件（submit 時に 002 へ aliases 2件・j009 へ
  3件が自動記録されたが rejects 行ではない）・差し戻し0件
  （submit 時の警告なし）。
- converted 10,286→10,288 / rejects 2,028→2,026、
  canonical 重なり0・漏れ0。play_from_deck_top は multi の
  dmrp22-005（reveal_stay 複合）だけが残る。

実挙動は登録カード自身で固定する（山札の上の呪文を唱える、
山札の上のクリーチャーを召喚する＝1体まで）。ドライバは
scenario.build の薄い包みで、tests.conftest は import しない
（第319弾以降の作法）。山札の上は zlist("deck", p)[0]。
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

ALLOW_002 = {
    "kind": "static",
    "affects": {"zone": "deck", "owner": "you",
                "filter": {"types": ["spell", "tamaseed"]}},
    "if": {"is_turn": "you"},
    "mod": {"allow": [{"action": "cast_from_deck_top"},
                      {"action": "generate_from_deck_top"}]}}

SPEED_ALL = {
    "kind": "static",
    "affects": {"owner": "you", "filter": {"types": ["creature"]}},
    "mod": {"grant": ["speed_attacker"]}}

ALLOW_J009 = {
    "kind": "static",
    "affects": {"zone": "deck", "owner": "you",
                "filter": {"types": ["creature"]}},
    "if": {"is_turn": "you"},
    "mod": {"allow": [{"action": "summon_from_deck_top", "once": True}]}}

FORM_002 = [ALLOW_002]
FORM_J009 = [SPEED_ALL, ALLOW_J009]


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


def test_round369_disposition():
    rej = _reject_rows()
    assert len(rej) == 2026
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10288
    assert not (ids & set(rej))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dm22rp2x-002")
    assert c is not None and c["abilities"] == FORM_002
    assert (c.get("source") or {}).get("aliases") == ["dm22rp2-002",
                                                     "dm22rp2x-002x"]
    c = _conv_cache.find(CONVERTED, "dm26sd1-j009")
    assert c is not None and c["abilities"] == FORM_J009
    assert (c.get("source") or {}).get("aliases") == ["dm23bd6-017",
                                                     "dm25sp2-005",
                                                     "dmrp17-s11"]
    for t in ("dm22rp2x-002", "dm26sd1-j009"):
        cc = _conv_cache.find(CONVERTED, t)
        assert not (cc.get("source") or {}).get("unsupported")
        parse_card(cc, TABLES)
    left = {rid for rid, r in rej.items()
            if "play_from_deck_top" in (r.get("gaps") or [])}
    assert left == {"dmrp22-005"}, left    # multi のため残る


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _in_zone(e, p, zone, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def _set_deck_top(e, p, defn):
    deck = e.s.zones["deck"][p]
    cid = next(c for c in deck if e.s.cards[c].defn == defn)
    deck.remove(cid)
    deck.insert(0, cid)
    return cid


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


def test_registered_vision_casts_top_spell(rules):
    e = _build(rules, {"bz": ["dm22rp2x-002"], "mana": ["T009"] * 2,
                       "deck": ["T003"]}, {})
    _set_deck_top(e, 0, "T003")
    assert "play:T003:dtop" in [o["key"] for o in e._play_options(0)]
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and "play:T003:dtop" in keys:
            e.answer([keys.index("play:T003:dtop")])
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    else:
        raise AssertionError("did not reach main")
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] in ("charge", "main", "attack"):
            break
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert _in_zone(e, 0, "graveyard", "T003")


def test_registered_orochi_summons_once(rules):
    e = _build(rules, {"bz": ["dm26sd1-j009"], "mana": ["T001"] * 4,
                       "deck": ["T001", "T001"]}, {})
    _set_deck_top(e, 0, "T001")
    deck = e.s.zones["deck"][0]
    second = next(c for c in deck if e.s.cards[c].defn == "T001")
    deck.remove(second)
    deck.insert(1, second)
    assert "play:T001:dtop" in [o["key"] for o in e._play_options(0)]
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and "play:T001:dtop" in keys:
            e.answer([keys.index("play:T001:dtop")])
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    else:
        raise AssertionError("did not reach main")
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] in ("charge", "main", "attack"):
            break
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert _in_zone(e, 0, "bz", "T001")
    assert "play:T001:dtop" not in [o["key"] for o in e._play_options(0)]
    _drive_to(e, "charge", 0)
    assert "play:T002:dtop" in [o["key"] for o in e._play_options(0)]
