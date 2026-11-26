"""語彙パイロット第368弾の対象カード検証（登録形）。

対象は pure な draw_equal_to_chosen_cost の全1件:
- dm21-011 グレート・リンク・テクノロジー
ラウンド403で登録済み。登録形は提出形と完全一致:
partial の骨格〔types [spell] / civs [water] /
cost 10 / mana 1、abilities・spell ともに無し〕に
第368弾の確立形〔シンパシーの static（dm21-020 の
登録先例と同形）＋ spell の choose/draw 2 op〕を
足し、unsupported を外したもの。補完あり: partial の
text は引く条項だけのため、提出時にシンパシー条項を
abilities として補い、text には行の公式テキスト全文を
入れた。単面カードで未検証の面は無い。alias は無い。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import find, proto_card  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dm21-011"
GAP = "draw_equal_to_chosen_cost"

SYMPATHY = {"kind": "static", "zone": "hand", "affects": "self",
            "mod": {"cost": {"amount": -1,
                             "count": {"zone": "bz", "owner": "you",
                                       "filter": {"races": ["グレートメカオー",
                                                            "キカイヒーロー"]}}},
                    "cost_min": 1}}
SPELL = [{"op": "choose",
          "select": {"zone": "bz", "owner": "any",
                     "filter": {"types": ["creature"]},
                     "count": 1},
          "as": "pick"},
         {"op": "draw", "count": {"cost_of": "pick"}}]
FORM_ABILITIES = [SYMPATHY]
FULL_TEXT = ("シンパシー：グレートメカオーとキカイヒーロー(この呪文を唱える時"
             "支払うコストは、バトルゾーンにある自分のグレートメカオーまたは"
             "キカイヒーロー１体につき１少なくなる。ただし、コストは１より"
             "少なくならない)\nバトルゾーンにあるクリーチャーを１体選ぶ。"
             "そのクリーチャーのコストの数と同じ枚数のカードを引く。")


def _reject_rows():
    rows = {}
    with open(ROOT / "data/cards/raw/rejects.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                rows[r["id"]] = r
    return rows


def test_target_registered_and_family_cleared():
    rows = _reject_rows()
    assert TARGET not in rows            # 登録により対象行は解消
    fam = [i for i, x in rows.items() if GAP in (x.get("gaps") or [])]
    assert fam == []                     # ファミリーはこの1件だけだった
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["types"] == ["spell"] and c["civs"] == ["water"]
    assert c["cost"] == 10 and c["mana"] == 1
    assert c["text"] == FULL_TEXT       # 公式テキスト全文（補完）
    assert c["abilities"] == FORM_ABILITIES
    assert len(c["abilities"]) == 1      # static 1件ちょうど
    assert c["spell"] == SPELL
    assert len(c["spell"]) == 2          # choose/draw の2 op ちょうど
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert SYMPATHY in d.abilities
    assert [op["op"] for op in d.spell] == ["choose", "draw"]
    # プロト T1108 と abilities / spell が完全一致
    proto = proto_card("T1108")
    assert proto["abilities"] == FORM_ABILITIES
    assert proto["spell"] == SPELL
