"""再変換ラウンド386（第351弾 battle_power_against_specific_race）
の記録テスト。

- 新規登録2件: dm08-006 光器サーシャ / dm16-021 光器スヴェータ
  （登録形は意図した形と完全一致）。
- converted 10,326→10,328 / rejects 1,986→1,984、
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

DRAGON_BLOCK = {
    "kind": "static", "affects": "self",
    "mod": {"allow": [{"action": "block",
                       "other": {"race_has": "ドラゴン"}}]},
}
BATTLE_006 = {
    "kind": "static", "affects": "self",
    "mod": {"battle_power": {"amount": 6000,
                             "opponent_filter": {"race_has": "ドラゴン"}}},
}
BATTLE_021 = {
    "kind": "static", "affects": "self",
    "mod": {"battle_power": {"amount": 4000,
                             "opponent_filter": {"any_of": [
                                 {"race_has": "デーモン・コマンド"},
                                 {"race_has": "ドラゴン"}]}}},
}
FORM_006 = [DRAGON_BLOCK, BATTLE_006]
FORM_021 = [BATTLE_021]


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


def test_round386_disposition():
    rej = _reject_rows()
    assert len(rej) == 1984
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10328
    assert not (ids & set(rej))          # canonical 重なり0
    for tid, form in (("dm08-006", FORM_006), ("dm16-021", FORM_021)):
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None and c["abilities"] == form
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    left = {rid for rid, r in rej.items()
            if "battle_power_against_specific_race" in (r.get("gaps") or [])}
    assert left == set(), left


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _attack_and_maybe_block(e, attacker, blocker, state):
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "charge" and d.get("player") == 1:
            return
        if d["kind"] == "attack" and d.get("player") == 0 \
                and not state.get("attacked"):
            tgt = [k for k in keys
                   if k == f"attack:{attacker}:player"]
            if tgt:
                state["attacked"] = True
                e.answer([keys.index(tgt[0])])
                continue
            e.answer([keys.index("pass")])
        elif d["kind"] == "block":
            state["block_decision"] = keys
            pick = [i for i, k in enumerate(keys)
                    if k.startswith(f"bz:{blocker}")]
            if pick:
                state["blocked"] = True
                e.answer([pick[0]])
            else:
                e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("attack never finished")


def test_registered_sasha_dragon_blocker(rules):
    # 非ドラゴンはブロックできない
    e = _build(rules, {"bz": ["T005"]}, {"bz": ["dm08-006"]})
    state = {}
    _attack_and_maybe_block(e, "T005", "dm08-006", state)
    assert state.get("attacked") and not state.get("block_decision")
    # ドラゴンはブロックでき、バトルに勝つ
    e = _build(rules, {"bz": ["T156"]}, {"bz": ["dm08-006"]})
    state = {}
    _attack_and_maybe_block(e, "T156", "dm08-006", state)
    assert state.get("blocked")
    assert "T156" in [e.s.cards[c].defn for c in e.zlist("graveyard", 0)]


def test_registered_sveta_battle_power(rules):
    e = _build(rules, {"bz": ["T156"]}, {"bz": ["dm16-021"]})
    state = {}
    _attack_and_maybe_block(e, "T156", "dm16-021", state)
    assert state.get("blocked")
    assert "T156" in [e.s.cards[c].defn for c in e.zlist("graveyard", 0)]
    assert "dm16-021" in [e.s.cards[c].defn for c in e.bz_tops(1)]
