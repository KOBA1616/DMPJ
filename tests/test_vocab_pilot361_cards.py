"""語彙パイロット第361弾の対象カード（登録形の検証）。

対象は pure な deck_milled_trigger の全1件で、
ラウンド396で登録:
- dm36-023 奈落の魔黒ジャック・ライガー
（partial は骨格〔keywords [double_breaker] のみ、
types は [creature] で進化の記載も欠けた stub〕で、
未解決は unsupported の deck_milled_trigger 1件だけ
だった。提出形は行データの面情報＋ types
[creature, evolution]・evolve_from
{race_has: E・ソウル}・keywords [double_breaker]＋
第361弾の確立形1能力を足したもの。登録形は提出形と
完全一致）

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
TARGET = "dm36-023"

FORM = [{"kind": "trigger", "zone": "graveyard",
         "when": {"event": "move", "from": "deck", "to": "graveyard",
                  "subject": "self"},
         "effect": [{"op": "may",
                     "body": [{"op": "move",
                               "select": {"ref": "self", "count": 1},
                               "to": "hand", "reason": "return"}]}]}]


def test_target_registered():
    c = find(CONVERTED, TARGET)
    assert c is not None
    assert not (c.get("source") or {}).get("unsupported")
    assert not c.get("aliases")          # alias 畳み込み0件
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert c["keywords"] == ["double_breaker"]
    assert c["name"] == "奈落の魔黒ジャック・ライガー"
    assert c["types"] == ["creature", "evolution"]
    assert c["evolve_from"] == {"race_has": "E・ソウル"}
    assert c["cost"] == 4
    assert c["power"] == 6000
    assert c["races"] == ["ゴースト"]
    d = parse_card(c, TABLES)
    assert FORM[0] in d.abilities


def test_proto_form_matches():
    assert proto_card("T1086")["abilities"] == FORM
