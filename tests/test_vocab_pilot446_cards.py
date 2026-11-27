"""語彙パイロット第446弾（cards 側）:
blocker_cost_restriction — 対象は dmr05-105
ヌケッピ・サンナン（pure 1件、multi にも
現れない）。

提出形は partial の骨格（text 公式全文、
keywords [hunting]）に確立形の abilities を
足し、unsupported を外したもの:
条項「このクリーチャーは、コスト６以下の
クリーチャーにブロックされない」= static
{affects: self, mod: {deny: [{action:
be_blocked, other: {cost_le: 6}}]}}。
deny の辞書形 {action: be_blocked, other:
{power_le: 4000}} は登録済み dm01-009 の
登録形そのもので、other の cost_le は
第444弾の登録形（be_attacked 側）で実測済み
＝ドリフト。**補完あり: abilities**
（deny static 1件のみ）。

登録ブロッカーの確認（第375弾の教訓）:
rule_convert.split はキーワード hunting のみ
定型所有し、本条項の text は定型化されず
残る＝ツール側ブロッカーなし。

alias は無し（identity 実測で canon_id は
対象自身、aliases_for = []、rejects に同名の
独自行も無い）。
ラウンド480で登録済み（reopen の出力は対象1件
ちょうど、登録形は提出形と完全一致〔source
以外の全フィールド〕）。本ファイルは登録形に
書き換え済み。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import copy
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from dmsim.cards.identity import aliases_for, canon_id  # noqa: E402
from tests._conv_cache import PROTO, find, proto_card  # noqa: E402
from tests.test_vocab_pilot446 import FORM, NAME, TEXT  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
GAP = "blocker_cost_restriction"
TARGET = "dmr05-105"

SUBMIT = {"id": TARGET, **FORM}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_registered_and_family_cleared():
    rows = _reject_rows()
    mine = {r["id"]: r for r in rows}
    # ラウンド480で登録済み: 対象行は rejects から解消
    assert TARGET not in mine
    # ファミリー完全解消（pure 1件のみだった）
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == []
    # 登録形 == 提出形（source 以外の全フィールド）
    c = find(CONVERTED, TARGET)
    assert c is not None
    assert {k: v for k, v in c.items() if k != "source"} == SUBMIT
    assert len(c["abilities"]) == 1
    assert c["abilities"][0]["kind"] == "static"
    assert c["keywords"] == ["hunting"]
    assert c["text"] == TEXT
    assert not (c.get("source") or {}).get("unsupported")


def test_alias_and_canon():
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []
    # proto には対象 id のカードは無い（T1237 は型カード）
    assert find(str(PROTO), TARGET) is None


def test_submit_form_parse_and_match_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    assert d.name == NAME and d.power == 2000
    proto = proto_card("T1237")
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "keywords", "text", "abilities"):
        assert proto[k] == SUBMIT[k], k


def test_official_row_consistency():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/r05.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    off = next(r for r in rows if r["id"] == TARGET)
    assert off["name"] == NAME
    assert off["card_type"] == "クリーチャー"
    assert off["civilization"] == "自然"
    assert int(off["cost"]) == 4
    assert int(off["power"]) == 2000
    assert off["race"] == "ファイアー・バード/ハンター"
    assert int(off["mana"]) == 1
    assert off["text"] == TEXT
