"""語彙パイロット第384弾の対象カード検証（登録形）。

対象は pure な creatures_enter_tapped の全1件:
- dm06-001 銀界の守護者ル・ギラ・レシール
ラウンド419で登録済み。登録形は提出形と完全一致:
partial の組立て済み部分（クリーチャー / 光 / コスト5 /
パワー4000 / ガーディアン、mana 1、keywords
[blocker, cannot_attack_player]）に第384弾の確立形
static〔affects {zone: bz, owner: any, filter
{types: [evolution]}}, mod {grant: [enters_tapped]}〕
（第339弾の一般化）を足し、unsupported を外したもの。
abilities はこの1件ちょうど。補完なし: partial の
text は行の公式テキスト全文と一致。alias は無い。
単面カードで未検証の面は無い。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (['blocker', 'cannot_attack_player'],
残りテキスト, []) を返し、keywords は定型所有だが
partial の keywords と同一で能力の定型所有は無い
（part[2] は空）ことを第384弾で実測済みで、
ラウンド419は通常どおり submit できた。

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
from tests.test_vocab_pilot384 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dm06-001"
GAP = "creatures_enter_tapped"
NAME = "銀界の守護者ル・ギラ・レシール"


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
    assert c["civs"] == ["light"]
    assert c["cost"] == 5 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ガーディアン"]
    assert c["keywords"] == ["blocker", "cannot_attack_player"]
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完なし）
    # 登録形は提出形と完全一致: 確立形 static 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    # keywords は常在型に展開され、確立形 static も含まれる
    assert FORM[0] in d.abilities
    assert len(d.abilities) == 3
    # プロト T1144 と abilities・text が完全一致
    proto = proto_card("T1144")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
