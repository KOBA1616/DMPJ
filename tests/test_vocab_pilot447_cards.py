"""語彙パイロット第447弾（cards 側）:
attack_target_power_filter — 対象は dmr15-030
勇気伝承 ゲット Jr.（pure 1件、multi にも
現れない）。

提出形は partial の骨格（名称・文明・コスト2・
パワー2000・種族・マナ1）に公式全文の text と
確立形の abilities を足し、unsupported を
外したもの:
- マナ武装 3 = static {affects: self,
  if: {cmp: [{count: {zone: mana, owner: you,
  filter: {civs: [fire]}}}, ">=", 3]},
  mod: {deny: [{action: be_attacked,
  other: {cost_le: 4}}]}}
  （deny は第444弾の登録形、マナ武装条件は
  登録済みマナ武装カードの確立形）
- マナ武装 5 = static {affects: self,
  if: {cmp: [同 count, ">=", 5]},
  mod: {power_when: {amount: 4000,
  when: attacking}, grant: [double_breaker]}}
  （dm26rp2-028 の {power, grant} 単一 static
  の先例）
＝ドリフト。**補完あり: text（公式全文。
partial の text は第1条項の断片のみ）＋
abilities（static 2件とも）**。

登録ブロッカーの確認（第375弾の教訓）:
rule_convert.split は対象行に None を返す
（キーワード無し行は定型所有の対象外、
第442弾と同型）＝ツール側ブロッカーなし。

alias は dmr15-030d / promoy13-066
（いずれも canon は対象自身、identity
実測済み）。
ラウンド481で登録済み（reopen の出力は対象1件
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
from tests.test_vocab_pilot447 import FORM, NAME, TEXT  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
GAP = "attack_target_power_filter"
TARGET = "dmr15-030"
ALIASES = ["dmr15-030d", "promoy13-066"]

SUBMIT = {"id": TARGET, **FORM}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_registered_and_family_cleared():
    rows = _reject_rows()
    mine = {r["id"]: r for r in rows}
    # ラウンド481で登録済み: 対象行は rejects から解消
    assert TARGET not in mine
    # ファミリー完全解消（pure 1件のみだった）
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == []
    # 登録形 == 提出形（source 以外の全フィールド）
    c = find(CONVERTED, TARGET)
    assert c is not None
    assert {k: v for k, v in c.items() if k != "source"} == SUBMIT
    assert len(c["abilities"]) == 2
    assert all(a["kind"] == "static" for a in c["abilities"])
    assert not c.get("keywords")          # keywords は付いていない
    assert c["text"] == TEXT              # text は公式全文
    assert not (c.get("source") or {}).get("unsupported")
    assert c["source"]["aliases"] == ALIASES


def test_alias_and_canon():
    assert canon_id(TARGET) == TARGET
    for a in ALIASES:
        assert canon_id(a) == TARGET
    assert aliases_for(NAME, TARGET) == ALIASES
    # proto には対象 id のカードは無い（T1238 は型カード）
    assert find(str(PROTO), TARGET) is None


def test_submit_form_parse_and_match_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    assert d.name == NAME and d.power == 2000
    proto = proto_card("T1238")
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "text", "abilities"):
        assert proto[k] == SUBMIT[k], k


def test_official_row_consistency():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/r15.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    off = next(r for r in rows if r["id"] == TARGET)
    assert off["name"] == NAME
    assert off["card_type"] == "クリーチャー"
    assert off["civilization"] == "火"
    assert int(off["cost"]) == 2
    assert int(off["power"]) == 2000
    assert off["race"] == "ヒューマノイド爆"
    assert int(off["mana"]) == 1
    assert off["text"] == TEXT
