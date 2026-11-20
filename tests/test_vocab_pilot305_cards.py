"""語彙パイロット第305弾の対象カード検証（ラウンド340で登録済み）。

soul_shift 純粋2件（dm26rp2-001 極まる九極 Q.9 /
dmex18-005 ケンゲキオージャ ～究極火焔～）は、ラウンド340で
登録された。機構は第218弾の soul_shift {floor}＋第274弾の
クラシック適用で実装済みで、本弾はギャップ名のドリフト確認
のみ（新規語彙なし）。ここでは登録形が第305弾の確立形と
完全一致し、対象行が rejects から解消したことを固定する。
実挙動は第305弾本体（プロト）とラウンド340 cards（登録
カード自身）で固定済み。

正本判定（ラウンド340で identity を実データ照合）:
- 対象2件はいずれも canon_id が自身＝独立正本。
- canon_id(dm35-004) = canon_id(dmc64-013) = dmex18-005 で、
  aliases_for（ケンゲキオージャ）とも一致する。alias は
  登録カードの source.aliases に記録されただけ（どちらの
  alias にも reject 行は元々無かった）。

確立形:
- dm26rp2-001: partial は骨格（types に evolution が無く
  evolve_from・abilities も無い）ため、公式全文から
  types [creature, evolution] ＋ evolve_from {civs: [light],
  types: [creature]} ＋ soul_shift {floor: 0} ＋ 離脱誘発
  （第294弾の event.was_under ゲート＋dmex18-s11 先例の
  look 形、order: shuffle）を構築。text は reject 行の
  正式本文。
- dmex18-005: partial ＋ soul_shift {floor: 0} ＋ 勝利誘発
  （第290弾の cause {by: opp, kind: [spell, ability]} 形）。

dmc64-024 / dmc64-025 は soul_shift と evolve_from_deck_onto_self
の2ギャップ行で、本弾の対象外（残ることを確認する）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活
するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

LEAVE_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "subject": "self"},
    "if": {"exists": {"ref": "event.was_under",
                      "filter": {"types": ["creature"],
                                 "cost_le": 9, "cost_ge": 9}}},
    "effect": [
        {"op": "choose",
         "select": {"zone": "deck", "owner": "you", "from_top": 9,
                    "look": True, "count": "all"},
         "reveal": True, "as": "pile"},
        {"op": "may", "body": [
            {"op": "play_free",
             "select": {"ref": "pile",
                        "filter": {"types": ["creature"], "civs": ["light"],
                                   "cost_le": 9, "cost_ge": 9},
                        "count": 1}}]},
        {"op": "move",
         "select": {"ref": "pile", "count": "all"},
         "to": "deck", "position": "bottom", "order": "shuffle",
         "reason": "put"},
    ],
}

WIN_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "subject": "self",
             "cause": {"by": "opp", "kind": ["spell", "ability"]}},
    "effect": [{"op": "win"}],
}

TARGETS = ("dm26rp2-001", "dmex18-005")


def _rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def _conv(cid):
    return _conv_cache.find(CONVERTED, cid)


def test_targets_registered_in_pilot305_forms():
    rows = _rows()
    for tid in TARGETS:
        assert tid not in rows, tid          # rejects から外れた
        c = _conv(tid)
        assert c is not None, tid            # converted に登録済み
        assert not (c.get("source") or {}).get("unsupported"), tid
        parse_card(c, TABLES)
    q9 = _conv("dm26rp2-001")
    d1 = parse_card(q9, TABLES)
    assert d1.soul_shift == {"floor": 0}
    assert d1.evolve_from == {"civs": ["light"], "types": ["creature"]}
    assert q9["abilities"] == [LEAVE_TRIGGER]   # 連結混入なし
    assert sorted(d1.keywords) == ["blocker", "g_strike", "triple_breaker"]
    ken = _conv("dmex18-005")
    d5 = parse_card(ken, TABLES)
    assert d5.soul_shift == {"floor": 0}
    assert d5.evolve_from == {"name_has": "ゴウケンオー"}
    assert ken["abilities"] == [WIN_TRIGGER]
    assert d5.keywords == ["quad_breaker"]
    # alias は source.aliases に記録（独立エントリではない）
    assert (ken.get("source") or {}).get("aliases") == \
        ["dm35-004", "dmc64-013"]
    assert _conv("dm35-004") is None
    assert _conv("dmc64-013") is None


def test_deck_onto_self_rows_remain():
    rows = _rows()
    for tid in ("dmc64-024", "dmc64-025"):
        assert rows[tid].get("gaps") == \
            ["soul_shift", "evolve_from_deck_onto_self"], tid
