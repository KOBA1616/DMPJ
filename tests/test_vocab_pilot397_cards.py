"""語彙パイロット第397弾の対象カード検証（登録形）。

対象は pure な mana_placed_count_this_turn の全1件:
- dmrp06-027 マ・スクメーロ・タンク
ラウンド432で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 自然 / コスト4 /
パワー8000 / 種族 グランセクト、mana 1、keywords
[double_breaker, enters_tapped]、abilities は
static {affects: self, mod: {deny: [untap_at_start]}}
の1件が構築済み）に第397弾の確立形 trigger
〔when {event: move, to: mana, subject: {owner: you},
ord: {kind: mana_put, ge: 2}} → untap {select:
{ref: self}}〕を足し、unsupported を外したもの。
abilities はこの2件ちょうど（static → trigger の
条項順）、keywords は [double_breaker, enters_tapped]
のまま。**補完なし** — partial の text は行の
公式テキスト全文と一致する。alias は無い（identity
実測で canon_id は対象自身、aliases_for = []）。
確立形は登録先例 dm23rp2x-047（「各ターン2枚目の
カードを自分のマナゾーンに置いた時」に ord
{kind: mana_put, eq: 2}）の ord 比較を ge: 2 に
変えた形で、「最初のカードでなければ」＝2枚目以降
すべてを対象にする。ファミリーは完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (['double_breaker'], 条項テキスト,
[]) を返し、定型所有する abilities は空のため
merge_split が二重付与する対象は無い（第397弾で実測）。

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
from tests.test_vocab_pilot397 import FORM, FULL_TEXT, TRIGGER  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmrp06-027"
GAP = "mana_placed_count_this_turn"
NAME = "マ・スクメーロ・タンク"


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
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 4 and c["power"] == 8000 and c["mana"] == 1
    assert c["races"] == ["グランセクト"]
    assert c["keywords"] == ["double_breaker", "enters_tapped"]
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完なし）
    # 登録形は提出形と完全一致: 確立形2能力ちょうど（条項順）
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert TRIGGER in d.abilities
    # プロト T1164 と abilities・text・骨格が完全一致
    proto = proto_card("T1164")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power", "races", "mana"):
        assert proto[k] == c[k]
    assert proto["keywords"] == c["keywords"]
