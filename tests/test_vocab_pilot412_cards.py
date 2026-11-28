"""語彙パイロット第412弾の対象カード検証（登録形）。

対象は turn_count_free（pure 1件、multi にも現れない）:
- dmex19-028 超宮兵 マノミ
ラウンド447で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 水 / コスト5 /
パワー4000 / 種族 ムートピア、mana 1、keywords
無し、abilities は第2条項の CIP 誘発が構築済み）に
第412弾の確立形 free_if {cmp: [{turn_count:
{kind: cast, owner: you}}, ">=", 3]}（カード
フィールド。登録済み dmrp06-038 / dmpcd02-b18 と
同形で閾値のみ違い）を足し、unsupported を
外したもの。abilities は CIP 誘発1件ちょうど、
keywords は無いまま、free_if は保持。
**補完なし**（partial の text は行の公式テキスト
全文と一致）。

alias は dmrp06-016 の1件で rejects に独自行は
無く、登録エントリの source.aliases に validate
が自動付与した。identity 実測で canon_id は
対象自身（alias 側の canon も dmex19-028）、
aliases_for = [dmrp06-016]。turn_count_free は
完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は ([], 第1条項の条項テキスト,
[CIP 誘発]) を返し、part[2] の定型所有は CIP 誘発
1件のみで partial の abilities と完全一致する
（G・ゼロはカードフィールド free_if のため定型
所有の対象外。convert は None）。ラウンド447の
登録で dedupe が成立し、登録後の abilities は
1件ちょうど・free_if の保持を実測確認済み。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore, identity  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import find, proto_card  # noqa: E402
from tests.test_vocab_pilot412 import CIP, FORM, FREE_IF, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmex19-028"
ALIAS = "dmrp06-016"
GAP = "turn_count_free"
NAME = "超宮兵 マノミ"

# 提出形: partial の骨格＋確立形 free_if（補完なし）
SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["water"],
    "cost": 5,
    "power": 4000,
    "races": ["ムートピア"],
    "mana": 1,
    "text": FULL_TEXT,
    "free_if": FREE_IF,
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
    assert len(rows) <= 1919  # 件数は減る一方（スナップショット固定をやめた）
    assert TARGET not in rows            # 登録により対象行は解消
    fam = sorted(i for i, x in rows.items()
                 if GAP in (x.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert ALIAS not in rows             # alias に独自行なし
    assert identity.canon_id(TARGET) == TARGET
    assert identity.canon_id(ALIAS) == TARGET
    assert identity.aliases_for(NAME, TARGET) == [ALIAS]
    assert find(CONVERTED, TARGET) is not None
    assert find(CONVERTED, ALIAS) is None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["water"]
    assert c["cost"] == 5 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ムートピア"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: free_if が保持され、
    # abilities は CIP 誘発1件ちょうど
    assert c["free_if"] == FREE_IF
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert c["abilities"] == [CIP]
    assert not c.get("keywords")          # text 由来キーワードは union されない
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == [ALIAS]  # validate の自動付与
    d = parse_card(c, TABLES)
    assert d.free_if == FREE_IF
    assert d.abilities == FORM
    assert not d.keywords
    # プロト T1180 と free_if・abilities・text・骨格が完全一致
    proto = proto_card("T1180")
    assert proto["free_if"] == FREE_IF
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power", "races", "mana"):
        assert proto[k] == SUBMIT[k]
    assert not proto.get("keywords")
