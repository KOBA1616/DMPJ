"""語彙パイロット第385弾の対象カード検証（登録形）。

対象は pure な cost_amount_draw の全1件:
- promoy18-087 リッチ警官 キャッシュ！
ラウンド420で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 光・水 / コスト8 /
パワー2500 / 種族 ヒューマノイド、mana 1、keywords・
abilities ともに無し）に第385弾の確立形〔CIP 誘発
may [choose {zone: hand, as: pick}, draw {count:
{cost_of: pick}}]〕1能力を足し、unsupported を
外したもの。abilities はこの1件ちょうど、keywords
は無いまま。補完あり: partial の text は条項の断片
（「コストと同じ枚数引く」）だけのため、登録形では
text に行の公式テキスト全文が入っている。alias は
無い。単面カードで未検証の面は無い。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無いことを
第385弾で実測済みで、ラウンド420は通常どおり
submit できた。

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
from tests.test_vocab_pilot385 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "promoy18-087"
GAP = "cost_amount_draw"
NAME = "リッチ警官 キャッシュ！"


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
    assert c["types"] == ["creature"]
    assert c["civs"] == ["light", "water"]
    assert c["cost"] == 8 and c["power"] == 2500 and c["mana"] == 1
    assert c["races"] == ["ヒューマノイド"]
    assert not c.get("keywords")         # keywords は無いまま
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    # 登録形は提出形と完全一致: 確立形 trigger 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d.abilities == FORM
    # プロト T1148 と abilities・text が完全一致
    proto = proto_card("T1148")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
