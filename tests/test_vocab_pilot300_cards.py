"""語彙パイロット第300弾のカード側テスト（登録形、ラウンド335で書換）:
skip_turn_remainder 純粋3件はラウンド335で処理済み。

- dm26ex4-031 切札混成 ゴッド・タイム（canon）が登録され、
  abilities == [CIP（destroy マクロ形）, 形A]、キーワードは
  partial の [ex_life, speed_attacker, triple_breaker] のまま
  （submit の連結・テキスト由来の追加なし）。
- dm26ex4-sec012（別印刷）は dm26ex4-031 の alias に畳み込まれ、
  独立エントリではなく reject 行も残らない。2印刷の本文差は
  EXライフ注釈文のみだった（パイロット段階で実測）。
- dmr21-021 時の宮殿 ベルファーレは partial の革命チェンジ
  declare ＋ 形B ＋ 形C で登録。「タップしていれば」は第2節のみ
  （解釈判断。公式FAQに個別裁定なし。docs 参照）。
- skip_turn_remainder は rejects に残らない。

プロトテスト（test_vocab_pilot300.py）とは別プロセスで実行する
こと（conftest の DMSIM_SKIP_CONVERTED 復活の汚染回避）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402

import _conv_cache  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

FORM_A = {"kind": "trigger",
          "when": {"event": "move", "from": "shield",
                   "subject": {"exlife_of": "self"}},
          "effect": [{"op": "may", "body": [{"op": "end_turn"}]}]}
FORM_B = {"kind": "trigger",
          "when": {"event": "move", "from": "bz", "to": "graveyard",
                   "reason": "destroy", "subject": "self"},
          "effect": [{"op": "end_turn"}]}
FORM_C = {"kind": "trigger",
          "when": {"event": "break", "player": "you"},
          "if": {"exists": {"ref": "self", "filter": {"tapped": True}}},
          "effect": [{"op": "end_turn"}]}
CIP_GOD_TIME = {"kind": "trigger",
                "when": {"event": "move", "to": "bz", "subject": "self"},
                "effect": [{"op": "destroy",
                            "select": {"zone": "bz", "owner": "opp",
                                       "filter": {"types": ["creature"],
                                                  "power_le": 5000},
                                       "count": "all"}}]}
DECLARE_BEL = {"kind": "declare", "zone": "hand",
               "when": {"event": "attack",
                        "subject": {"owner": "you",
                                    "filter": {"civs": ["light", "water"],
                                               "race_has": "ドラゴン"}}},
               "effect": [{"op": "swap",
                           "out": {"ref": "event.subject"},
                           "in": {"ref": "self"}}]}

TARGETS = ("dm26ex4-031", "dm26ex4-sec012", "dmr21-021")


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_family_cleared_from_rejects():
    rej = _reject_rows()
    for cid in TARGETS:
        assert cid not in rej, cid
    assert not [r for r in rej.values()
                if "skip_turn_remainder" in (r.get("gaps") or [])]


def test_god_time_registered_and_sec012_folded():
    god = _conv_cache.find(CONVERTED, "dm26ex4-031")
    assert god is not None
    assert god["keywords"] == ["ex_life", "speed_attacker", "triple_breaker"]
    assert god["abilities"] == [CIP_GOD_TIME, FORM_A]
    assert (god.get("source") or {}).get("aliases") == ["dm26ex4-sec012"]
    parse_card(god, TABLES)
    # 別印刷は独立エントリではない（alias としてのみ存在）
    assert _conv_cache.find(CONVERTED, "dm26ex4-sec012") is None


def test_belphaire_registered_with_forms_b_and_c():
    bel = _conv_cache.find(CONVERTED, "dmr21-021")
    assert bel is not None
    assert bel["keywords"] == ["double_breaker"]
    assert bel["abilities"] == [DECLARE_BEL, FORM_B, FORM_C]
    parse_card(bel, TABLES)
