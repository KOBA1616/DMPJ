"""語彙パイロット第405弾の対象カード検証（登録形）。

対象は count_distinct_races（pure 1件、multi にも現れない）:
- dm20-037 反骨鉄拳バーニアン
ラウンド440で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 光 / コスト4 / パワー2000 /
種族 グレートメカオー、mana 1、keywords・abilities
ともに無し）に第405弾の確立形 static〔affects: self,
mod {power: {amount: 2000, count: {distinct_race_count:
{zone: bz, owner: opp, filter: {types:
[creature]}}}}}〕1件を足し、unsupported を外した
もの。abilities はこの1件ちょうど、keywords は
無いまま。**補完なし**（partial の text は行の
公式テキスト全文と一致）。alias は無い（identity
実測で canon_id は対象自身、aliases_for = []）。
count_distinct_races は完全解消。distinct_race_count
は新規式キーの初回登録。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い
（第405弾で実測）。

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
from tests.test_vocab_pilot405 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dm20-037"
GAP = "count_distinct_races"
NAME = "反骨鉄拳バーニアン"


def _reject_rows():
    rows = {}
    with open(ROOT / "data/cards/raw/rejects.jsonl",
              encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                rows[r["id"]] = r
    return rows


def test_target_registered_and_family_cleared():
    rows = _reject_rows()
    assert TARGET not in rows            # 登録により対象行は解消
    fam = [i for i, x in rows.items()
           if GAP in (x.get("gaps") or [])]
    assert fam == []                     # ファミリー完全解消
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 4 and c["power"] == 2000 and c["mana"] == 1
    assert c["races"] == ["グレートメカオー"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は確立形 static 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("keywords")          # keywords は無いまま
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")
    d = parse_card(c, TABLES)
    assert FORM[0] in d.abilities
    assert len(d.abilities) == 1
    assert d.keywords == []
    # プロト T1172 と abilities・text・骨格が完全一致
    proto = proto_card("T1172")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power", "races", "mana"):
        assert proto[k] == c[k]
