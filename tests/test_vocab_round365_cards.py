"""再変換ラウンド365（第330弾 destroyed_while_tapped）の記録テスト。

- 新規登録1件: dmr18-s04 超復讐 ギャロウィン。
- stale クリーンアップ1件: dm26ex1-021 の rejects 行（非正本。
  正本 dm26rp3-tr005 は既に登録済みだった）。submit は
  dm26ex1-021 を「取得済みの原文に無いID」で弾いた（load_rows は
  正本に畳み込むため）。
- 登録済みカードの修正1件: dm26rp3-tr005 の2条項（破壊時誘発と
  battle_power）が実挙動で不発だったため第330弾の形に差し替え。
- alias 畳み込み0件・差し戻し0件。
- converted 10,279→10,280 / rejects 2,036→2,034、
  canonical 重なり0・漏れ0。destroyed_while_tapped は残り0件で
  ファミリー解消。

実挙動は登録カード自身で固定する（駆動には proto T1003 の破壊
呪文と T1004 のブロッカーを使う）。ドライバは scenario.build の
薄い包みで、tests.conftest は import しない（第319弾以降の作法）。
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

BAD = {"kind": "static", "affects": "self", "zone": "hand",
       "mod": {"opt_reduce": {"amount": 2, "then": "destroy"}}}

DESTROYED_TAPPED = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy", "subject": "self"},
    "if": {"subject_tapped": True},
    "effect": [{"op": "extra_turn"}]}

BATTLE_POWER = {"kind": "static", "affects": "self",
                "mod": {"battle_power": {"amount": 5000}}}

FORM_021_CANON = [BAD, BATTLE_POWER, DESTROYED_TAPPED]

DECLARE = {"kind": "declare", "zone": "hand",
           "when": {"event": "attack",
                    "subject": {"owner": "you",
                                "filter": {"civs": ["darkness"],
                                           "race_has": "コマンド"}}},
           "effect": [{"op": "may",
                       "body": [{"op": "invade",
                                 "onto": {"ref": "event.subject"}}]}]}

EFFECT_S04 = [
    {"op": "destroy",
     "select": {"zone": "bz", "owner": "opp",
                "filter": {"types": ["creature"]}, "count": 1}},
    {"op": "move",
     "select": {"zone": "graveyard", "owner": "you",
                "filter": {"civs": ["darkness"],
                           "types": ["creature"],
                           "not_name": "超復讐 ギャロウィン"},
                "count": 1},
     "to": "hand", "reason": "return"}]

OTHER_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy",
             "subject": {"owner": "you", "other": True,
                         "filter": {"types": ["creature"]}}},
    "if": {"exists": {"ref": "self", "filter": {"tapped": True}}},
    "effect": EFFECT_S04}

SELF_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy", "subject": "self"},
    "if": {"subject_tapped": True},
    "effect": EFFECT_S04}

FORM_S04 = [DECLARE, OTHER_TRIGGER, SELF_TRIGGER]


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


def test_round365_disposition():
    rej = _reject_rows()
    assert len(rej) == 2034
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10280
    assert not (ids & set(rej))          # canonical 重なり0
    assert "dm26ex1-021" not in ids and "dm26ex1-021" not in rej
    c = _conv_cache.find(CONVERTED, "dm26rp3-tr005")
    assert c is not None and c["abilities"] == FORM_021_CANON
    c = _conv_cache.find(CONVERTED, "dmr18-s04")
    assert c is not None and c["abilities"] == FORM_S04
    assert not (c.get("source") or {}).get("unsupported")
    assert not (c.get("source") or {}).get("aliases")
    for t in ("dm26rp3-tr005", "dmr18-s04"):
        parse_card(_conv_cache.find(CONVERTED, t), TABLES)
    left = {rid for rid, r in rej.items()
            if "destroyed_while_tapped" in (r.get("gaps") or [])}
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


def _cast_destroy_own(e, target_defn, tap_defn=None):
    cast = False
    destroyed = False
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended before destroy"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and not cast \
                and "play:T1003" in keys:
            if tap_defn is not None:
                e.s.cards[_bz(e, 0, tap_defn)].tapped = True
            e.answer([keys.index("play:T1003")])
            cast = True
            continue
        if cast and d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if cast and d["kind"] == "choose_cards":
            pick = next((k for k in keys if target_defn in k), None)
            if pick is not None and not destroyed:
                e.answer([keys.index(pick)])
                destroyed = True
            else:
                e.answer([0])
            continue
        if cast and d["kind"] in ("charge", "main", "attack"):
            return
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("destroy did not resolve")


def test_registered_canon_extra_turn_when_destroyed_tapped(rules):
    """修正後の登録形 dm26rp3-tr005: タップ状態で破壊されると
    追加ターンを得る（修正前は exists 形で決して誘発しなかった）。"""
    e = _build(rules, {"bz": ["dm26rp3-tr005"], "hand": ["T1003"],
                       "mana": ["T053"]}, {})
    cast = False
    destroyed = False
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and not cast \
                and "play:T1003" in keys:
            e.s.cards[_bz(e, 0, "dm26rp3-tr005")].tapped = True
            e.answer([keys.index("play:T1003")])
            cast = True
            continue
        if cast and _in_zone(e, 0, "graveyard", "dm26rp3-tr005"):
            destroyed = True
        if destroyed and d["kind"] == "charge":
            assert (d.get("player"), bool(e.s.extra_turn)) == (0, True)
            return
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("next charge did not appear")


def test_registered_canon_battle_power(rules):
    """修正後の登録形 dm26rp3-tr005: バトル中パワー+5000 で
    T1004（13000）に勝つ（修正前は affects の形で効かなかった）。"""
    e = _build(rules, {"bz": ["dm26rp3-tr005"]}, {"bz": ["T1004"]})
    t = _bz(e, 0, "dm26rp3-tr005")
    e.s.cards[t].entered_turn = -1
    blocked = False
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended before battle"
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 \
                and "attack:dm26rp3-tr005:player" in keys:
            e.answer([keys.index("attack:dm26rp3-tr005:player")])
            continue
        if d["kind"] == "block":
            pick = next((k for k in keys if "T1004" in k), None)
            assert pick is not None, keys
            e.answer([keys.index(pick)])
            blocked = True
            continue
        if blocked and d["kind"] in ("charge", "main", "attack"):
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert blocked
    assert _in_zone(e, 1, "graveyard", "T1004")
    assert e.s.cards[t].zone == "bz"


def test_registered_self_destroyed_while_tapped(rules):
    """登録形 dmr18-s04: 自分がタップ状態で破壊されると、相手の
    クリーチャーを1体破壊し、闇のクリーチャーを墓地から戻す。"""
    e = _build(rules, {"bz": ["dmr18-s04"], "graveyard": ["T053"],
                       "hand": ["T1003"], "mana": ["T053"]},
               {"bz": ["T004"]})
    _cast_destroy_own(e, "dmr18-s04", tap_defn="dmr18-s04")
    assert _in_zone(e, 0, "graveyard", "dmr18-s04")
    assert _in_zone(e, 1, "graveyard", "T004")
    assert _in_zone(e, 0, "hand", "T053")
