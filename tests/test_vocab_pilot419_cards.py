"""語彙パイロット第419弾（cards 側）: turn_count_cost_reduction。

対象 dmex14-054 捧程者 アコギエレキ（pure 1件、
multi にも現れない）。partial は骨格＋keywords
[speed_attacker] まで構築済みで text は公式全文
（補完なし）。提出形は手札常在型の static 1件を
足すだけ。形の根拠は本体テストの docstring 参照
（ドリフト: 登録済み dm24ex3-rp2003 / dm24ex3-rp2004
の static {zone: hand, affects: self, mod: {cost:
{amount: -2, count: {sum: [turn_count, turn_count]},
cost_min: 1}}} の kind を summon / cast に差し替えた
もの）。alias は無し。

ラウンド454で登録済み（登録形は提出形と完全一致、
source 以外の全フィールドを照合）。本ファイルは
登録形に書き換え済み。
"""
import copy
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.cards.identity import aliases_for, canon_id  # noqa: E402
from tests._conv_cache import all_cards, find, proto_card  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
TARGET = "dmex14-054"
GAP = "turn_count_cost_reduction"
NAME = "捧程者 アコギエレキ"

FORM = [{"kind": "static", "zone": "hand", "affects": "self",
         "mod": {"cost": {"amount": -2,
                          "count": {"sum": [
                              {"turn_count": {"kind": "summon",
                                              "owner": "you"}},
                              {"turn_count": {"kind": "cast",
                                              "owner": "you"}}]}},
                 "cost_min": 1}}]
FULL_TEXT = ("このターンに自分が召喚したクリーチャー１体または唱えた"
             "呪文１枚につき、このクリーチャーの召喚コストを２少なく"
             "する。ただし、コストは０以下にはならない。\n"
             "スピードアタッカー（このクリーチャーは召喚酔いしない）")
SUBMIT = {"id": TARGET, "name": NAME, "types": ["creature"],
          "civs": ["fire"], "cost": 5, "power": 5000,
          "races": ["ムートピア", "美孔麗王国"], "mana": 1,
          "text": FULL_TEXT, "keywords": ["speed_attacker"],
          "abilities": FORM}


def test_target_registered_and_family_cleared():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 1912
    mine = {r["id"]: r for r in rows}
    assert TARGET not in mine            # 対象行は登録で解消
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []
    conv = all_cards(CONVERTED)
    assert len({c["id"] for c in conv}) == 10399
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形は提出形と完全一致
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")


def test_submit_form_parses_and_matches_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    assert len(d.abilities) == 2   # static 1件＋キーワード展開1件
    p = proto_card("T1190")
    for key in ("name", "types", "civs", "cost", "power", "races",
                "mana", "text", "keywords", "abilities"):
        assert SUBMIT[key] == p[key]


def test_official_row_matches_skeleton():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/ex14.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    row = next(r for r in rows if r["id"] == TARGET)
    assert row["name"] == NAME == SUBMIT["name"]
    assert row["card_type"] == "クリーチャー"
    assert row["civilization"] == "火" and SUBMIT["civs"] == ["fire"]
    assert int(row["cost"]) == SUBMIT["cost"] == 5
    assert int(row["power"]) == SUBMIT["power"] == 5000
    assert int(row["mana"]) == SUBMIT["mana"] == 1
    assert row["race"].split("/") == SUBMIT["races"]
    assert row["text"] == SUBMIT["text"] == FULL_TEXT
