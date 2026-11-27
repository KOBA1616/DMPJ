"""語彙パイロット第448弾（cards 側）:
s_trigger_suppression — 対象は dm28-025
ヤミノリミット（pure 2件のうち表現可能な側。
dm27-051 は発生源紐づけの別機構のため残置）。

提出形は partial の骨格（名称・文明・コスト4・
パワー4000・種族・マナ1）に公式全文の text と
確立形の abilities を足し、unsupported を
外したもの:
- static {affects: {zone: shield, owner: opp},
  if: {cmp: [{count: {zone: shield, owner: opp}},
  ">=", 4]}, mod: {deny: [s_trigger]}}
  （第374弾の deny 形＋登録済み dmr19-077 の
  count 条件の組み合わせ＝ドリフト）
＝第435弾の形そのもの。113.6a 専用ステージが
待機状態シールドの数え分けを実装し、復活条件
を満たしたため本弾で再検証する。proto は同
ステージ追加の T1239 を流用（新規追加なし）。

**補完あり: text（公式全文。partial の text は
条件部を落とした断片）＋abilities（static 1件）**。

alias は無し（identity 実測で canon_id は対象
自身、aliases_for = []、rejects に独自行も無い）。
ラウンド482で登録済み（reopen の出力は2件で、
ファミリーの残り1件 dm27-051 は元行をそのまま
差し戻し、登録形は提出形と完全一致〔source
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
from tests.test_vocab_pilot448 import FORM, NAME, TEXT  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
GAP = "s_trigger_suppression"
TARGET = "dm28-025"
OTHER = "dm27-051"

SUBMIT = {"id": TARGET, **FORM}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_registered_and_family_not_cleared():
    rows = _reject_rows()
    mine = {r["id"]: r for r in rows}
    # ラウンド482で登録済み: 対象行は rejects から解消
    assert TARGET not in mine
    # ファミリーは解消しない（dm27-051 は別機構のため残置）
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == [OTHER]
    assert OTHER in mine
    row = mine[OTHER]
    assert row["gaps"] == [GAP]
    assert row.get("reason") == "vocab"
    assert row["partial"]["text"] == "相手は、そのシールドの「S・トリガー」を使えない"
    # 登録形 == 提出形（source 以外の全フィールド）
    c = find(CONVERTED, TARGET)
    assert c is not None
    assert {k: v for k, v in c.items() if k != "source"} == SUBMIT
    assert len(c["abilities"]) == 1
    assert c["abilities"][0]["kind"] == "static"
    assert not c.get("keywords")          # keywords は付いていない
    assert c["text"] == TEXT              # text は公式全文
    assert not (c.get("source") or {}).get("unsupported")
    assert not (c.get("source") or {}).get("aliases")


def test_alias_and_canon():
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []
    # proto には対象 id のカードは無い（T1239 は型カード）
    assert find(str(PROTO), TARGET) is None


def test_submit_form_parse_and_match_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    assert d.name == NAME and d.power == 4000
    proto = proto_card("T1239")
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "text", "abilities"):
        assert proto[k] == SUBMIT[k], k


def test_official_row_consistency():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/28.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    off = next(r for r in rows if r["id"] == TARGET)
    assert off["name"] == NAME
    assert off["card_type"] == "クリーチャー"
    assert off["civilization"] == "闇"
    assert int(off["cost"]) == 4
    assert int(off["power"]) == 4000
    assert off["race"] == "ダーク・モンスター"
    assert int(off["mana"]) == 1
    assert off["text"] == TEXT
