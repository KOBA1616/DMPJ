"""語彙パイロット第416弾の対象カード検証（登録形）。

対象は fixed_breaks_plus_one（pure 1件、multi にも
現れない）:
- dmrp07-052 C.W.テラス
ラウンド451で登録済み。登録形は提出形と完全一致:
対象行は round66 由来の素行（partial も reason
フィールドも無し。note は「シールドをさらに１つ
ブレイクする。modify で固定+1のブレイク数増加を
表す語彙がない」）で、提出形は公式データ行
（by_product/rp07.jsonl）から決定的に構築した骨格
（クリーチャー / 自然 / コスト4 / パワー4000 /
種族 ジョーカーズ、mana 1、keywords 無し）に
第416弾の確立形 trigger 2件〔Jチェンジ６
（trigger {event: attack, subject: self} →
may [swap {out: {ref: self}, out_to: mana,
in: {zone: mana, owner: you, filter: {types:
[creature], cost_le: 6, race_has: ジョーカーズ},
count: 1}}]、同セットの登録済み dmrp07-027 と
完全一致）／ CIP（trigger {event: move, to: bz,
subject: self} → choose {other: true, count: 1,
as: pick} → modify {ref: pick, mod: {power:
4000, breaks_add: 1}, duration: end_of_turn}、
登録済み dmr19-047・第159弾の modify 先例）〕を
足したもの。abilities はこの2件ちょうど、keywords
は無いまま。**補完なし**（text は公式全文）。

alias は無し（identity 実測で canon_id は対象自身、
aliases_for = [] のため登録エントリに
source.aliases は付かない）。
fixed_breaks_plus_one は完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い＝
ツール側ブロッカーなし。対象行に reason フィールド
が無いため reopen の出力は0件で、submit が登録
成功時に行を除去した（ラウンド451で実測確認済み）。

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
from tests.test_vocab_pilot416 import FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmrp07-052"
GAP = "fixed_breaks_plus_one"
NAME = "C.W.テラス"

# 提出形: 公式データ行から構築した骨格＋確立形 trigger 2件（補完なし）
SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["nature"],
    "cost": 4,
    "power": 4000,
    "races": ["ジョーカーズ"],
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
    assert len(rows) <= 1915  # 件数は減る一方（スナップショット固定をやめた）
    assert TARGET not in rows            # 登録により対象行は解消
    fam = sorted(i for i, x in rows.items()
                 if GAP in (x.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    assert identity.canon_id(TARGET) == TARGET
    assert identity.aliases_for(NAME, TARGET) == []
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 4 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ジョーカーズ"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は trigger 2件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("keywords")         # keywords は無いまま
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し＝自動付与なし
    d = parse_card(c, TABLES)
    for a in FORM:
        assert a in d.abilities
    assert len(d.abilities) == 2
    # プロト T1184 と abilities・text・骨格が完全一致
    proto = proto_card("T1184")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power", "races", "mana"):
        assert proto[k] == SUBMIT[k]


def test_official_row_matches_skeleton():
    """骨格は公式データ行（by_product/rp07.jsonl）から
    構築したもので、原文と一致することを固定する。"""
    with open(ROOT / "data/cards/raw/by_product/rp07.jsonl",
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
    assert official["civilization"] == "自然"
    assert official["cost"] == "4" and official["power"] == "4000"
    assert official["race"] == "ジョーカーズ"
    assert official["mana"] == "1"
    assert official["text"] == FULL_TEXT
