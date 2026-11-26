"""語彙パイロット第406弾の対象カード検証（登録形）。

対象は distinct_race_count（pure 1件、multi にも現れない）:
- dmx12b-058 口寄の化身
ラウンド441で登録済み。登録形は提出形と完全一致
（差分は validate が identity.aliases_for から
自動付与した source.aliases のみ）: partial の
骨格（クリーチャー / 自然 / コスト6 / パワー4000 /
種族 ミステリー・トーテム、mana 1、keywords・
abilities ともに無し）に第406弾の確立形 trigger
〔when {event: move, to: bz, subject: self}、
effect [may [draw {count: {distinct_race_count:
{selector: {zone: bz, owner: you},
exclude_races: [ミステリー・トーテム]}}}]]]〕
1件を足し、unsupported を外したもの。abilities
はこの1件ちょうど、keywords は無いまま。
**補完あり: text のみ**（partial の text は断片
「種族１種類につき」のため、提出形の text は
公式全文）。alias は dm14-010 / dmc42-015 /
dmc57-015 / dmc61-010 の4件で、いずれも rejects
に独自行は無く、identity 実測で canon_id は
対象・全 alias とも dmx12b-058。distinct_race_count
は完全解消。distinct_race_count の構造化形
{selector, exclude_races} は新規の式形で、
本ラウンドが初回登録。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い
（第406弾で実測）。

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
from tests.test_vocab_pilot406 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmx12b-058"
GAP = "distinct_race_count"
NAME = "口寄の化身"
ALIASES = ["dm14-010", "dmc42-015", "dmc57-015", "dmc61-010"]


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
    for a in ALIASES:
        assert a not in rows             # alias に独自行は無い
        assert find(CONVERTED, a) is None
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 6 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ミステリー・トーテム"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完あり: text のみ）
    # 登録形は提出形と完全一致: abilities は確立形 trigger 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("keywords")          # keywords は無いまま
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ALIASES  # validate の自動付与
    d = parse_card(c, TABLES)
    assert d.abilities == FORM
    assert len(d.abilities) == 1
    assert d.keywords == []
    # プロト T1173 と abilities・text・骨格が完全一致
    proto = proto_card("T1173")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power", "races", "mana"):
        assert proto[k] == c[k]
