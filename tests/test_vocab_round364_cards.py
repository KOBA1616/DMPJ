"""再変換ラウンド364（第329弾 shield_placement_trigger）の記録テスト。

- 新規登録2件: dm26ex4-cho047 DARK MEMORY CONTAINER /
  dm26rp1-tr002 楯教の求道者 ザゼ・ゼーン。
- alias 畳み込み0件（submit 時に cho047 へ aliases 3件
  [dm25ex3-055, dm25rp2-048, promoy25-051]、tr002 へ aliases 4件
  [dm24ex3-rp3s02, dm24ex3-rp3sec03, dm24rp3-s02, dm24rp3-sec003]
  が自動記録されたが、いずれも rejects 行ではない）。
- stale クリーンアップ0件・差し戻し0件。
- converted 10,277→10,279 / rejects 2,038→2,036、
  canonical 重なり0・漏れ0。shield_placement_trigger は残り0件で
  ファミリー解消。
- 提出時のバリデータ警告で cho047 の墓地からの自己登場を
  play_free から move {ref: self} to: bz reason: put へ修正
  （「出す」は召喚ではない）。proto・回答・converted の3か所を
  同形に揃えた。

実挙動は登録カード自身で固定する（シールド配置の駆動には proto
T1000 のシールド追加呪文を使う）。ドライバは scenario.build の
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

TARGETS = {"dm26ex4-cho047", "dm26rp1-tr002"}

CIP = {"kind": "trigger", "when": {"event": "move", "to": "bz",
                                   "subject": "self"},
       "effect": [{"op": "draw", "count": 2}]}

GY_TRIGGER = {"kind": "trigger", "zone": "graveyard",
              "when": {"event": "move", "to": "shield",
                       "subject": {"owner": "you"}},
              "effect": [{"op": "may",
                          "body": [{"op": "move",
                                    "select": {"ref": "self"},
                                    "to": "bz", "reason": "put"}]}]}

FORM_047 = [CIP, GY_TRIGGER]

NO_UNTAP = {"kind": "static", "affects": "self",
            "mod": {"deny": ["untap_at_start"]}}

MODAL = {"op": "modal", "count": 1, "modes": [
    [{"op": "draw", "count": 1}],
    [{"op": "choose",
      "select": {"zone": "bz", "owner": "opp",
                 "filter": {"types": ["creature"]}},
      "as": "chosen"},
     {"op": "tap", "select": {"ref": "chosen"},
      "no_untap_next": True}],
    [{"op": "modify", "select": {"ref": "self"},
      "mod": {"no_leave": True},
      "duration": "until_next_own_turn_start"}],
]}

SHIELD_TRIGGER = {"kind": "trigger",
                  "when": {"event": "move", "to": "shield",
                           "subject": {"owner": "you"}},
                  "effect": [{"op": "untap", "select": {"ref": "self"}},
                             MODAL]}

FORM_TR002 = [NO_UNTAP, SHIELD_TRIGGER]


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


def test_round364_disposition():
    rej = _reject_rows()
    assert len(rej) == 2036
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10279
    assert not (ids & set(rej))          # canonical 重なり0
    assert TARGETS <= ids and not (TARGETS & set(rej))
    c = _conv_cache.find(CONVERTED, "dm26ex4-cho047")
    assert c is not None and c["abilities"] == FORM_047
    assert (c.get("source") or {}).get("aliases") == [
        "dm25ex3-055", "dm25rp2-048", "promoy25-051"]
    c = _conv_cache.find(CONVERTED, "dm26rp1-tr002")
    assert c is not None and c["abilities"] == FORM_TR002
    assert (c.get("source") or {}).get("aliases") == [
        "dm24ex3-rp3s02", "dm24ex3-rp3sec03", "dm24rp3-s02",
        "dm24rp3-sec003"]
    for t in TARGETS:
        cc = _conv_cache.find(CONVERTED, t)
        assert not (cc.get("source") or {}).get("unsupported")
        parse_card(cc, TABLES)
    left = {rid for rid, r in rej.items()
            if "shield_placement_trigger" in (r.get("gaps") or [])}
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


def _cast_shield_add(e, may_answer=None, mode_idx=None):
    """proto T1000 を唱えてシールド配置を起こし、誘発まで処理する。"""
    cast = False
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended before shield add"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and not cast \
                and "play:T1000" in keys:
            e.answer([keys.index("play:T1000")])
            cast = True
            continue
        if cast and d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if cast and d["kind"] == "yes_no" and may_answer is not None:
            e.answer([keys.index(may_answer)])
            continue
        if cast and d["kind"] == "choose_mode" and mode_idx is not None:
            e.answer([keys.index(f"mode:{mode_idx}")])
            continue
        if cast and d["kind"] == "choose_cards":
            e.answer([0])
            continue
        if cast and d["kind"] in ("charge", "main", "attack"):
            return
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("shield add did not resolve")


def test_registered_graveyard_trigger_brings_out(rules):
    """登録形 cho047: 墓地から、シールド配置を機に may で出る。
    出たら CIP で2枚引く。"""
    e = _build(rules, {"graveyard": ["dm26ex4-cho047"],
                       "hand": ["T1000"], "mana": ["T001"]}, {})
    _cast_shield_add(e, may_answer="yes")
    c = _bz(e, 0, "dm26ex4-cho047")
    assert e.s.cards[c].zone == "bz"
    assert len(e.zlist("hand", 0)) == 2


def test_registered_shield_trigger_untap_and_modal(rules):
    """登録形 tr002: シールド配置でアンタップし、モード0で1枚引く。"""
    e = _build(rules, {"bz": ["dm26rp1-tr002"],
                       "hand": ["T1000", "T002"], "mana": ["T001"]},
               {"bz": ["T004"]})
    c = _bz(e, 0, "dm26rp1-tr002")
    e.s.cards[c].tapped = True
    _cast_shield_add(e, mode_idx=0)
    assert e.s.cards[c].tapped is False
    assert len(e.zlist("hand", 0)) == 2
