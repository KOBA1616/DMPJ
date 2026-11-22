"""再変換ラウンド371（第336弾 break_limit）の記録テスト。

- 新規登録3件: dm29-001 光神龍ラル・アブゾーバー /
  dm16-008 インパクト・アブソーバー / dm26rp1-039
  我竜塔最高層 ローズ・キャッスル。いずれも登録形は
  確立形と完全一致。
- alias 畳み込み0件・差し戻し0件（submit 時の警告なし）。
- converted 10,291→10,294 / rejects 2,023→2,020、
  canonical 重なり0・漏れ0。break_limit の行は残っていない
  （ファミリー解消）。

実挙動は登録カード自身で固定する（ラルがあると攻撃時の
choose_shields が (1, 1) になり1枚だけ割れる。ギアは
未クロスで両者を上限1にし、クロスすると戻る。城は表向きの
時だけ上限1）。ドライバは scenario.build の薄い包みで、
tests.conftest は import しない（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402

from tests import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

FORM_001 = [{
    "kind": "static",
    "affects": {"owner": "opp", "filter": {"types": ["creature"]}},
    "mod": {"breaks_max": 1}}]
FORM_008 = [
    {"kind": "replace",
     "when": {"event": "move", "from": "bz", "to": "graveyard",
              "reason": "destroy", "subject": "crossed"},
     "instead": [{"op": "move", "select": {"ref": "crossed"},
                  "to": "shield", "reason": "put"}]},
    {"kind": "static",
     "affects": {"owner": "any", "filter": {"types": ["creature"]}},
     "if": {"not": {"exists": {"ref": "self",
                               "filter": {"crossed": True}}}},
     "mod": {"breaks_max": 1}}]
FORM_039 = [
    {"kind": "trigger", "zone": "shield", "if": {"face_up": True},
     "when": {"event": "battle_start",
              "subject": {"owner": "you",
                          "filter": {"types": ["creature"]}}},
     "effect": [{"op": "modify", "select": {"ref": "event.opponent"},
                 "mod": {"power": -4000}, "duration": "during_attack"}]},
    {"kind": "trigger", "zone": "shield", "if": {"face_up": True},
     "when": {"event": "battle_start",
              "opponent": {"owner": "you",
                           "filter": {"types": ["creature"]}}},
     "effect": [{"op": "modify", "select": {"ref": "event.subject"},
                 "mod": {"power": -4000}, "duration": "during_attack"}]},
    {"kind": "static", "zone": "shield", "if": {"face_up": True},
     "affects": {"owner": "opp", "filter": {"types": ["creature"]}},
     "mod": {"breaks_max": 1}}]


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


def test_round371_disposition():
    rej = _reject_rows()
    assert len(rej) == 2020
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10294
    assert not (ids & set(rej))          # canonical 重なり0
    for t, form in (("dm29-001", FORM_001), ("dm16-008", FORM_008),
                    ("dm26rp1-039", FORM_039)):
        c = _conv_cache.find(CONVERTED, t)
        assert c is not None and c["abilities"] == form, t
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    left = {rid for rid, r in rej.items()
            if "break_limit" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _breaks(e, p, defn):
    return e.chars(_cid(e, p, defn))["breaks"]


def test_registered_gear_and_castle_caps(rules):
    e = _build(rules, {"bz": ["dm16-008", "T1014"]}, {"bz": ["T1014"]})
    assert _breaks(e, 0, "T1014") == 1
    assert _breaks(e, 1, "T1014") == 1
    gear = _cid(e, 0, "dm16-008")
    e.s.cards[gear].crossed = e.s.ref(_cid(e, 0, "T1014"))
    assert _breaks(e, 0, "T1014") == 3
    e2 = _build(rules, {"bz": ["T1014"]},
                {"shield": ["dm26rp1-039"]})
    cid = next(c for c in e2.zlist("shield", 1)
               if e2.s.cards[c].defn == "dm26rp1-039")
    assert _breaks(e2, 0, "T1014") == 3
    e2.s.cards[cid].face_up = True
    assert _breaks(e2, 0, "T1014") == 1


def test_registered_ral_limits_attack_break(rules):
    e = _build(rules, {"bz": ["T1014"]}, {"bz": ["dm29-001"]})
    assert len(e.zlist("shield", 1)) == 5
    seen = {}
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_shields":
            seen["minmax"] = (d["min"], d["max"])
            e.answer(list(range(d["min"])))
            break
        if d["kind"] == "attack" and d.get("player") == 0 \
                and "attack:T1014:player" in keys:
            e.answer([keys.index("attack:T1014:player")])
            continue
        if d["kind"] == "block":
            e.answer([keys.index("no_block")])
            continue
        if d["kind"] == "declare_strigger":
            e.answer([])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    else:
        raise AssertionError("attack did not reach choose_shields")
    assert seen["minmax"] == (1, 1)
    # 解決を進めて割れた枚数を見る
    for _ in range(60):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main", "attack"):
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert len(e.zlist("shield", 1)) == 4
