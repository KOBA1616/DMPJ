"""再変換ラウンド391（第356弾 destroy_after_attack）の記録テスト。

- 新規登録1件: dm24rp2-064 プランタ＝ランター（登録形は
  第356弾の確立形と完全一致、abilities 2件、keywords [blocker]）。
- alias 畳み込み0件（identity の canon_id 実測で自 ID、
  aliases_for は空）。stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [destroy_after_attack] のため reopen で
  外してから submit（reopen の出力は対象1件ちょうど）。
- converted 10,335→10,336 / rejects 1,977→1,976、
  canonical 重なり0・漏れ0。destroy_after_attack は
  ファミリーがこの1件だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_attacking_player）は
  判断待ちのため本ラウンドでは触っていない。

実挙動は登録カード自身で固定する。ドライバは scenario.build
の薄い包みで、tests.conftest は import しない
（第319弾以降の作法）。条件役・相手役は proto T1071/T1072。
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
TARGET = "dm24rp2-064"

TRIGGER_A = {"kind": "trigger",
             "when": {"event": "attack", "subject": "self"},
             "effect": [{"op": "delayed_trigger",
                         "when": {"event": "attack_end",
                                  "subject": "self"},
                         "duration": "during_attack",
                         "effect": [{"op": "destroy",
                                     "select": {"ref": "self"}}]}]}
STATIC_SLAYER = {"kind": "static", "affects": "self",
                 "if": {"exists": {"zone": "bz", "owner": "you",
                                   "filter": {"race_has": "超化獣"}}},
                 "mod": {"grant": ["slayer"]}}
FORM = [TRIGGER_A, STATIC_SLAYER]


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


def test_round391_disposition():
    rej = _reject_rows()
    assert len(rej) == 1976
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10336
    assert not (ids & set(rej))          # canonical 重なり0
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None and c["abilities"] == FORM
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d.keywords == ["blocker"]
    left = {rid for rid, r in rej.items()
            if "destroy_after_attack" in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（scenario.build 直包み、第356弾本体と同型） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive(e, attacker, blocker=None, limit=1500):
    state = {"attacked": False, "attack_turn": None}
    for _ in range(limit):
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
                   if blocker and k.startswith(f"bz:{blocker}:")]
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


def test_registered_attack_destroys_self_at_attack_end(rules):
    """登録したプランタ＝ランターが攻撃すると、攻撃の後
    （攻撃終了時）に破壊される。"""
    e = _build(rules, {"bz": [TARGET]}, {})
    st = _drive(e, TARGET)
    assert st["attacked"]
    assert TARGET in _defns(e, "graveyard", 0)
    assert TARGET not in _defns(e, "bz", 0)


def test_registered_no_attack_no_destroy(rules):
    """攻撃しなければ破壊されない。"""
    e = _build(rules, {"bz": [TARGET]}, {})
    for _ in range(400):
        if e.s.turn >= 2:
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert TARGET in _defns(e, "bz", 0)
    assert TARGET not in _defns(e, "graveyard", 0)


def test_registered_slayer_destroys_attacker_after_lost_battle(rules):
    """超化獣（T1071）がいれば登録カードはスレイヤーを得る:
    パワー3000の攻撃をブロックしてバトルに負けても、
    バトルの後に攻撃クリーチャーが破壊される。"""
    e = _build(rules, {"bz": [TARGET, "T1071"]}, {"bz": ["T1072"]})
    st = _drive(e, "T1072", blocker=TARGET)
    assert st["attacked"]
    assert TARGET in _defns(e, "graveyard", 0)       # バトル敗北
    assert "T1072" in _defns(e, "graveyard", 1)      # スレイヤーで破壊
    assert "T1072" not in _defns(e, "bz", 1)
    assert "T1071" in _defns(e, "bz", 0)             # 条件側は残る


def test_registered_no_slayer_without_choukajuu(rules):
    """超化獣がいなければスレイヤーは付かず、バトルに勝った
    攻撃クリーチャーは場に残る。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1072"]})
    st = _drive(e, "T1072", blocker=TARGET)
    assert st["attacked"]
    assert TARGET in _defns(e, "graveyard", 0)       # バトル敗北
    assert "T1072" in _defns(e, "bz", 1)             # 破壊されない
    assert "T1072" not in _defns(e, "graveyard", 1)
