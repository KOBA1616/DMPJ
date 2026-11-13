"""語彙パイロット第206弾のカード適用テスト（登録形）。

ラウンド242: rainbonus 単独7件を全件新規登録し、ファミリーは全解消
した。dmex14-042 の「攻撃できない」は展開形を id: above つきで直接
書き、レインボーナス静的が ignore_ids で無視する形（鬼タイムの先例と
同型。submit がテキストから cannot_attack_player を補完すると二重の
deny になり無視が効かないため、登録後に同形へ修正し挙動まで確認した）。
dmex14-043 の効果は spell フィールドにある。
"""
import copy
import json
from pathlib import Path

from dmsim.cards import cardstore
from dmsim.cards.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = ("dmex14-002", "dmex14-003", "dmex14-006", "dmex14-007",
              "dmex14-008", "dmex14-042", "dmex14-043")


def _converted(cid):
    for c in cardstore.read(CONVERTED):
        if c["id"] == cid:
            return c
    raise KeyError(cid)


def test_registered_forms():
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
    c42 = _converted("dmex14-042")
    assert "cannot_attack_player" not in (c42.get("keywords") or [])
    assert any(a.get("id") == "above"
               and a.get("mod", {}).get("deny") == ["attack_player"]
               for a in c42["abilities"])
    assert any(a.get("mod", {}).get("ignore_ids") == ["above"]
               for a in c42["abilities"])
    assert _converted("dmex14-043").get("spell")


def test_family_cleared():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    assert not [r for r in rows if "rainbonus" in (r.get("gaps") or [])]
