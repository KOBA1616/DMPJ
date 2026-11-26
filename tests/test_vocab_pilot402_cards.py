"""語彙パイロット第402弾の対象カード検証（登録形）。

対象は indestructible_duration（pure 1件、multi にも
現れない）:
- promoy13-019 天英雄 ヴァルハラ・デューク
ラウンド437で登録済み。登録形は提出形と完全一致:
partial の骨格（光 / コスト7 / パワー7000 / 種族
エンジェル・コマンド・ドラゴン、mana 1、keywords
[double_breaker]）に第402弾の確立形 trigger〔when
{event: move, to: bz, subject: self}、if {cmp:
[{count: {zone: mana, owner: you, filter: {civs:
[light]}}}, ">=", 7]}、effect [modify {select:
{zone: bz, owner: you, filter: {types: [creature]},
count: all}, mod: {indestructible: true}, duration:
until_next_own_turn_start}]〕1件を足し、unsupported
を外したもの。abilities はこの1件ちょうど、
keywords は [double_breaker] のまま。**補完なし**
（partial の text は公式全文と一致）。alias は無い
（identity 実測で canon_id は対象自身、
aliases_for = []）。indestructible_duration は
完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (['double_breaker'], 条項テキスト,
[]) を返し、定型所有は空（第402弾で実測）。

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
from tests.test_vocab_pilot402 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "promoy13-019"
GAP = "indestructible_duration"
NAME = "天英雄 ヴァルハラ・デューク"


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
    fam = sorted(i for i, x in rows.items()
                 if GAP in (x.get("gaps") or []))
    assert fam == []                     # ファミリーは完全解消
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 7 and c["power"] == 7000 and c["mana"] == 1
    assert c["races"] == ["エンジェル・コマンド・ドラゴン"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    assert c["keywords"] == ["double_breaker"]
    # 登録形は提出形と完全一致: 確立形1能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("aliases")        # alias は無い
    assert not src.get("unsupported")
    d = parse_card(c, TABLES)
    # parse では keyword double_breaker が派生 static に展開されるため、
    # abilities は [double_breaker 派生 static, 確立形 trigger] の2件
    assert len(d.abilities) == 2
    assert d.abilities[0].get("keyword") == "double_breaker"
    assert d.abilities[1] == FORM[0]
    # プロト T1169 と abilities・text・骨格が完全一致
    proto = proto_card("T1169")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power",
              "races", "mana", "keywords"):
        assert proto[k] == c[k]
