"""語彙パイロット第396弾の対象カード検証（登録形）。

対象は pure な power_per_civilization の全1件:
- dm25-055 虹色の霊光
ラウンド431で登録済み。登録形は提出形と完全一致:
partial の骨格（呪文 / 自然 / コスト3、mana 1、
keywords・abilities・spell ともに無し）に
第396弾の確立形 spell〔choose {owner: you,
as: pick} → set_var {name: p_up, value:
{mul: [{civ_count: {ref: pick}}, 2000]}} →
modify {select: {ref: pick}, mod: {power:
{amount: {var: p_up}}}, duration: end_of_turn}
→ draw {player: you, count: 1}〕を足し、
unsupported を外したもの。**補完あり: text のみ**
— partial の text は条項の断片（「そのクリーチャー
が持つ文明ひとつにつき+2000」）のため、登録形の
text は行の公式テキスト全文。alias は無い
（identity 実測で canon_id は対象自身、
aliases_for = []）。確立形は第79弾の式 civ_count
を第322弾の set_var で修整の生成前に数えて束縛し、
op_modify の生成時ベイクで mod の amount へ
リテラルに固定する形。当初候補形（mod の count に
{civ_count: {ref: pick}} を書く形は特性計算時の
env_self に解決時の束縛が無く空に倒れ、{ref: self}
形は civ_count の chars_ro 再入で RecursionError
になる）は第396弾で実測して却下した。
ファミリーは完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い
（第396弾で実測）。

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
from tests.test_vocab_pilot396 import EXPANDED, FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dm25-055"
GAP = "power_per_civilization"
NAME = "虹色の霊光"


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
    assert c["types"] == ["spell"]
    assert c["civs"] == ["nature"]
    assert c["cost"] == 3 and c["mana"] == 1
    assert not c.get("keywords")
    assert c["text"] == FULL_TEXT        # 公式テキスト全文（補完あり: text のみ）
    # 登録形は提出形と完全一致: 確立形 spell 4 op ちょうど
    assert c["spell"] == FORM
    assert len(c["spell"]) == 4
    assert not c.get("abilities")
    assert not c.get("aliases")
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert d.spell == EXPANDED           # マクロ展開後の形（＝提出形）
    # プロト T1163 と spell・text・骨格が完全一致
    proto = proto_card("T1163")
    assert proto["spell"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "mana"):
        assert proto[k] == c[k]
