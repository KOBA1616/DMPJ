"""語彙パイロット第301弾の対象カード検証（ラウンド336で登録済みの形）。

reveal_stay 純粋3件（dmr05-v03 / dmx15-006 / dmx16-006）は
ラウンド336で converted に登録された。登録形が第301弾の確立形
（新 op move_to_event ＋ choose 束縛→判定→移動の順）と完全一致し、
dmx16-006 の別印刷4件が alias に畳み込まれていることを固定する。

注意:
- dmr05-v03 の partial は abilities を持たないスケルトンだった。
  第2節（破壊された時、下にあったクリーチャーをすべて墓地から
  出す）は第294弾の event.was_under ＋ play_free の既存形。
- dmrp22-005 にも reveal_stay のラベルがあるが誤ラベル
  （unsupported は山札の上をターン終了時まで表向きにする別条項
  ＋play_from_deck_top）。ラウンド336でも行には触っておらず、
  rejects に残ったままであることをあわせて固定する。
- conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
  scenario を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402

ROOT = Path(__file__).parent.parent
TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
TARGETS = ("dmr05-v03", "dmx15-006", "dmx16-006")

FORM_A = {"kind": "replace",
          "when": {"event": "move", "from": "bz", "to": "graveyard",
                   "reason": "destroy", "subject": "self"},
          "instead": [
              {"op": "choose",
               "select": {"zone": "deck", "owner": "you", "from_top": 1,
                          "count": 1},
               "reveal": True, "as": "top"},
              {"op": "if",
               "cond": {"not": {"exists": {"ref": "top",
                                           "filter": {"race_has": "ヒューマノイド"}}}},
               "then": [{"op": "move_to_event",
                         "select": {"ref": "event.subject"}}]}]}
FORM_A_C2 = {"kind": "trigger",
             "when": {"event": "move", "from": "bz", "to": "graveyard",
                      "reason": "destroy", "subject": "self"},
             "effect": [{"op": "may", "body": [
                 {"op": "play_free",
                  "select": {"ref": "event.was_under",
                             "zone": "graveyard"}}]}]}
FORM_B = {"kind": "replace",
          "when": {"event": "move", "from": "bz", "subject": "self"},
          "instead": [
              {"op": "may", "body": [
                  {"op": "choose",
                   "select": {"zone": "deck", "owner": "you", "from_top": 1,
                              "count": 1},
                   "as": "picked"}]},
              {"op": "if",
               "cond": {"exists": {"ref": "picked"}},
               "then": [{"op": "move", "select": {"ref": "picked"},
                         "to": "graveyard", "reason": "put"}]},
              {"op": "if",
               "cond": {"not": {"exists": {"ref": "picked",
                                           "filter": {"race_has": "アウトレイジ"}}}},
               "then": [{"op": "move_to_event",
                         "select": {"ref": "event.subject"}}]}]}
FORM_C = {"kind": "replace",
          "when": {"event": "move", "from": "bz",
                   "subject": {"owner": "you",
                               "filter": {"types": ["creature"],
                                          "race_has": "ドラゴン"}}},
          "instead": [
              {"op": "choose",
               "select": {"zone": "deck", "owner": "you", "from_top": 1,
                          "count": 1},
               "as": "seen"},
              {"op": "move", "select": {"ref": "seen"},
               "to": "graveyard", "reason": "put"},
              {"op": "if",
               "cond": {"not": {"any": [
                   {"exists": {"ref": "seen",
                               "filter": {"race_has": "ドラゴン"}}},
                   {"exists": {"ref": "seen",
                               "filter": {"race_has": "ファイアー・バード"}}}]}},
               "then": [{"op": "move_to_event",
                         "select": {"ref": "event.subject"}}]}]}
FORMS = {"dmr05-v03": [FORM_A, FORM_A_C2],
         "dmx15-006": [FORM_B],
         "dmx16-006": [FORM_C]}
KEYWORDS = {"dmr05-v03": ["triple_breaker"],
            "dmx15-006": ["double_breaker"],
            "dmx16-006": ["double_breaker"]}
X16_ALIASES = ["dm22-015", "dmc36-017", "dmc49-019", "dmx09-018"]


def _reject_rows():
    rows = {}
    with open(ROOT / "data/cards/raw/rejects.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                rows[r["id"]] = r
    return rows


def test_targets_registered_with_forms():
    rows = _reject_rows()
    for tid in TARGETS:
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None, tid
        assert c["abilities"] == FORMS[tid], tid
        assert c["keywords"] == KEYWORDS[tid], tid
        assert not (c.get("source") or {}).get("unsupported"), tid
        parse_card(c, TABLES)
        assert tid not in rows, tid
    # dmx16-006 の別印刷4件は alias に畳み込み（独立エントリではない）
    c16 = _conv_cache.find(CONVERTED, "dmx16-006")
    assert (c16.get("source") or {}).get("aliases") == X16_ALIASES
    for a in X16_ALIASES:
        assert _conv_cache.find(CONVERTED, a) is None, a
        assert a not in rows, a


def test_reveal_stay_only_mislabeled_row_remains():
    rows = _reject_rows()
    holders = {rid for rid, r in rows.items() if "reveal_stay" in r["gaps"]}
    assert holders == {"dmrp22-005"}, holders
    assert "play_from_deck_top" in rows["dmrp22-005"]["gaps"]
