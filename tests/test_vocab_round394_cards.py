"""再変換ラウンド394（第359弾 after_battle_bounce）の記録テスト。

- 新規登録1件: dm27-042 パナオン（登録形は提出形と完全一致:
  partial の骨格〔keywords [blocker, cannot_attack]〕＋
  第359弾の確立形1能力、abilities 1件ちょうど、
  keywords [blocker, cannot_attack]）。
- alias 畳み込み0件（identity の canon_id 実測で自 ID、
  aliases_for は空、登録エントリに aliases なし。対象 id は
  real.yaml / real_akashic.yaml / real_vocab.yaml /
  real_zone.yaml / converted.yaml のいずれにも無く、
  proto.yaml のヒットは T1079 の notes 内参照のみ）。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [after_battle_bounce] のため reopen で
  外してから submit（reopen の出力は対象1件ちょうど）。
- converted 10,338→10,339 / rejects 1,974→1,973、
  canonical 重なり0・alias 重なり0・漏れ0。
  after_battle_bounce はファミリーがこの1件だけだったため
  完全に解消。
- dm02-046 の stale 行（destroy_self_after_attacking_player）
  は判断待ちのため本ラウンドでも触っていない。

実挙動は登録カード自身で固定する。ドライバは
scenario.build の薄い包みで、tests.conftest は
import しない（第319弾以降の作法）。相手役は proto
T1080（パワー3000アタッカー）/ T1081（パワー500
アタッカー）/ T1082（対照ブロッカー）。
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
TARGET = "dm27-042"
GAP = "after_battle_bounce"

FORM = [{"kind": "trigger",
         "when": {"event": "block", "subject": "self"},
         "effect": [{"op": "delayed_trigger",
                     "when": {"event": "attack_end",
                              "target": "self"},
                     "duration": "during_attack",
                     "effect": [{"op": "move",
                                 "select": {"ref": "event.subject"},
                                 "to": "hand",
                                 "reason": "return"}]}]}]


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


def test_round394_disposition():
    rej = _reject_rows()
    assert len(rej) == 1973
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10339
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias 畳み込み0件
    assert not (c.get("source") or {}).get("unsupported")
    assert c["abilities"] == FORM        # 登録形 == 提出形（FORM）
    assert len(c["abilities"]) == 1
    assert c["keywords"] == ["blocker", "cannot_attack"]
    d = parse_card(c, TABLES)
    assert d.keywords == ["blocker", "cannot_attack"]
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（scenario.build 直包み、第359弾本体と同型） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive_attack(e, attacker, block_with=None):
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


def test_registered_bounces_blocked_attacker_after_battle(rules):
    """登録したパナオンがパワー3000の攻撃をブロックすると、
    パナオンはバトルで破壊されるが、バトルの後に攻撃
    クリーチャーは持ち主の手札に戻る。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1080"]})
    st = _drive_attack(e, "T1080", block_with=TARGET)
    assert st["attacked"]
    assert TARGET in _defns(e, "graveyard", 0)   # バトル敗北
    assert "T1080" in _defns(e, "hand", 1)        # バトルの後に手札へ
    assert "T1080" not in _defns(e, "bz", 1)
    assert "T1080" not in _defns(e, "graveyard", 1)


def test_registered_blocked_attacker_destroyed_stays(rules):
    """パワー500の攻撃をブロックすると攻撃側はバトルで
    破壊され、戻しは no-op（墓地に留まる）。パナオンは残る。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1081"]})
    st = _drive_attack(e, "T1081", block_with=TARGET)
    assert st["attacked"]
    assert "T1081" in _defns(e, "graveyard", 1)
    assert "T1081" not in _defns(e, "hand", 1)
    assert TARGET in _defns(e, "bz", 0)


def test_registered_unblocked_attacker_not_bounced(rules):
    """ブロックしなければ誘発せず、攻撃クリーチャーは
    バトルゾーンに残る。"""
    e = _build(rules, {"bz": [TARGET]}, {"bz": ["T1080"]})
    st = _drive_attack(e, "T1080", block_with=None)
    assert st["attacked"]
    assert "T1080" in _defns(e, "bz", 1)
    assert "T1080" not in _defns(e, "hand", 1)
    assert TARGET in _defns(e, "bz", 0)


def test_registered_other_blocker_does_not_trigger(rules):
    """別のブロッカーがブロックした場合はパナオンの誘発は
    起きず、攻撃クリーチャーはバトルゾーンに残る。"""
    e = _build(rules, {"bz": [TARGET, "T1082"]}, {"bz": ["T1080"]})
    st = _drive_attack(e, "T1080", block_with="T1082")
    assert st["attacked"]
    assert "T1082" in _defns(e, "graveyard", 0)   # バトル敗北
    assert "T1080" in _defns(e, "bz", 1)          # 戻されない
    assert "T1080" not in _defns(e, "hand", 1)
    assert TARGET in _defns(e, "bz", 0)
