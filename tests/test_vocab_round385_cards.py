"""再変換ラウンド385（第350弾 must_attack_next_turn）の記録テスト。

- 新規登録1件: dmrp22-021 ドラヴィ圧鬼の巻（登録形は
  意図した形と完全一致）。
- stale 掃除1件: dm05-014 ファントム・ベール
  （canonical の dm18-036 が同機構で登録済み・alias 記録
  済みだったため、rejects 行の除去が正しい解決）。
- converted 10,325→10,326 / rejects 1,988→1,986、
  canonical 重なり0・漏れ0。
- must_attack_next_turn は dm23ex3-tr09 にだけ残る
  （バトル代替の機構が無いため対象外。行は原文どおり
  復帰済み）。

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

MOD_014 = {"op": "modify",
           "select": {"zone": "bz", "owner": "opp",
                      "filter": {"types": ["creature"]}, "count": "all"},
           "mod": {"require": ["attack"]},
           "duration": "until_next_own_turn_start"}
CIP_021 = {"kind": "trigger",
           "when": {"event": "move", "to": "bz", "subject": "self"},
           "effect": [{"op": "modify",
                       "select": {"zone": "bz", "owner": "opp",
                                  "filter": {"types": ["creature"]},
                                  "count": "all"},
                       "mod": {"require": ["attack"]},
                       "duration": "until_next_own_turn_start"}]}
SHINKA_021 = {"kind": "trigger",
              "when": {"event": "evolve_base", "subject": "self"},
              "effect": [{"op": "modify",
                          "select": {"ref": "event.top"},
                          "mod": {"gain": [{"kind": "trigger",
                                            "first_time": True,
                                            "when": {"event": "battle_win",
                                                     "subject": "self"},
                                            "effect": [{"op": "untap",
                                                        "select": {"ref": "self",
                                                                   "count": 1}}]}]},
                          "duration": "until_next_own_turn_start"}]}
FORM_021 = [CIP_021, SHINKA_021]


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


def test_round385_disposition():
    rej = _reject_rows()
    assert len(rej) == 1986
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10326
    assert not (ids & set(rej))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dmrp22-021")
    assert c is not None and c["abilities"] == FORM_021
    assert not (c.get("source") or {}).get("unsupported")
    parse_card(c, TABLES)
    assert "dm05-014" not in rej
    canon = _conv_cache.find(CONVERTED, "dm18-036")
    assert canon is not None and canon["spell"] == [MOD_014]
    assert "dm05-014" in (canon.get("source") or {}).get("aliases", [])
    left = {rid for rid, r in rej.items()
            if "must_attack_next_turn" in (r.get("gaps") or [])}
    assert left == {"dm23ex3-tr09"}, left


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _play_then_opp_turn(e, play_key, state):
    for _ in range(900):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if (d["kind"] == "charge" and d.get("player") == 0
                and state.get("played")):
            return
        if (d["kind"] == "main" and d.get("player") == 0
                and play_key in keys and not state.get("played")):
            state["played"] = True
            e.answer([keys.index(play_key)])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "attack" and d.get("player") == 1:
            if "pass" not in keys:
                state["forced_attack"] = True
            if "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                atk = [i for i, k in enumerate(keys)
                       if k.endswith(":player")]
                e.answer([atk[0] if atk else 0])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("yes")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("drive never finished")


def test_registered_tamaseed_forces_attacks(rules):
    e = _build(rules, {"hand": ["dmrp22-021"], "mana": ["T005", "T001"]},
               {"bz": ["T005", "T004"]})
    state = {}
    _play_then_opp_turn(e, "play:dmrp22-021", state)
    assert state.get("forced_attack")
    tapped = {e.s.cards[c].defn: e.s.cards[c].tapped
              for c in e.bz_tops(1)}
    assert all(tapped.values()), tapped


def test_registered_phantom_veil_forces_attacks(rules):
    # canonical の dm18-036（ファントム・ベール）自身で固定
    e = _build(rules, {"hand": ["dm18-036"], "mana": ["T053"]},
               {"bz": ["T005", "T004"]})
    state = {}
    _play_then_opp_turn(e, "play:dm18-036", state)
    assert state.get("forced_attack")
    tapped = {e.s.cards[c].defn: e.s.cards[c].tapped
              for c in e.bz_tops(1)}
    assert all(tapped.values()), tapped
