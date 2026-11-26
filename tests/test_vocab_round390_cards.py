"""再変換ラウンド390（第355弾 trigger_when_ally_is_blocked）の記録テスト。

- 新規登録1件: dm21-048 肝っ玉メリー（登録形は第355弾の
  確立形と完全一致、abilities 1件、keywords なし）。
- alias 畳み込み0件（identity の canon_id 実測で自 ID、
  aliases_for は空）。stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [trigger_when_ally_is_blocked] のため
  reopen で外してから submit（reopen の出力は対象1件ちょうど）。
- converted 10,334→10,335 / rejects 1,978→1,977、
  canonical 重なり0・漏れ0。trigger_when_ally_is_blocked は
  ファミリーがこの1件だけだったため完全に解消。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない
（第319弾以降の作法）。相手役・攻撃役は proto T1067〜T1069。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests import _conv_cache  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

_VB = {"owner": "you", "filter": {"race_has": "ビークル・ビー"}}
TRIGGER = {"kind": "trigger",
           "when": {"event": "block", "attacker": _VB},
           "effect": [{"op": "delayed_trigger",
                       "when": {"event": "attack_end", "subject": _VB},
                       "duration": "during_attack",
                       "effect": [{"op": "destroy",
                                   "select": {"ref": "event.target"}}]}]}
FORM = [TRIGGER]


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


def test_round390_disposition():
    rej = _reject_rows()
    assert len(rej) == 1977
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10335
    assert not (ids & set(rej))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, "dm21-048")
    assert c is not None and c["abilities"] == FORM
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 1
    assert d.keywords == []
    left = {rid for rid, r in rej.items()
            if "trigger_when_ally_is_blocked" in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消


# ---------- 実挙動ドライバ（scenario.build 直包み、第355弾本体と同型） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive_attack(e, attacker, block):
    state = {"attacked": False, "attack_turn": None}
    for _ in range(1500):
        if state["attacked"] and e.s.turn >= state["attack_turn"] + 2:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack":
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and not state["attacked"]:
                state["attacked"] = True
                state["attack_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            hit = [i for i, k in enumerate(keys)
                   if block and k.startswith("bz:T1068:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return state


def test_registered_blocker_destroyed_after_battle(rules):
    """登録した肝っ玉メリーが場にいる時、自分のビークル・ビーが
    ブロックされバトルに負けた後、ブロックしたクリーチャーが
    破壊される。"""
    e = _build(rules, {"bz": ["dm21-048", "T1067"]}, {"bz": ["T1068"]})
    st = _drive_attack(e, "T1067", block=True)
    assert st["attacked"]
    assert "T1067" in _defns(e, "graveyard", 0)      # バトル敗北
    assert "T1068" in _defns(e, "graveyard", 1)      # バトルの後に破壊
    assert "T1068" not in _defns(e, "bz", 1)
    assert "dm21-048" in _defns(e, "bz", 0)          # 観測者は残る


def test_registered_no_trigger_for_non_vehicle_bee(rules):
    """ビークル・ビーでないクリーチャーがブロックされても
    ブロッカーは破壊されない。"""
    e = _build(rules, {"bz": ["dm21-048", "T1069"]}, {"bz": ["T1068"]})
    st = _drive_attack(e, "T1069", block=True)
    assert st["attacked"]
    assert "T1069" in _defns(e, "graveyard", 0)
    assert "T1068" in _defns(e, "bz", 1)
    assert "T1068" not in _defns(e, "graveyard", 1)


def test_registered_no_block_no_destroy(rules):
    """ブロックされなければ何も破壊されない。"""
    e = _build(rules, {"bz": ["dm21-048", "T1067"]}, {"bz": ["T1068"]})
    st = _drive_attack(e, "T1067", block=False)
    assert st["attacked"]
    assert "T1067" in _defns(e, "bz", 0)
    assert "T1068" in _defns(e, "bz", 1)
    assert "T1068" not in _defns(e, "graveyard", 1)
