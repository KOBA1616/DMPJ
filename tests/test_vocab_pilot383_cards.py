"""語彙パイロット第383弾の対象カード検証（登録形）。

対象は pure な variable_breaks_by_count の全1件:
- dm06-029 シグマ・トゥレイト
ラウンド418で登録済み。登録形は提出形と完全一致:
partial の組立て済み部分（進化クリーチャー / 火 /
コスト6 / パワー9000 / サバイバー、mana 1、
evolve_from {races: [サバイバー]}）に第383弾の
確立形 static〔breaks {count: 自分の他のサバイバー数}〕
（第130弾）を足し、unsupported を外したもの。
abilities はこの1件ちょうど。補完なし: partial の
text は行の公式テキストの「 / 」連結形で全文と一致。
alias は無い。単面カードで未検証の面は無い。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無いことを
第383弾で実測済みで、ラウンド418は通常どおり submit
できた。

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
from tests.test_vocab_pilot383 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dm06-029"
GAP = "variable_breaks_by_count"
NAME = "シグマ・トゥレイト"


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
    assert c["name"] == NAME
    assert c["types"] == ["creature", "evolution"]
    assert c["civs"] == ["fire"]
    assert c["cost"] == 6 and c["power"] == 9000 and c["mana"] == 1
    assert c["races"] == ["サバイバー"]
    assert c["evolve_from"] == {"races": ["サバイバー"]}
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完なし）
    # 登録形は提出形と完全一致: 確立形 static 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d.abilities == FORM
    # プロト T1141 と abilities・text が完全一致
    proto = proto_card("T1141")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
