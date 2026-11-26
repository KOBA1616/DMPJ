"""語彙パイロット第392弾の対象カード検証（登録形）。

対象は pure な civilization_breaker の全1件:
- dm27-010 彩強の巨人
ラウンド427で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 自然 / コスト9 /
パワー11000 / 種族 ジャイアント、mana 1、
keywords・abilities 無し）に、mod breaks の式形式
{civ_count: セレクタ}（第79弾。登録先例 dmc34-025 は
「追加で」型で base 既定1）と第145弾で実挙動検証済みの
base: 0（バラエティ・ブレイカーと同機構）を組み合わせた
static {affects: self, mod: {breaks: {civ_count:
{zone: mana, owner: you}, base: 0}}} 1件を足し、
unsupported を外したもの。補完あり: partial の text は
「文明ブレイカー」だけのため、text には行の公式
テキスト全文を入れた。alias は無い。breaks の
{civ_count ＋ base: 0} は本カードが初の登録。
ファミリーは完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い（第392弾で実測）。

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
from tests.test_vocab_pilot392 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dm27-010"
GAP = "civilization_breaker"
NAME = "彩強の巨人"


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
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 9 and c["power"] == 11000 and c["mana"] == 1
    assert c["races"] == ["ジャイアント"]
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    # 登録形は提出形と完全一致: 確立形 static 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 1
    # プロト T1159 と abilities・text が完全一致
    proto = proto_card("T1159")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power", "races", "mana"):
        assert proto[k] == c[k]
