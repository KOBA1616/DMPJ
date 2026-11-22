"""再変換ラウンド389（第354弾 forced_attack_target）の記録テスト。

- 新規登録2件: dm16-s03 超神龍アバス・ノナリス /
  dm10-s07 不落の超人（登録形は意図した形と完全一致）。
- converted 10,332→10,334 / rejects 1,980→1,978、
  canonical 重なり0・漏れ0。ファミリー解消。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない（第319弾以降の作法）。
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

STATIC_S03 = {"kind": "static", "affects": "self",
              "mod": {"must_be_attacked": True}}
STATIC_S07 = {
    "kind": "static", "affects": "self",
    "if": {"all": [
        {"is_turn": "opp"},
        {"exists": {"ref": "self", "filter": {"tapped": True}}},
        {"cmp": [{"turn_count": {"kind": "attack_on", "ref": "self"}},
                 "==", 0]}]},
    "mod": {"must_be_attacked": True},
}
FORM_S03 = [STATIC_S03]
FORM_S07 = [STATIC_S07]


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


def test_round389_disposition():
    rej = _reject_rows()
    assert len(rej) == 1978
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10334
    assert not (ids & set(rej))          # canonical 重なり0
    for tid, form in (("dm16-s03", FORM_S03), ("dm10-s07", FORM_S07)):
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None and c["abilities"] == form
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    left = {rid for rid, r in rej.items()
            if "forced_attack_target" in (r.get("gaps") or [])}
    assert left == set(), left


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _p0_first_attack_options(e, attacker):
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0:
            return [k for k in keys if k.startswith(f"attack:{attacker}:")]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("attack decision never came")


def test_registered_furaku_taunt(rules):
    e = _build(rules, {"bz": ["T005"]}, {"bz": ["dm10-s07"]})
    cid = e.bz_tops(1)[0]
    e.s.cards[cid].tapped = True
    opts = _p0_first_attack_options(e, "T005")
    assert "attack:T005:player" not in opts, opts
    assert "attack:T005:dm10-s07" in opts, opts
    e = _build(rules, {"bz": ["T005"]}, {"bz": ["dm10-s07"]})
    opts = _p0_first_attack_options(e, "T005")
    assert "attack:T005:player" in opts, opts


def test_registered_abas_taunt(rules):
    e = _build(rules, {"bz": ["T005"]},
               {"hand": ["dm16-s03"], "bz": ["T1065"],
                "mana": ["T053", "T053", "T053", "T053",
                         "T053", "T053", "T053"]})
    state = {}
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if (d["kind"] == "attack" and d.get("player") == 0
                and state.get("p1_attacked")):
            opts = [k for k in keys if k.startswith("attack:T005:")]
            assert "attack:T005:player" not in opts, opts
            assert "attack:T005:dm16-s03" in opts, opts
            return
        if (d["kind"] == "main" and d.get("player") == 1
                and "play:dm16-s03" in keys):
            state["played"] = True
            e.answer([keys.index("play:dm16-s03")])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif (d["kind"] == "attack" and d.get("player") == 1
                and "attack:dm16-s03:player" in keys):
            state["p1_attacked"] = True
            e.answer([keys.index("attack:dm16-s03:player")])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("taunt check never reached")
