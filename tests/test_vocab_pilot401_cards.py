"""語彙パイロット第401弾の対象カード検証（登録形）。

対象は block_break（pure 1件、multi にも現れない）:
- dm33-001 超神龍レイ・ソレイユ
ラウンド436で登録済み。登録形は提出形と完全一致:
partial の骨格（光 / コスト4 / パワー6000 /
種族 アポロニア・ドラゴン、mana 1、keywords
[blocker]）に第401弾の確立形 static〔affects
{zone: bz, owner: you, filter: {types: [creature]}},
mod {gain: [trigger {when: {event: block, subject:
self}, effect: [break {player: opp, count: 1}]}]}〕
1件を足し、unsupported を外したもの。abilities は
この1件ちょうど、keywords は [blocker] のまま。
**補完あり: types と evolve_from のみ**（types へ
evolution を追加し、evolve_from {types: [creature],
keyword: blocker} を追加。第372弾・登録先例
dm32-011 と同文・同形。text は partial の時点で
公式全文と一致するため補完なし）。alias は無い
（identity 実測で canon_id は対象自身、
aliases_for = []）。block_break は完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (['blocker'], 条項テキスト, []) を
返し、定型所有は空（第401弾で実測）。

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
from tests.test_vocab_pilot401 import EVOLVE_FROM, FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dm33-001"
GAP = "block_break"
NAME = "超神龍レイ・ソレイユ"


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
    # 補完あり: types は [creature, evolution]
    assert c["types"] == ["creature", "evolution"]
    assert c["civs"] == ["light"]
    assert c["cost"] == 4 and c["power"] == 6000 and c["mana"] == 1
    assert c["races"] == ["アポロニア・ドラゴン"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    assert c["keywords"] == ["blocker"]
    # 補完あり: evolve_from
    assert c["evolve_from"] == EVOLVE_FROM
    # 登録形は提出形と完全一致: 確立形1能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("aliases")        # alias は無い
    assert not src.get("unsupported")
    d = parse_card(c, TABLES)
    # parse では keyword blocker が派生 static に展開されるため、
    # abilities は [blocker 派生 static, 確立形 static] の2件
    assert len(d.abilities) == 2
    assert d.abilities[1] == FORM[0]
    assert d.abilities[0].get("keyword") == "blocker"
    assert d.evolve_from == EVOLVE_FROM
    # プロト T1168 と abilities・evolve_from・text・骨格が完全一致
    proto = proto_card("T1168")
    assert proto["abilities"] == FORM
    assert proto["evolve_from"] == EVOLVE_FROM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power",
              "races", "mana", "keywords"):
        assert proto[k] == c[k]
