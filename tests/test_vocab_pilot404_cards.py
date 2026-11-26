"""語彙パイロット第404弾の対象カード検証（登録形）。

対象は draw_count_by_card（pure 1件）:
- dmr05-021 知識の包囲網
ラウンド439で登録済み。登録形は提出形と完全一致:
partial の骨格（呪文 / 水 / コスト7 / mana 1、
spell・abilities ともに無し）に第404弾の確立形
spell [choose {select: {zone: hand, owner: you,
count: 1}, as: pick}, draw {count: {cost_of:
pick}}] の2 op を足し、unsupported を外したもの。
spell はこの2 op ちょうど、abilities は無いまま。
**補完あり: spell と text**（text には行の公式
テキスト全文を入れた。登録後の全文一致も照合
済み）。alias は無い（identity 実測で canon_id
は対象自身、aliases_for = []）。
draw_count_by_card は完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い
（第404弾で実測）。

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
from tests.test_vocab_pilot404 import FULL_TEXT, SPELL  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmr05-021"
GAP = "draw_count_by_card"
NAME = "知識の包囲網"


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
    assert c["types"] == ["spell"] and c["civs"] == ["water"]
    assert c["cost"] == 7 and c["mana"] == 1
    assert c["text"] == FULL_TEXT        # 公式全文（補完: text）
    # 登録形は提出形と完全一致: spell は確立形2 op ちょうど
    assert c["spell"] == SPELL
    assert len(c["spell"]) == 2
    assert not c.get("abilities")        # abilities は無いまま
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")
    d = parse_card(c, TABLES)
    assert [op["op"] for op in d.spell] == ["choose", "draw"]
    assert not d.abilities
    # プロト T1171 と spell・text・骨格が完全一致
    proto = proto_card("T1171")
    assert proto["spell"] == SPELL
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "mana"):
        assert proto[k] == c[k]
