"""語彙パイロット第294弾のカード適用テスト（登録形）: ラウンド329の結果。

対象は was_under_cards_return 純粋4件で、全件が converted.yaml に
登録された（新規登録4件、差し戻し0件）:
- dm25rp2-033 ～時空の工兵～（形A: 破壊された時、下にあったカードを
  すべて墓地から手札に戻す）
- dmex12-004 デュエにゃん皇帝（形B: 破壊された時、下にあった
  ファンキー・ナイトメアをすべて墓地から出す）
- dmex12-037 超轟速 レッド・エンド（形C: 破壊された時、下に重ねて
  あったカードのうち1枚を墓地から出してもよい）
- dm24bd5-012 氷結龍 ダイヤモンド・クレバス（形D: 離れた時、下に
  あったカードをすべて手札に加える。ラウンド328で同理由により
  差し戻され、本ラウンドで登録）

登録形は partial に第294弾の条項（move レコードの was_under＋セレクタ
{ref: event.was_under}）のトリガーを1つ足したもの。実挙動の検証は
tests/test_vocab_round329_cards.py で行う。

プロトテスト（test_vocab_pilot294.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが
汚染される）。
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

DESTROY_SELF = {"event": "move", "from": "bz", "to": "graveyard",
                "reason": "destroy", "subject": "self"}

# ラウンド329の登録形（partial に足した条項）
ADDITIONS = {
    "dm25rp2-033": {"kind": "trigger", "when": dict(DESTROY_SELF),
                    "effect": [{"op": "move",
                                "select": {"ref": "event.was_under",
                                           "zone": "graveyard"},
                                "to": "hand", "reason": "return"}]},
    "dmex12-004": {"kind": "trigger", "when": dict(DESTROY_SELF),
                   "effect": [{"op": "play_free",
                               "select": {"ref": "event.was_under",
                                          "zone": "graveyard",
                                          "filter": {"race_has": "ファンキー・ナイトメア"}}}]},
    "dmex12-037": {"kind": "trigger", "when": dict(DESTROY_SELF),
                   "effect": [{"op": "may",
                               "body": [{"op": "play_free",
                                         "select": {"ref": "event.was_under",
                                                    "zone": "graveyard",
                                                    "count": 1}}]}]},
    "dm24bd5-012": {"kind": "trigger",
                    "when": {"event": "move", "from": "bz", "subject": "self"},
                    "effect": [{"op": "move",
                                "select": {"ref": "event.was_under",
                                           "zone": ["graveyard", "mana",
                                                    "deck", "shield"]},
                                "to": "hand", "reason": "return"}]},
}

ALIASES = {
    "dm25rp2-033": ["dm25rp2-sec19"],
    "dmex12-004": ["dmex08-121", "dmr19-005"],
    "dmex12-037": ["dmex08-217", "promoy14-045"],
    "dm24bd5-012": ["dm23rp1-tr7", "dm24ex1-006", "dmex12-s15"],
}

KEYWORDS = {
    "dm25rp2-033": ["g_strike"],
    "dmex12-004": ["double_breaker"],
    "dmex12-037": ["double_breaker"],
    "dm24bd5-012": ["powered_breaker"],
}


def _reject_ids():
    out = set()
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            out.add(json.loads(line)["id"])
    return out


def test_targets_registered_in_round329():
    rej = _reject_ids()
    for tid, add in ADDITIONS.items():
        c = _conv_cache.find(CONVERTED, tid)
        assert c is not None, tid                    # 登録された
        assert tid not in rej, tid                   # rejects に残らない
        assert "unsupported" not in (c.get("source") or {}), tid
        assert sorted((c.get("source") or {}).get("aliases") or []) == \
            sorted(ALIASES[tid]), tid
        assert c.get("keywords") == KEYWORDS[tid], tid
        d = parse_card(c, TABLES)
        trigs = [a for a in d.abilities if a.get("kind") == "trigger"
                 and a.get("when", {}).get("event") == "move"]
        assert add in trigs, (tid, trigs)


def test_family_cleared():
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            assert "was_under_cards_return" not in (r.get("gaps") or []), r["id"]
