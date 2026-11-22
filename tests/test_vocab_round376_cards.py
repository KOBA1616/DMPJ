"""再変換ラウンド376（第341弾 each_player_keeps_one_creature）の記録テスト。

- 新規登録2件: dm24bd6-003 偽りのコード シャーロック /
  dm23bd5-001 煉獄大帝 キング・ロマノフ。いずれも登録形は
  意図した形と一致（submit 直後の abilities 重複チェック済み、
  重複なし）。
- alias 畳み込み0件・差し戻し0件。
- converted 10,305→10,307 / rejects 2,009→2,007、
  canonical 重なり0・漏れ0。each_player_keeps_one_creature
  の行は残っていない（ファミリー解消）。

実挙動は登録カード自身で固定する（003 は選ばれなかった側を
破壊、001 は持ち主のマナへ）。ドライバは scenario.build の
薄い包みで、tests.conftest は import しない（第319弾以降の作法）。
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

CRYSTAL_STATIC = {
    "kind": "static",
    "affects": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}},
    "if": {"cmp": [{"count": {"zone": "mana", "owner": "you",
                              "filter": {"face_down": True}}},
                    ">=", 4]},
    "mod": {"grant": ["blocker", "speed_attacker", "slayer"]},
}

def _choose_keep(as_name, owner, chooser=None):
    sel = {"zone": "bz", "owner": owner,
           "filter": {"types": ["creature"]}, "count": 1}
    if chooser:
        sel["chooser"] = chooser
    return {"op": "choose", "select": sel, "as": as_name}


def _rest_select():
    return {"zone": "bz", "owner": "any",
            "filter": {"types": ["creature"]}, "count": "all",
            "exclude": [{"ref": "keep_you"}, {"ref": "keep_opp"}]}


CIP_DESTROY = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [
        _choose_keep("keep_you", "you"),
        _choose_keep("keep_opp", "opp", chooser="opp"),
        {"op": "destroy", "select": _rest_select()},
    ],
}]

CIP_MANA = [{
    "kind": "trigger",
    "when": {"event": "move", "to": "bz", "subject": "self"},
    "effect": [
        _choose_keep("keep_you", "you"),
        _choose_keep("keep_opp", "opp", chooser="opp"),
        {"op": "move", "select": _rest_select(),
         "to": "mana", "reason": "put"},
    ],
}]

FORM_003 = [CRYSTAL_STATIC] + CIP_DESTROY


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


def test_round376_disposition():
    rej = _reject_rows()
    assert len(rej) == 2007
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10307
    assert not (ids & set(rej))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dm24bd6-003")
    assert c is not None and c["abilities"] == FORM_003
    assert not (c.get("source") or {}).get("unsupported")
    parse_card(c, TABLES)
    c = _conv_cache.find(CONVERTED, "dm23bd5-001")
    assert c is not None and c["abilities"][-1:] == CIP_MANA
    assert len(c["abilities"]) == 3
    assert not (c.get("source") or {}).get("unsupported")
    parse_card(c, TABLES)
    left = {rid for rid, r in rej.items()
            if "each_player_keeps_one_creature" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _pick(keys, defn):
    return next(i for i, k in enumerate(keys)
                if f":{defn}:" in k or k.endswith(f":{defn}"))


def _drive(e, plan, limit=900):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        if plan(d, _keys(d)):
            return d
    raise AssertionError("plan never stopped")


def _summon_plan(e, state, summon_key, keeps):
    def plan(d, keys):
        if state.get("summoned") and state.get("p1_charged") \
                and d["kind"] == "attack" and d.get("player") == 0:
            return True
        if state.get("summoned") and d["kind"] == "charge" \
                and d.get("player") == 1:
            state["p1_charged"] = True
        if d["kind"] == "main" and d.get("player") == 0 \
                and not state.get("summoned") \
                and summon_key in keys:
            e.answer([keys.index(summon_key)])
            state["summoned"] = True
            return False
        if d["kind"] == "choose_cards" and keeps:
            defn, player = keeps[0]
            if d.get("player") == player:
                keeps.pop(0)
                state.setdefault("choose_players", []).append(player)
                e.answer([_pick(keys, defn)])
                return False
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            return False
        if d["kind"] == "block" and "no_block" in keys:
            # ロマノフの require: attack で相手は攻撃を強いられる。
            # ブロックせず通す（T005 を残すため）
            e.answer([keys.index("no_block")])
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        return False
    return plan


def test_registered_sherlock_destroys_rest(rules):
    e = _build(rules,
               {"hand": ["dm24bd6-003"], "bz": ["T001"],
                "mana": ["T004", "T005", "T053"] + ["T001"] * 6},
               {"bz": ["T005", "T009"]})
    state = {}
    keeps = [("dm24bd6-003", 0), ("T005", 1)]
    _drive(e, _summon_plan(e, state, "play:dm24bd6-003", keeps))
    assert state["choose_players"] == [0, 1]
    assert [e.s.cards[c].defn for c in e.bz_tops(0)] == ["dm24bd6-003"]
    assert [e.s.cards[c].defn for c in e.bz_tops(1)] == ["T005"]
    assert [e.s.cards[c].defn for c in e.zlist("graveyard", 0)] == ["T001"]
    assert [e.s.cards[c].defn for c in e.zlist("graveyard", 1)] == ["T009"]


def test_registered_romanov_rest_to_mana(rules):
    e = _build(rules,
               {"hand": ["dm23bd5-001"], "bz": ["T001", "T009"],
                "mana": ["T004", "T053"] + ["T001"] * 8},
               {"bz": ["T005", "T004"]})
    state = {}
    keeps = [("dm23bd5-001", 0), ("T005", 1)]
    _drive(e, _summon_plan(e, state, "play:dm23bd5-001", keeps))
    assert state["choose_players"] == [0, 1]
    assert [e.s.cards[c].defn for c in e.bz_tops(0)] == ["dm23bd5-001"]
    assert [e.s.cards[c].defn for c in e.bz_tops(1)] == ["T005"]
    mana0 = {e.s.cards[c].defn for c in e.zlist("mana", 0)}
    assert {"T001", "T009"} <= mana0
    mana1 = {e.s.cards[c].defn for c in e.zlist("mana", 1)}
    assert "T004" in mana1
