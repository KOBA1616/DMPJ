"""語彙パイロット第295弾のカード適用テスト（登録形）: ラウンド330の結果。

対象は super_shield_plus 純粋3件:
- dmex06-010 奇跡の精霊ネオ・ミルザム（形A）: ラウンド330で新規登録
- dm28-s01 超神龍ラディオ・ヤエサル（形A）: ラウンド330で新規登録
  （第293弾のマナ進化Vはラウンド328で解け、本節だけ差し戻されていた。
  進化面と W・ブレイカーは partial に銀行済みだった）
- dmx19-s06 奇跡の精霊ミルザム（形B）: real.yaml に手変換済みだった
  ため converted へは登録せず、ラウンド330で reject 行の除去のみ
  （stale 解消。converted との二重登録はしない）

登録形は partial に第295弾の条項（op shield_plus の each / count 引数
つき CIP 誘発）を足したもの。実挙動の検証は
tests/test_vocab_round330_cards.py で行う。

プロトテスト（test_vocab_pilot295.py）とは別プロセスで実行すること
（conftest の DMSIM_SKIP_CONVERTED 復活で load_rules キャッシュが
汚染される）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import yaml  # noqa: E402

from dmsim.cards import cardstore  # noqa: E402

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REAL = DATA / "cards" / "real.yaml"
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

CIP = {"event": "move", "to": "bz", "subject": "self"}

# 第295弾の提出形（partial に足した条項）
ADDITIONS = {
    "dmex06-010": {"kind": "trigger", "when": dict(CIP),
                   "effect": [{"op": "may",
                               "body": [{"op": "shield_plus", "each": True}]}]},
    "dm28-s01": {"kind": "trigger", "when": dict(CIP),
                 "effect": [{"op": "may",
                             "body": [{"op": "shield_plus", "each": True}]}]},
}

REGISTERED = sorted(ADDITIONS)


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_registered_forms():
    rej = _reject_rows()
    for cid, add in ADDITIONS.items():
        c = _conv_cache.find(CONVERTED, cid)
        assert c is not None, cid                      # 登録された
        assert cid not in rej, cid                     # rejects に残らない
        assert "unsupported" not in (c.get("source") or {}), cid
        d = parse_card(c, TABLES)
        assert add in d.abilities, cid
    # dm28-s01 は進化面（第293弾形A）が銀行済みのまま効く
    d = parse_card(_conv_cache.find(CONVERTED, "dm28-s01"), TABLES)
    assert d.face(None).evolve_zone == "mana"


def test_dmx19_s06_stays_in_real_only():
    """形B の dmx19-s06 は real.yaml の手変換が正本。converted に
    二重登録されず、reject 行も残らない。"""
    rej = _reject_rows()
    assert "dmx19-s06" not in rej
    assert _conv_cache.find(CONVERTED, "dmx19-s06") is None
    data = yaml.safe_load(open(REAL, encoding="utf-8"))
    cards = data.get("cards", data) if isinstance(data, dict) else data
    assert any(c.get("id") == "dmx19-s06" for c in cards)


def test_family_cleared():
    rej = _reject_rows()
    assert not [r["id"] for r in rej.values()
                if "super_shield_plus" in (r.get("gaps") or [])]
