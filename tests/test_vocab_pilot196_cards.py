"""語彙パイロット第196弾のカード適用テスト（登録形）。

ラウンド232で eternal_kappa 単独5件を新規登録した。全件、登録形に
エターナル・Κの置換（kind: replace、行き先なし、optional、裏向きマナ
枚数の if、instead は flip_up）が含まれる。dm24bd6-001 のみ
once_per_turn＋2枚版。残件だった多重ギャップ8件はラウンド318で処理し
（3件登録・5件は Κ 節をキーワードとして partial に保存して差し戻し）、
ファミリーは解消した。
"""
import copy
import json
from pathlib import Path

from dmsim.cards import cardstore

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = {"dm23ex3-s03": (3, False), "dm23ex3-s04": (3, False),
              "dm24ex2-023": (3, False), "dm24bd6-001": (2, True),
              "dm24ex2-041": (3, False)}


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def test_registered_forms():
    for cid, (n, once) in REGISTERED.items():
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        reps = [a for a in card["abilities"] if a.get("kind") == "replace"
                and a.get("instead") and a["instead"][0].get("op") == "flip_up"]
        assert len(reps) == 1, cid
        assert reps[0]["instead"][0]["select"]["count"] == n, cid
        assert bool(reps[0].get("once_per_turn")) is once, cid
        assert reps[0].get("optional") is True, cid


def test_family_cleared():
    # ラウンド318で残件8件を処理し、eternal_kappa を gaps に持つ行は無い
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    left = [r for r in rows if "eternal_kappa" in (r.get("gaps") or [])]
    assert left == []
