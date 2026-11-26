"""再変換ラウンド396（第361弾 deck_milled_trigger）の記録テスト。

- 新規登録1件: dm36-023 奈落の魔黒ジャック・ライガー
  （登録形は提出形と完全一致: move 誘発
  {event: move, from: deck, to: graveyard,
  subject: self}＋zone: graveyard → may [move
  {ref: self, count: 1} to: hand, reason: return]、
  abilities 1件ちょうど、keywords [double_breaker]。
  partial は stub で types に evolution が無く
  evolve_from も欠けていたため、提出形で types
  [creature, evolution] と evolve_from
  {race_has: E・ソウル} を補った）。
- alias 畳み込み0件（identity の canon_id 実測で自 ID、
  aliases_for は空、登録エントリに aliases なし。対象 id は
  real.yaml / real_akashic.yaml / real_vocab.yaml /
  real_zone.yaml / converted.yaml のいずれにも無く、
  proto.yaml のヒットは T1086 の notes 内参照のみ）。
  stale クリーンアップ0件・差し戻し0件。
- 対象1行は gaps = [deck_milled_trigger] のため reopen で
  外してから submit（reopen の出力は対象1件ちょうど）。
- converted 10,340→10,341 / rejects 1,972→1,971、
  canonical 重なり0・alias 重なり0・漏れ0。
  deck_milled_trigger はファミリーがこの1件だけだったため
  完全に解消。
- dm02-046 の stale 行（destroy_self_after_attacking_player）
  は判断待ちのため本ラウンドでも触っていない。

実挙動は登録カード自身で固定する（ミル役は proto T1087、
進化元役は T1088）。ドライバは第361弾本体と同型で、
tests.conftest は import しない（第319弾以降の作法）。
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
TARGET = "dm36-023"
GAP = "deck_milled_trigger"

FORM = [{"kind": "trigger", "zone": "graveyard",
         "when": {"event": "move", "from": "deck", "to": "graveyard",
                  "subject": "self"},
         "effect": [{"op": "may",
                     "body": [{"op": "move",
                               "select": {"ref": "self", "count": 1},
                               "to": "hand", "reason": "return"}]}]}]


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


def test_round396_disposition():
    rej = _reject_rows()
    assert len(rej) == 1971
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10341
    assert not (ids & set(rej))          # canonical 重なり0
    aliases = {a for c in conv for a in (c.get("aliases") or [])}
    assert not (aliases & set(rej))      # alias 重なり0
    c = _conv_cache.find(CONVERTED, TARGET)
    assert c is not None
    assert not c.get("aliases")          # alias 畳み込み0件
    assert not (c.get("source") or {}).get("unsupported")
    assert c["abilities"] == FORM        # 登録形 == 提出形（FORM）
    assert len(c["abilities"]) == 1
    assert c["keywords"] == ["double_breaker"]
    assert c["types"] == ["creature", "evolution"]
    assert c["evolve_from"] == {"race_has": "E・ソウル"}
    d = parse_card(c, TABLES)
    assert FORM[0] in d.abilities
    left = {rid for rid, r in rej.items()
            if GAP in (r.get("gaps") or [])}
    assert left == set(), left           # ファミリー解消
    # 判断待ちの stale 行には触っていない
    assert rej["dm02-046"]["gaps"] == ["destroy_self_after_attacking_player"]


# ---------- 実挙動ドライバ（第361弾本体と同型、対象は登録カード自身） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive(e, plays=(), yes=True, pick=None, stop=None, limit=400):
    plays = list(plays)
    seen = {"yes_no": 0}
    for _ in range(limit):
        if stop is not None and stop():
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "yes_no":
            seen["yes_no"] += 1
            want = "yes" if yes else "no"
            e.answer([keys.index(want)] if want in keys
                     else list(range(d.get("min", 0))))
        elif kind == "main" and d.get("player") == 0:
            hit = next((k for k in plays if k in keys), None)
            if hit is not None:
                plays.remove(hit)
                e.answer([keys.index(hit)])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif pick and any(pick in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys)
                           if pick in k)])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return seen


def _mill_setup(rules):
    # 山札リストの末尾が一番上（deck[0]）なので登録カードが上。
    return _build(rules,
                  {"hand": ["T1087"], "mana": ["T1087", "T1087"],
                   "deck": ["T002", TARGET]},
                  {})


def test_registered_milled_may_add_to_hand(rules):
    """登録カードが山札から墓地に置かれた時、may で
    手札に加えられる。"""
    e = _mill_setup(rules)
    seen = _drive(e, plays=["play:T1087"], yes=True,
                  stop=lambda: TARGET in _defns(e, "hand", 0))
    assert seen["yes_no"] >= 1
    assert TARGET in _defns(e, "hand", 0)
    assert TARGET not in _defns(e, "graveyard", 0)


def test_registered_milled_may_decline_stays_in_graveyard(rules):
    """登録カードの may を断れば墓地に留まる。"""
    e = _mill_setup(rules)
    seen = _drive(e, plays=["play:T1087"], yes=False,
                  stop=lambda: e.s.turn >= 4
                  and TARGET in _defns(e, "graveyard", 0))
    assert seen["yes_no"] >= 1
    assert TARGET in _defns(e, "graveyard", 0)
    assert TARGET not in _defns(e, "hand", 0)


def test_registered_discarded_from_hand_does_not_trigger(rules):
    """登録カードが手札から墓地に置かれた時は誘発しない
    （from: deck の照合）。"""
    e = _build(rules,
               {"hand": [TARGET, "T118"],
                "mana": ["T1088", "T1088"]},
               {})
    seen = _drive(e, plays=["play:T118"], pick=f"zone:{TARGET}",
                  stop=lambda: TARGET in _defns(e, "graveyard", 0))
    seen2 = _drive(e, limit=30)
    assert TARGET in _defns(e, "graveyard", 0)
    assert seen["yes_no"] == 0 and seen2["yes_no"] == 0


def test_registered_evolution_onto_e_soul_base(rules):
    """登録カードは E・ソウルを持つクリーチャーの上に
    進化できる。"""
    e = _build(rules,
               {"bz": ["T1088"], "hand": [TARGET],
                "mana": ["T1088"] * 4},
               {})
    _drive(e, plays=[f"play:{TARGET}"], pick="T1088",
           stop=lambda: TARGET in _defns(e, "bz", 0), limit=200)
    assert TARGET in _defns(e, "bz", 0)
    assert "T1088" in _defns(e, "bz", 0)   # 進化元は下に残る


def test_registered_no_evolution_onto_non_e_soul(rules):
    """登録カードは E・ソウルを持たないクリーチャーには
    進化できない。"""
    e = _build(rules,
               {"bz": ["T1087"], "hand": [TARGET],
                "mana": ["T1088"] * 4},
               {})
    _drive(e, stop=lambda: e.s.turn >= 5, limit=200)
    assert TARGET in _defns(e, "hand", 0)
    assert TARGET not in _defns(e, "bz", 0)
