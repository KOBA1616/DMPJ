"""語彙パイロット第360弾の対象カード（登録形の検証）。

対象は pure な breaks_plus_one の全1件で、
ラウンド395で登録:
- dm14-s08 ファイナル・ドラグアーマー
（partial は static {affects: crossed, mod: {power_when
{amount: 5000, when: attacking}, add_races:
[アーマード・ドラゴン]}} を既に持ち、未解決は
unsupported の breaks_plus_one 1件だけだった。提出形は
partial の既存 static の mod に breaks_add: 1 を足した
もの。登録形は提出形と完全一致。partial に keywords は
無く、登録エントリにも keywords は無い）

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import find, proto_card  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
TARGET = "dm14-s08"

FORM = [{"kind": "static", "affects": "crossed",
         "mod": {"power_when": {"amount": 5000, "when": "attacking"},
                 "breaks_add": 1,
                 "add_races": ["アーマード・ドラゴン"]}}]


def test_target_registered():
    c = find(CONVERTED, TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert not c.get("aliases")          # alias 畳み込み0件
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("keywords")         # partial に keywords は無い
    assert c["name"] == "ファイナル・ドラグアーマー"
    assert c["types"] == ["cross_gear"]
    assert c["cost"] == 3
    d = parse_card(c, TABLES)
    assert FORM[0] in d.abilities


def test_proto_form_matches():
    assert proto_card("T1083")["abilities"] == FORM
