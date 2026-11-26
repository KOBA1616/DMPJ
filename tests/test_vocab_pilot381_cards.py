"""語彙パイロット第381弾の対象カード検証（登録形）。

対象は pure な opponent_cannot_summon_or_cast_next_turn
の全1件:
- dm21-014 デビル・リンク・タブー
ラウンド416で登録済み。登録形は提出形と完全一致:
partial の骨格（呪文 / 闇 / コスト10 / mana 1、
能力なし）に第381弾の確立形〔シンパシーの static 1件
（dm21-020 / dm21-011 の登録先例と同形）＋ spell の
modify deny summon / deny cast の2 op
（ファイナル・ストップ dm26sd1-e007 と同型、
duration: until_next_own_turn_start）〕を足し、
unsupported を外したもの。abilities は static 1件
ちょうど、spell は2 op ちょうど、keywords は無いまま。
補完あり: partial の text はロック条項だけのため、
提出形では text に行の公式テキスト全文（シンパシー
条項を含む）を入れた（ラウンド403・dm21-011 の
作法）。alias は無い。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無いことを
第381弾で実測済みで、ラウンド416は通常どおり submit
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
from tests.test_vocab_pilot381 import (  # noqa: E402
    DENY_CAST, DENY_SUMMON, FULL_TEXT, SYMPATHY)

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dm21-014"
GAP = "opponent_cannot_summon_or_cast_next_turn"
NAME = "デビル・リンク・タブー"


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
    assert c["types"] == ["spell"] and c["civs"] == ["darkness"]
    assert c["cost"] == 10 and c["mana"] == 1
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    # 登録形は提出形と完全一致: 確立形ちょうど
    assert c["abilities"] == [SYMPATHY]
    assert len(c["abilities"]) == 1
    assert c["spell"] == [DENY_SUMMON, DENY_CAST]
    assert len(c["spell"]) == 2
    assert not c.get("keywords")
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d is not None
    # プロト T1135 と abilities・spell・text が完全一致
    proto = proto_card("T1135")
    assert proto["abilities"] == [SYMPATHY]
    assert proto["spell"] == [DENY_SUMMON, DENY_CAST]
    assert proto["text"] == FULL_TEXT
