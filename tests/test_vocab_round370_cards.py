"""再変換ラウンド370（第335弾 per_card_tap_or_untap）の記録テスト。

- 新規登録3件: dm25bd2-015 清浄の精霊ウル / dm24rp2-051
  粛清者ゴットハルト / dm25-002 超鎧亜キングダム・ゲオルグ。
  いずれも登録形は確立形と完全一致。
- alias 畳み込み0件（submit 時に dm25bd2-015 へ aliases
  3件が自動記録されたが rejects 行ではない）・差し戻し0件
  （submit 時の警告なし）。
- converted 10,288→10,291 / rejects 2,026→2,023、
  canonical 重なり0・漏れ0。per_card_tap_or_untap の行は
  残っていない（ファミリー解消）。

実挙動は登録カード自身で固定する（ウルで相手をタップ、
ゴットハルトで2体を別々に、ゲオルグは攻撃時に進化でない
クリーチャーをタップ）。ドライバは scenario.build の薄い
包みで、tests.conftest は import しない（第319弾以降の
作法）。相手のタップ状態は相手のターン開始で消えるため、
検証は自分のターンの攻撃フェイズで止めて行う。
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

CHOOSE_1 = {"op": "choose",
            "select": {"zone": "bz", "owner": "any",
                       "filter": {"types": ["creature"]}, "count": 1},
            "as": "target"}
MODAL_TU = {"op": "modal", "modes": [
    [{"op": "tap", "select": {"ref": "target"}}],
    [{"op": "untap", "select": {"ref": "target"}}]]}
FORM_015 = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [CHOOSE_1, MODAL_TU]}]
CHOOSE_UP2 = {"op": "choose",
              "select": {"zone": "bz", "owner": "any",
                         "filter": {"types": ["creature"]},
                         "count": 1, "up_to": True},
              "as": "target"}
FORM_051 = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [{"op": "repeat", "times": 2,
                "body": [CHOOSE_UP2, MODAL_TU]}]}]
CHOOSE_E = {"op": "choose",
            "select": {"zone": "bz", "owner": "any",
                       "filter": {"types": ["creature"],
                                  "evolution": False}, "count": 1},
            "as": "target"}
FORM_002 = [{
    "kind": "trigger",
    "when": {"event": "attack", "subject": "self"},
    "effect": [{"op": "may", "body": [CHOOSE_E, MODAL_TU]}]}]


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


def test_round370_disposition():
    rej = _reject_rows()
    assert len(rej) == 2023
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10291
    assert not (ids & set(rej))          # canonical 重なり0
    for t, form in (("dm25bd2-015", FORM_015), ("dm24rp2-051", FORM_051),
                    ("dm25-002", FORM_002)):
        c = _conv_cache.find(CONVERTED, t)
        assert c is not None and c["abilities"] == form, t
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    c = _conv_cache.find(CONVERTED, "dm25bd2-015")
    assert (c.get("source") or {}).get("aliases") == [
        "dmd32-007", "dmex11-015", "dmpcd01-t10"]
    left = {rid for rid, r in rej.items()
            if "per_card_tap_or_untap" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _tapped(e, p, defn):
    cid = next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)
    return e.s.cards[cid].tapped


def _pick(keys, defn):
    return next(i for i, k in enumerate(keys)
                if k.startswith("bz:") and k.split(":")[1] == defn)


def _charge_answer(keys, keep_defn):
    if "pass" in keys:
        return [keys.index("pass")]
    for i, k in enumerate(keys):
        if keep_defn not in k:
            return [i]
    return [0]


def _opp_attacks(e, keep_defn):
    attacked = False
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if attacked and d["kind"] == "charge" and d.get("player") == 0:
            return
        if d["kind"] == "attack" and d.get("player") == 1 \
                and "attack:T005:player" in keys:
            e.answer([keys.index("attack:T005:player")])
            attacked = True
            continue
        if d["kind"] == "block":
            e.answer([keys.index("no_block")])
            continue
        if d["kind"] == "declare_strigger":
            e.answer([])
            continue
        if d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "charge":
            e.answer(_charge_answer(keys, keep_defn))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def _summon_and_choose_modal(e, play_key, plan):
    plan = list(plan)
    played = False
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if played and not plan and d["kind"] == "attack" \
                and d.get("player") == 0:
            return
        if d["kind"] == "main" and d.get("player") == 0 and not played \
                and play_key in keys:
            e.answer([keys.index(play_key)])
            played = True
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "charge" and not played:
            e.answer(_charge_answer(keys, play_key.split(":")[1]))
            continue
        if d["kind"] == "choose_cards":
            e.answer([_pick(keys, plan[0][0])])
            continue
        if d["kind"] == "choose_mode":
            _, mode = plan.pop(0)
            e.answer([keys.index(f"mode:{mode}")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("summon/choose/modal did not resolve")


def test_registered_uru_taps_opponent(rules):
    e = _build(rules, {"hand": ["dm25bd2-015"], "mana": ["T004"] * 6,
                       "bz": ["T1004"]},
               {"bz": ["T005"]})
    _summon_and_choose_modal(e, "play:dm25bd2-015", [("T005", 0)])
    assert _tapped(e, 1, "T005")


def test_registered_gotthart_repeat(rules):
    e = _build(rules, {"hand": ["dm24rp2-051"], "mana": ["T004"] * 4,
                       "bz": ["T1004"]},
               {"bz": ["T005", "T001"]})
    _opp_attacks(e, "dm24rp2-051")
    assert _tapped(e, 1, "T005")
    _summon_and_choose_modal(e, "play:dm24rp2-051",
                             [("T005", 1), ("T001", 0)])
    assert not _tapped(e, 1, "T005")
    assert _tapped(e, 1, "T001")


def test_registered_georg_attack_taps(rules):
    e = _build(rules, {"bz": ["dm25-002"]},
               {"bz": ["T005", "T001", "T1017"]})
    state = {"attacked": False, "seen": None, "tapped_at_break": None}
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "choose_shields":
            state["tapped_at_break"] = _tapped(e, 1, "T005")
            e.answer(list(range(d["min"])))
            break
        if d["kind"] == "attack" and d.get("player") == 0 \
                and not state["attacked"] \
                and "attack:dm25-002:player" in keys:
            e.answer([keys.index("attack:dm25-002:player")])
            state["attacked"] = True
            continue
        if d["kind"] == "yes_no":
            e.answer([keys.index("yes")])
            continue
        if d["kind"] == "choose_cards":
            state["seen"] = keys
            e.answer([_pick(keys, "T005")])
            continue
        if d["kind"] == "choose_mode":
            e.answer([keys.index("mode:0")])
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
        raise AssertionError("attack did not resolve")
    assert state["seen"] is not None
    # 進化クリーチャー（T1017）は対象に選べない
    assert not any(k.split(":")[1] == "T1017" for k in state["seen"]
                   if k.startswith("bz:")), state["seen"]
    assert state["tapped_at_break"] is True
