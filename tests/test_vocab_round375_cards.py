"""再変換ラウンド375（第340弾 enters_tapped_opponent）の記録テスト。

- 新規登録2件: dmc52-007 聖霊王エルフェウス /
  dm24bd6-006 偽りの希望 修羅丸「終斗」。いずれも登録形は
  確立形と完全一致（submit 直後の abilities 重複チェック済み、
  重複なし）。
- alias 畳み込み0件（submit 時に 007 へ aliases [dm14-001]
  が自動記録されたが rejects 行ではない）・差し戻し0件。
- converted 10,303→10,305 / rejects 2,011→2,009、
  canonical 重なり0・漏れ0。enters_tapped_opponent
  の行は残っていない（ファミリー解消）。

実挙動は登録カード自身で固定する（エルフェウスがいる間、
相手クリーチャーはタップして出る。修羅丸は各ターン1体目
だけ）。ドライバは scenario.build の薄い包みで、
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

FORM_007 = [
    {"kind": "static",
     "affects": {"zone": "bz", "owner": "opp",
                 "filter": {"types": ["creature"]}},
     "mod": {"grant": ["enters_tapped"]}},
]
FORM_006 = [
    {"kind": "trigger", "first_time": True,
     "when": {"event": "move", "to": "bz",
              "subject": {"owner": "opp",
                          "filter": {"types": ["creature"]}}},
     "effect": [{"op": "tap", "select": {"ref": "event.subject"}}]},
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


def test_round375_disposition():
    rej = _reject_rows()
    assert len(rej) == 2009
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10305
    assert not (ids & set(rej))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dmc52-007")
    assert c is not None and c["abilities"] == FORM_007
    assert not (c.get("source") or {}).get("unsupported")
    parse_card(c, TABLES)
    c = _conv_cache.find(CONVERTED, "dm24bd6-006")
    assert c is not None and c["abilities"] == FORM_006
    assert not (c.get("source") or {}).get("unsupported")
    parse_card(c, TABLES)
    left = {rid for rid, r in rej.items()
            if "enters_tapped_opponent" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz_card(e, p, defn):
    return next(c for c in e.bz_tops(p)
                if e.s.cards[c].defn == defn)


def _drive(e, plan, limit=900):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        if plan(d, _keys(d)):
            return d
    raise AssertionError("plan never stopped")


def test_registered_elpheus_taps_entries(rules):
    e = _build(rules, {"bz": ["dmc52-007"]},
               {"hand": ["T005"], "mana": ["T005", "T001", "T001"]})
    state = {"played": False}

    def plan(d, keys):
        if state["played"] and d["kind"] == "charge" \
                and d.get("player") == 0:
            return True
        if d["kind"] == "main" and d.get("player") == 1 \
                and not state["played"] and "play:T005" in keys:
            e.answer([keys.index("play:T005")])
            state["played"] = True
            return False
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        return False

    _drive(e, plan)
    assert e.s.cards[_bz_card(e, 1, "T005")].tapped is True


def test_registered_shuramaru_first_only(rules):
    e = _build(rules, {"bz": ["dm24bd6-006"]},
               {"hand": ["T005", "T009", "T004", "T003"],
                "mana": ["T005", "T009", "T004", "T001", "T001"]})
    state = {"p1turns": 0, "phase": 1, "played": set()}

    def plan(d, keys):
        if d["kind"] == "charge" and d.get("player") == 1:
            state["p1turns"] += 1
            if state["p1turns"] == 2 and "charge:T003" in keys:
                e.answer([keys.index("charge:T003")])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
            return False
        if d["kind"] == "charge" and d.get("player") == 0:
            if state["phase"] == 1 and state["p1turns"] == 1 \
                    and {"T005", "T009"} <= state["played"]:
                return True
            if state["phase"] == 2 and state["p1turns"] == 2 \
                    and "T004" in state["played"]:
                return True
            if "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d["min"])))
            return False
        if d["kind"] == "main" and d.get("player") == 1:
            for tgt in ("T005", "T009", "T004"):
                key = f"play:{tgt}"
                if key in keys and tgt not in state["played"]:
                    e.answer([keys.index(key)])
                    state["played"].add(tgt)
                    return False
        if d["kind"] == "pay_mana":
            keep = [i for i, k in enumerate(keys) if "T009" not in k]
            e.answer(keep[:d["min"]] if keep
                     else list(range(d["min"])))
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        return False

    _drive(e, plan)
    assert e.s.cards[_bz_card(e, 1, "T005")].tapped is True
    assert e.s.cards[_bz_card(e, 1, "T009")].tapped is False
    state["phase"] = 2
    _drive(e, plan)
    assert e.s.cards[_bz_card(e, 1, "T004")].tapped is True
