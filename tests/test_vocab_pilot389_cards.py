"""語彙パイロット第389弾の対象カード検証（登録形）。

対象は pure な mill_count_variable の全1件:
- dmex10-014 死罠の杖
ラウンド424で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 闇・自然 / コスト4 /
パワー5000 / 種族 ビーストフォーク・不死樹王国、
mana 1、keywords・abilities ともに無し）に、
CIP 誘発 [choose {select: {zone: bz, owner: opp,
filter: {types: [creature]}, count: 1}, as: pick},
mana_put {select: {ref: pick}}, mill {owner: you,
count: {cost_of: pick}}] の1能力を足し、unsupported を
外したもの。補完あり: partial の text は条項の断片
（「そのクリーチャーのコストと同じ枚数」）のため、
text には行の公式テキスト全文を入れた。alias は無い。
mill の count への式渡し（{cost_of: pick}）は
本カードが初の登録。ファミリーは完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い（第389弾で実測）。

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
from tests.test_vocab_pilot389 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmex10-014"
GAP = "mill_count_variable"
NAME = "死罠の杖"


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
    assert c["types"] == ["creature"]
    assert c["civs"] == ["darkness", "nature"]
    assert c["cost"] == 4 and c["power"] == 5000 and c["mana"] == 1
    assert c["races"] == ["ビーストフォーク", "不死樹王国"]
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    # 登録形は提出形と完全一致: 確立形1能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 1
    # プロト T1154 と abilities・text が完全一致
    proto = proto_card("T1154")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power", "races", "mana"):
        assert proto[k] == c[k]
