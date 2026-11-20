"""語彙パイロット第299弾のカード側テスト（登録形）:
under_card_removed 純粋3件（dm34-014 / dm34-022 / dm34-032）は
ラウンド334で登録済み。本ファイルは登録形（converted の
abilities が提出形 FORMS と完全一致し、partial の連結残り・
テキスト由来の追加が無いこと）を固定する。

提出形の要点:
- 誘発対は3件共通: 破壊側 {reason: destroy, subject: {owner: you,
  other: true, filter: {types: [creature]}}, from_under: false} と
  下カード側 {from_under: {owner: you, filter: {types: [evolution]}}}。
- dm34-014 の効果は modify {power: -1000} duration: end_of_turn。
- dm34-022 の効果は choose {from_top: 1, count: 1} で上を束縛し、
  呪文なら may [choose {ref, reveal: true} → move to hand]。
  choose {count: 0, up_to: true} 形（dmr08-008 の登録形）は
  select の mx=0 で常に空になる不発形なので使わない（第299弾で
  実測。converted に同形の select が334箇所ある既存問題として
  docs に記録し、修繕は棚卸し＋修繕の別ステージ課題）。
- dm34-032 の効果は may [choose_number → choose {reveal: true}
  → if {cost_of == declared} then 破壊 power_le 5000]。

プロトテスト（test_vocab_pilot299.py）とは別プロセスで実行する
こと（conftest の DMSIM_SKIP_CONVERTED 復活の汚染回避）。
"""
import copy
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

WHEN_DESTROY = {"event": "move", "from": "bz", "to": "graveyard",
                "reason": "destroy",
                "subject": {"owner": "you", "other": True,
                            "filter": {"types": ["creature"]}},
                "from_under": False}
WHEN_UNDER = {"event": "move", "from": "bz", "to": "graveyard",
              "from_under": {"owner": "you",
                             "filter": {"types": ["evolution"]}}}
EFFECT_014 = [{"op": "modify",
               "select": {"zone": "bz", "owner": "opp", "count": 1},
               "mod": {"power": -1000}, "duration": "end_of_turn"}]
EFFECT_022 = [{"op": "choose",
               "select": {"zone": "deck", "owner": "you", "from_top": 1,
                          "count": 1},
               "as": "top"},
              {"op": "if",
               "cond": {"exists": {"ref": "top",
                                   "filter": {"types": ["spell"]}}},
               "then": [{"op": "may", "body": [
                   {"op": "choose", "select": {"ref": "top", "count": 1},
                    "as": "hit", "reveal": True},
                   {"op": "move", "select": {"ref": "hit"},
                    "to": "hand", "reason": "draw"}]}]}]
EFFECT_032 = [{"op": "may", "body": [
    {"op": "choose_number", "as": "n"},
    {"op": "choose", "select": {"zone": "deck", "owner": "you",
                                 "count": 1},
     "as": "top", "reveal": True},
    {"op": "if",
     "cond": {"cmp": [{"cost_of": {"ref": "top"}}, "==",
                      {"declared": "n"}]},
     "then": [{"op": "move",
               "select": {"zone": "bz", "owner": "opp",
                          "filter": {"power_le": 5000}, "count": 1},
               "to": "graveyard", "reason": "destroy"}]}]}]


def _pair(effect):
    return [{"kind": "trigger", "when": copy.deepcopy(WHEN_DESTROY),
             "effect": copy.deepcopy(effect)},
            {"kind": "trigger", "when": copy.deepcopy(WHEN_UNDER),
             "effect": copy.deepcopy(effect)}]


FORMS = {"dm34-014": _pair(EFFECT_014), "dm34-022": _pair(EFFECT_022),
         "dm34-032": _pair(EFFECT_032)}


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_targets_registered_in_pilot299_forms():
    rej = _reject_rows()
    for cid, abilities in FORMS.items():
        assert cid not in rej, cid                    # reject 行は残らない
        entry = _conv_cache.find(CONVERTED, cid)
        assert entry is not None, cid                 # 登録済み
        assert not (entry.get("source") or {}).get("unsupported"), cid
        assert entry["abilities"] == abilities, cid   # 提出形と完全一致
        assert not entry.get("keywords"), cid         # テキスト由来の追加なし
        parse_card(entry, TABLES)
    # under_card_removed は解消
    assert not [r for r in rej.values()
                if "under_card_removed" in (r.get("gaps") or [])]
