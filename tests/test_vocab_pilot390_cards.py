"""語彙パイロット第390弾の対象カード検証（登録形）。

対象は pure な placed_this_turn_condition の全1件:
- dmsd07-003 ハンマノ裁徒
ラウンド425で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 光 / コスト4 /
パワー6000 / 種族 メタリカ・サバキスト、mana 1、
keywords [blocker, double_breaker]、abilities 無し）に
第390弾の確立形 static〔if {cmp: [{turn_count:
{kind: shield_put, owner: you}}, "==", 0]} の間
deny: [attack_player]〕1件を足し、unsupported を
外したもの。**補完なし**: partial の text は行の
公式テキスト全文と一致する。alias は無い。確立形は
登録済み dmrp08-032 ブロクノ裁徒Z の第1能力と同一。
ファミリーは完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (keywords, text, []) を返し、
part[2] の定型所有は空＝ブロッカー無し（第390弾で実測）。

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
from tests.test_vocab_pilot390 import FORM, FULL_TEXT, STATIC  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmsd07-003"
GAP = "placed_this_turn_condition"
NAME = "ハンマノ裁徒"


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
    assert fam == []                     # ファミリーは完全解消
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 4 and c["power"] == 6000 and c["mana"] == 1
    assert c["races"] == ["メタリカ", "サバキスト"]
    assert c["keywords"] == ["blocker", "double_breaker"]
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完なし）
    # 登録形は提出形と完全一致: 確立形 static 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities      # keywords は static に展開される
    # プロト T1155 と abilities・text・骨格が完全一致
    proto = proto_card("T1155")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "keywords"):
        assert proto[k] == c[k]
