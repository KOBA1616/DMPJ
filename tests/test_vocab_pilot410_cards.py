"""語彙パイロット第410弾の対象カード検証（登録形）。

対象は force_block（pure 1件、multi にも現れない）:
- dmr09-004 剛鉄突破 アイアンローズ
ラウンド445で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 光 / コスト7 /
パワー6000 / 種族 アウトレイジMAX、mana 1、
keywords [double_breaker]、abilities 無し）に
第410弾の確立形 abilities 2件〔第1条項: static
{affects: {zone: bz, owner: opp, filter: {types:
[creature]}}, mod: {grant: [blocker], require:
[block]}}／第2条項: static {affects: self, mod:
{power: {amount: 2000, count: {zone: bz, owner:
opp, filter: {types: [creature]}}}}}}〕を足し、
unsupported を外したもの。abilities はこの
2件ちょうど、keywords は [double_breaker] のまま。
**補完なし**（partial の text は公式全文と一致）。

alias は無し（identity 実測で canon_id は対象自身、
aliases_for = []）。force_block は本登録で完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (['double_breaker'], 条項テキスト,
[]) を返し、part[2] の定型所有は空。提出形には
FORM の static 2件すべてを含め、登録後の abilities
は2件ちょうど（ラウンド445で実測確認済み）。

第410弾のエンジン修正（combat.py: ブロック宣言で
タップするのは選ばれた1体だけ）は登録と同時に効く。

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
from tests.test_vocab_pilot410 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmr09-004"
GAP = "force_block"
NAME = "剛鉄突破 アイアンローズ"

# 提出形: partial の骨格＋確立形 abilities 2件（補完なし）
SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["light"],
    "cost": 7,
    "power": 6000,
    "races": ["アウトレイジMAX"],
    "mana": 1,
    "keywords": ["double_breaker"],
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
    assert len(rows) == 1921
    assert TARGET not in rows            # 登録により対象行は解消
    fam = sorted(i for i, x in rows.items()
                 if GAP in (x.get("gaps") or []))
    assert fam == []                     # ファミリーは完全解消
    assert identity.canon_id(TARGET) == TARGET
    assert identity.aliases_for(NAME, TARGET) == []
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["light"]
    assert c["cost"] == 7 and c["power"] == 6000 and c["mana"] == 1
    assert c["races"] == ["アウトレイジMAX"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は確立形2件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert c["keywords"] == ["double_breaker"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し（自動付与なし）
    d = parse_card(c, TABLES)
    for a in FORM:
        assert a in d.abilities
    # parse 後の double_breaker 派生 static を除き2件
    assert len(d.abilities) == 3
    assert "double_breaker" in d.keywords
    # プロト T1178 と abilities・text・骨格が完全一致
    proto = proto_card("T1178")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power", "races", "mana"):
        assert proto[k] == SUBMIT[k]
    assert proto["keywords"] == ["double_breaker"]
