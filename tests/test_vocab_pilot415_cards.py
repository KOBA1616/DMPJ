"""語彙パイロット第415弾の対象カード検証（登録形）。

対象は battle_indestructible（pure 1件、multi にも
現れない）:
- dmd27-012 燃えるメラッチ
ラウンド450で登録済み。登録形は提出形と完全一致:
対象行は partial の無い素行（reason フィールドも
無し）で、提出形は公式データ行（by_product/d27.jsonl）
から決定的に構築した骨格（クリーチャー / 火 /
コスト4 / パワー4000 / 種族 ファイアー・バード炎 /
革命軍、mana 1、keywords 無し）に第415弾の確立形
static 2件〔コスト軽減 {affects: {owner: you,
zone: hand, filter: {types: [evolution],
civs: [fire]}}, mod: {cost: -2, cost_min: 1}}
（登録済み dm17-022 の形＋文明フィルタ。下限1は
dm24ex1-087 / dm24bd2-016 の同文面先例と一致）／
battle_indestructible {affects: self, mod:
{battle_indestructible: true}}（第59弾の素形、
登録済み dm25rp3-055 / dmr21-077 と同一文面）〕を
足したもの。abilities はこの2件ちょうど、keywords
は無いまま。**補完なし**（text は公式全文）。

alias は dmr17-082 / promoy14-010 / promoy14-019
の3件（いずれも同名 燃えるメラッチ）で rejects に
独自行は無し。identity 実測で canon_id は対象自身、
aliases_for = 3件（alias 側の canon も dmd27-012）。
登録エントリの source.aliases には validate が
自動付与した3件が入る。
battle_indestructible は完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い＝
ツール側ブロッカーなし。対象行に reason フィールド
が無いため reopen の出力は0件で、submit が登録
成功時に行を除去した（ラウンド450で実測確認済み）。

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
from tests.test_vocab_pilot415 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmd27-012"
ALIASES = ["dmr17-082", "promoy14-010", "promoy14-019"]
GAP = "battle_indestructible"
NAME = "燃えるメラッチ"

# 提出形: 公式データ行から構築した骨格＋確立形 static 2件（補完なし）
SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 4,
    "power": 4000,
    "races": ["ファイアー・バード炎", "革命軍"],
    "mana": 1,
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
    assert len(rows) <= 1916  # 件数は減る一方（スナップショット固定をやめた）
    assert TARGET not in rows            # 登録により対象行は解消
    fam = sorted(i for i, x in rows.items()
                 if GAP in (x.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    for a in ALIASES:
        assert a not in rows              # alias に独自行なし
        assert identity.canon_id(a) == TARGET
    assert identity.canon_id(TARGET) == TARGET
    assert identity.aliases_for(NAME, TARGET) == ALIASES
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["fire"]
    assert c["cost"] == 4 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ファイアー・バード炎", "革命軍"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は static 2件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("keywords")         # keywords は無いまま
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ALIASES  # validate の自動付与
    d = parse_card(c, TABLES)
    for a in FORM:
        assert a in d.abilities
    assert len(d.abilities) == 2
    # プロト T1183 と abilities・text・骨格が完全一致
    proto = proto_card("T1183")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power", "races", "mana"):
        assert proto[k] == SUBMIT[k]


def test_official_row_matches_skeleton():
    """骨格は公式データ行（by_product/d27.jsonl）から
    構築したもので、原文と一致することを固定する。"""
    with open(ROOT / "data/cards/raw/by_product/d27.jsonl",
              encoding="utf-8") as f:
        official = None
        for line in f:
            if line.strip():
                r = json.loads(line)
                if r["id"] == TARGET:
                    official = r
                    break
    assert official is not None
    assert official["name"] == NAME
    assert official["card_type"] == "クリーチャー"
    assert official["civilization"] == "火"
    assert official["cost"] == "4" and official["power"] == "4000"
    assert official["race"] == "ファイアー・バード炎/革命軍"
    assert official["mana"] == "1"
    assert official["text"] == FULL_TEXT
