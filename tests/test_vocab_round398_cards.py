"""再変換ラウンド398（第363弾 attack_on_entry_turn_punished）の記録テスト。

- 新規登録1件: dm22rp2x-023 試練の大地ダン・ティラン
  （登録形は提出形と完全一致: partial 既存の
  マッハファイター展開形1能力＋第363弾の確立形
  1能力の2能力ちょうど、keywords なし、補完なし）。
- alias 畳み込み0件（alias dm22rp2-023 には rejects
  行が無く、登録エントリの source.aliases に記録
  されたのみ）。正本判定: 対象 id と alias の両方を
  real.yaml / real_akashic.yaml / real_vocab.yaml /
  real_zone.yaml / proto.yaml / converted.yaml と
  照合し、いずれにも登録なし（proto.yaml のヒットは
  T1092 の notes 内参照のみ）。identity の canon_id
  実測で対象 id が正本そのもの、alias の canon は
  対象 id、aliases_for(名前, 対象id) = [dm22rp2-023]。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [attack_on_entry_turn_punished]
  のため reopen で外してから submit（reopen の出力は
  対象1件ちょうど）。
- converted 10,342→10,343 / rejects 1,970→1,969、
  canonical 重なり0・alias 重なり0・漏れ0。
  attack_on_entry_turn_punished はファミリーがこの
  1件だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_attacking_
  player）は判断待ちのため本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
scenario.build の薄い包みで、tests.conftest は
import しない（第319弾以降の作法）。フィクスチャは
proto T1093（スピードアタッカー役）/ T1094（攻撃
対象役）。「出たターン」の再現は entered_turn を
現在のターンへ合わせる（第363弾の作法）。
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
TARGET = "dm22rp2x-023"
GAP = "attack_on_entry_turn_punished"

MACH = {"kind": "trigger",
        "when": {"event": "move", "to": "bz", "subject": "self"},
        "effect": [{"op": "modify", "select": {"ref": "self"},
                    "mod": {"allow": [{"action": "attack_creature",
                                       "other": {"tapped": False}}]},
                    "duration": "end_of_turn"}]}
TRIGGER = {"kind": "trigger",
           "when": {"event": "attack",
                    "subject": {"owner": "opp",
                                "filter": {"entered_this_turn": True}}},
           "effect": [{"op": "move",
                       "select": {"ref": "event.subject"},
                       "to": "mana", "reason": "put"}]}
FORM = [MACH, TRIGGER]


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


def test_round398_disposition():
    rej = _reject_rows()
    assert len(rej) == 1969
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10343
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias 畳み込み0件
    assert (c.get("source") or {}).get("aliases") == ["dm22rp2-023"]
    assert not (c.get("source") or {}).get("unsupported")
    # 登録形は提出形と完全一致: 2能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert c["name"] == "試練の大地ダン・ティラン"
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 4 and c["power"] == 5000
    assert c["races"] == ["ガイア・コマンド"]
    assert not c.get("keywords")
    d = parse_card(c, TABLES)
    assert TRIGGER in d.abilities and MACH in d.abilities
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive_attack(e, attacker, attacker_owner, target="player",
                  mark_entered=False):
    state = {"attacked": False, "attack_turn": None}
    for _ in range(1500):
        if state["attacked"] and e.s.turn >= state["attack_turn"] + 2:
            break
        if mark_entered:
            for c in e.bz_tops(attacker_owner):
                if e.cdef(c).id == attacker:
                    e.s.cards[c].entered_turn = e.s.turn
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack":
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:{target}"]
            if hit and not state["attacked"]:
                state["attacked"] = True
                state["attack_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            if "no_block" in keys:
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


def test_registered_puts_entered_turn_attacker_into_own_mana(rules):
    """登録カードが場にいる時、出たターンにプレイヤーを
    攻撃した相手クリーチャーは自身のマナゾーンに置かれ、
    シールドはブレイクされない。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1093"]})
    shields = len(e.zlist("shield", 0))
    st = _drive_attack(e, "T1093", 1, mark_entered=True)
    assert st["attacked"]
    assert "T1093" in _defns(e, "mana", 1)
    assert "T1093" not in _defns(e, "bz", 1)
    assert "T1093" not in _defns(e, "mana", 0)
    assert len(e.zlist("shield", 0)) == shields
    assert TARGET in _defns(e, "bz", 0)


def test_registered_not_entered_attacker_attacks_normally(rules):
    """前ターンからいる相手クリーチャーが攻撃しても
    置かれず、シールドは通常どおり1枚ブレイクされる。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1093"]})
    shields = len(e.zlist("shield", 0))
    st = _drive_attack(e, "T1093", 1, mark_entered=False)
    assert st["attacked"]
    assert "T1093" in _defns(e, "bz", 1)
    assert "T1093" not in _defns(e, "mana", 1)
    assert len(e.zlist("shield", 0)) == shields - 1


def test_registered_own_entered_turn_attacker_unaffected(rules):
    """自分のクリーチャーが出たターンに攻撃しても
    置かれない（subject の owner: opp）。"""
    e = _build(rules, {"bz": [TARGET, "T1093"]}, {"bz": ["T1094"]})
    shields = len(e.zlist("shield", 1))
    st = _drive_attack(e, "T1093", 0, mark_entered=True)
    assert st["attacked"]
    assert "T1093" in _defns(e, "bz", 0)
    assert "T1093" not in _defns(e, "mana", 0)
    assert len(e.zlist("shield", 1)) == shields - 1
