"""語彙パイロット第388弾の対象カード検証（登録形）。

対象は battle_opponent_reference（pure 2件）のうち単一条項の1件:
- dm24rp4-065 カンテ＝ランタン
ラウンド423で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 闇 / コスト2 / パワー1000 /
種族 アビスロイヤル、mana 1、keywords・abilities ともに
無し）に、第75弾の battle_start 両面誘発＋登録先例
dm26rp1-039 の modify 形で [攻撃側 trigger
{battle_start, subject: self} → modify
{ref: event.opponent, power: -3000,
duration: during_attack}, 守備側 trigger
{battle_start, opponent: self} → modify
{ref: event.subject, 同}] の2能力を足し、
unsupported を外したもの。補完あり: partial の text は
条項の断片のため、text には行の公式テキスト全文を
入れた。alias は無い。

もう1件の dmr01-049 は対象外で rejects に残る
（ファミリーは解消しない）: 行に name・partial が無く、
条項も相手スコープのバトル破壊不能で形が異なる。
なお reopen（battle_opponent_reference）の出力は
対象1件ちょうどだった — dmr01-049 の行には reason が
無く、reopen の reason: vocab 条件に該当しないため
外れなかった（第388弾の見込み2件とは異なった）。
差し戻しは不要で、行は gaps・text のみの元の形のまま
残っている。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い（第388弾で実測）。

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
from tests.test_vocab_pilot388 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dm24rp4-065"
OTHER = "dmr01-049"
GAP = "battle_opponent_reference"
NAME = "カンテ＝ランタン"


def _reject_rows():
    rows = {}
    with open(ROOT / "data/cards/raw/rejects.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                rows[r["id"]] = r
    return rows


def test_target_registered_and_family_remains():
    rows = _reject_rows()
    assert TARGET not in rows            # 登録により対象行は解消
    fam = sorted(i for i, x in rows.items()
                 if GAP in (x.get("gaps") or []))
    assert fam == [OTHER]                # もう1件は対象外で残る
    # dmr01-049 は reopen で外れず、元の形（gaps・text のみ、
    # partial 無し）のまま残っている
    assert rows[OTHER]["gaps"] == [GAP]
    assert "partial" not in rows[OTHER]
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["darkness"]
    assert c["cost"] == 2 and c["power"] == 1000 and c["mana"] == 1
    assert c["races"] == ["アビスロイヤル"]
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり）
    # 登録形は提出形と完全一致: 確立形2能力ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 2
    # プロト T1152 と abilities・text が完全一致
    proto = proto_card("T1152")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
