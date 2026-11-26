"""語彙パイロット第394弾の対象カード検証（登録形）。

対象は pure な only_creature_condition の全1件:
- dm26rp3-056 龍装者 クシュトル
ラウンド429で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 光 / コスト3 /
パワー2500 / 種族 ドラゴンギルド・メタリカ、mana 1、
keywords [blocker]、abilities 無し）に第394弾の
確立形 static〔if {cmp: [{count: {zone: bz,
owner: you, filter: {types: [creature]}}}, "==", 1]}
の間 mod: {no_leave: true}〕1件を足し、unsupported を
外したもの。text は行の公式テキスト全文と一致する
（補完なし）。alias は無い。確立形は mod no_leave
（第49弾）を static の if で門番する登録先例
dmx22b-040 の門番パターンの自己版。ファミリーは
完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (['blocker'], 条項テキスト, []) を
返し、part[2] の定型所有は空＝ブロッカー無し
（第394弾で実測）。

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
from tests.test_vocab_pilot394 import FORM, FULL_TEXT, STATIC  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dm26rp3-056"
GAP = "only_creature_condition"
NAME = "龍装者 クシュトル"

# 提出形: partial の骨格＋確立形1件
SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["light"],
    "cost": 3,
    "power": 2500,
    "races": ["ドラゴンギルド", "メタリカ"],
    "mana": 1,
    "keywords": ["blocker"],
    "text": FULL_TEXT,
    "abilities": FORM,
}


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
    assert c["civs"] == ["light"]
    assert c["cost"] == 3 and c["power"] == 2500 and c["mana"] == 1
    assert c["races"] == ["ドラゴンギルド", "メタリカ"]
    assert c["keywords"] == ["blocker"]
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完なし）
    # 登録形は提出形と完全一致: 確立形1能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities         # keywords は static に展開される
    assert len(d.abilities) == 2         # blocker の static＋確立形 static
    # プロト T1161 と abilities・text が完全一致
    proto = proto_card("T1161")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "keywords"):
        assert proto[k] == c[k]
