"""語彙パイロット第382弾の対象カード検証（登録形）。

対象は pure な attack_after_win_condition の全1件:
- dm30-033 森の格闘家ガンバレット
ラウンド417で登録済み。登録形は提出形と完全一致:
partial の骨格（自然 / コスト1 / パワー5000 /
ドリームメイト、abilities 無し）に第382弾の確立形
static〔if {cmp: [{turn_count: {kind: battle_win,
owner: you}}, "==", 0]} の間 deny: [attack_player,
attack_creature]〕1件を足し、unsupported を外した
もの。abilities は static 1件ちょうど、keywords は
無いまま。補完あり: partial の text は条項の短縮
メモのため、提出形では text に行の公式テキスト
全文を入れた。alias は無い。本カードは新規 kind
battle_win を使う初の登録カード。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無いことを
第382弾で実測済みで、ラウンド417は通常どおり submit
できた。

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
from tests.test_vocab_pilot382 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dm30-033"
GAP = "attack_after_win_condition"
NAME = "森の格闘家ガンバレット"


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
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 1 and c["power"] == 5000 and c["mana"] == 1
    assert c["races"] == ["ドリームメイト"]
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    # 登録形は提出形と完全一致: 確立形 static 1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert not c.get("keywords")         # keywords は無いまま
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d.abilities == FORM
    # プロト T1138 と abilities・text が完全一致
    proto = proto_card("T1138")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
