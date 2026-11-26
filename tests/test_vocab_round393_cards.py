"""再変換ラウンド393（第358弾 destroy_after_attacking_on_entry_turn）
の記録テスト。

- 新規登録1件: dm22rp1-039 落下男（登録形は提出形と完全一致:
  partial の骨格〔keywords [slayer]〕＋第358弾の確立形1能力、
  abilities 1件ちょうど、keywords [slayer]）。
- alias 畳み込み0件（identity の canon_id 実測で自 ID、
  aliases_for は空、登録エントリに aliases なし。対象 id は
  real.yaml / real_akashic.yaml / real_vocab.yaml /
  real_zone.yaml / converted.yaml のいずれにも無く、
  proto.yaml のヒットは T1076 の notes 内参照のみ）。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [destroy_after_attacking_on_entry_turn]
  のため reopen で外してから submit（reopen の出力は
  対象1件ちょうど）。
- converted 10,337→10,338 / rejects 1,975→1,974、
  canonical 重なり0・alias 重なり0・漏れ0。
  destroy_after_attacking_on_entry_turn はファミリーが
  この1件だけだったため完全に解消。
- dm02-046 の stale 行（destroy_self_after_attacking_player）
  は判断待ちのため本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
scenario.build の薄い包みで、tests.conftest は
import しない（第319弾以降の作法）。相手役は proto
T1077（スピードアタッカー）/ T1078（ブロッカー）。
「出たターン」の再現は第358弾本体と同じく対象の
entered_turn を現在のターンへ合わせる操作で行う。
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
TARGET = "dm22rp1-039"
GAP = "destroy_after_attacking_on_entry_turn"

_OPP_NEW = {"owner": "opp", "filter": {"entered_this_turn": True}}
FORM = [{"kind": "trigger",
         "when": {"event": "attack", "subject": _OPP_NEW},
         "effect": [{"op": "delayed_trigger",
                     "when": {"event": "attack_end",
                              "subject": _OPP_NEW},
                     "duration": "during_attack",
                     "effect": [{"op": "destroy",
                                 "select": {"ref": "event.subject"}}]}]}]


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


def test_round393_disposition():
    rej = _reject_rows()
    assert len(rej) == 1974
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10338
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias 畳み込み0件
    assert not (c.get("source") or {}).get("unsupported")
    assert c["abilities"] == FORM        # 登録形 == 提出形（FORM）
    assert len(c["abilities"]) == 1
    assert c["keywords"] == ["slayer"]
    d = parse_card(c, TABLES)
    assert d.keywords == ["slayer"]
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（scenario.build 直包み、第358弾本体と同型） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive_attack(e, attacker, attacker_owner, block_with=None,
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
                   if block_with and k.startswith(f"bz:{block_with}:")]
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


def test_registered_destroys_entered_this_turn_attacker(rules):
    """登録した落下男がいる時、出たターンに攻撃した相手
    クリーチャーは、ブロックされずに攻撃した後、破壊される。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1077"]})
    st = _drive_attack(e, "T1077", 1, mark_entered=True)
    assert st["attacked"]
    assert "T1077" in _defns(e, "graveyard", 1)
    assert "T1077" not in _defns(e, "bz", 1)
    assert TARGET in _defns(e, "bz", 0)


def test_registered_destroys_even_after_winning_battle(rules):
    """出たターンに攻撃した相手が小ブロッカーに勝っても、
    バトルの後に破壊される。"""
    e = _build(rules, {"bz": [TARGET, "T1078"]}, {"bz": ["T1077"]})
    st = _drive_attack(e, "T1077", 1, block_with="T1078",
                       mark_entered=True)
    assert st["attacked"]
    assert "T1078" in _defns(e, "graveyard", 0)
    assert "T1077" in _defns(e, "graveyard", 1)
    assert TARGET in _defns(e, "bz", 0)


def test_registered_spares_not_entered_attacker(rules):
    """前ターンからいる相手クリーチャーが攻撃しても
    破壊されない。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1077"]})
    st = _drive_attack(e, "T1077", 1, mark_entered=False)
    assert st["attacked"]
    assert "T1077" in _defns(e, "bz", 1)
    assert "T1077" not in _defns(e, "graveyard", 1)
