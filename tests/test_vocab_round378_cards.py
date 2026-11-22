"""再変換ラウンド378（第343弾 first_entry_tapped_per_turn）の記録テスト。

- 新規登録1件: dm26ex4-cho001 アルカディアス・モモキング
  （登録形は意図した形と完全一致。submit 直後の照合済み）。
- stale クリーンアップ1件: dm26sd1-o002f は非正本で、正本
  cho001 の aliases として解消（submit は「取得済みの原文に
  無いID」で弾いた。第365弾と同型）。alias 畳み込みとしては
  数えない（rejects 行の解消は reopen 側）。
- converted 10,309→10,310 / rejects 2,005→2,003、
  canonical 重なり0・漏れ0。first_entry_tapped_per_turn
  の行は残っていない（ファミリー解消）。

実挙動は登録カード自身で固定する（各ターン1体目だけ
タップして出る）。ドライバは scenario.build の薄い包みで、
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

STATIC_POWER = {
    "kind": "static",
    "affects": {"zone": "bz", "owner": "you", "other": True,
                "filter": {"race_has": "レクスターズ"}},
    "mod": {"power": 2000},
}
STATIC_DENY = {
    "kind": "static",
    "affects": {"zone": "hand", "owner": "opp",
                "filter": {"types": ["spell"], "not_civs": ["light"]}},
    "mod": {"deny": ["cast"]},
}
FIRST_ENTRY = {
    "kind": "trigger", "first_time": True,
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "opp",
                         "filter": {"types": ["creature"]}}},
    "effect": [{"op": "tap", "select": {"ref": "event.subject"}}],
}
FORM = [STATIC_POWER, STATIC_DENY, FIRST_ENTRY]


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


def test_round378_disposition():
    rej = _reject_rows()
    assert len(rej) == 2003
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10310
    assert not (ids & set(rej))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dm26ex4-cho001")
    assert c is not None and c["abilities"] == FORM
    assert not (c.get("source") or {}).get("unsupported")
    assert "dm26sd1-o002f" in (c.get("source") or {}).get("aliases", [])
    parse_card(c, TABLES)
    assert "dm26sd1-o002f" not in ids and "dm26sd1-o002f" not in rej
    left = {rid for rid, r in rej.items()
            if "first_entry_tapped_per_turn" in (r.get("gaps") or [])}
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


def test_registered_momoking_first_only(rules):
    e = _build(rules, {"bz": ["dm26ex4-cho001"]},
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
