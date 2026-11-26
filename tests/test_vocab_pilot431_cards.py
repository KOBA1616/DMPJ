"""語彙パイロット第431弾（cards 側）:
after_battle_trigger — ラウンド466で登録済み。

対象は dmrp14-072 血誓怪人ザミザニン（pure 2件の
うちの1件。もう1件の dmrp09-074 は勝者参照が要る
ため残置し、ファミリーは解消しない）。対象行は
partial も reason フィールドも無い素行（第393・
415・416弾と同型）で、提出形は公式データ行
（by_product/rp14.jsonl）から決定的に構築した骨格
（クリーチャー / 闇 / コスト2 / パワー5000 / 種族
デビルマスク、mana 1、keywords [blocker,
cannot_attack]）に第431弾の確立形 ability 1件
〔trigger {when: {event: battle_end, subject: self},
effect: [destroy {select: {ref: self}}]}〕（第211弾の
battle_end 形。登録済み dmpcd03-b11 が同一の条項
構造をこの形で保持する）を足したもの。**補完なし**
（text は公式全文）。登録形は提出形と完全一致
〔source 以外の全フィールドを照合〕、abilities は
trigger 1件ちょうど、keywords [blocker,
cannot_attack] のまま。

alias は無し（identity 実測で canon_id は対象自身、
aliases_for = []）。登録ブロッカーの確認（第375弾の
教訓）: rule_convert.split（対象行）は
(['blocker', 'cannot_attack'], 条項テキスト, []) を
返し、定型所有はキーワード2件のみで part[2] の
能力所有は空＝ツール側ブロッカーなし。対象行に
reason フィールドが無いため、ラウンド466の reopen の
出力は0件で、submit が登録成功時に行を除去した
（ラウンド428・450・451で実測済み）。

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
from tests.test_vocab_pilot431 import FORM, FULL_TEXT, KEYWORDS  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
TARGET = "dmrp14-072"
OTHER = "dmrp09-074"
GAP = "after_battle_trigger"
NAME = "血誓怪人ザミザニン"

# 提出形: 公式データ行から構築した骨格＋確立形 trigger 1件（補完なし）
SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["darkness"],
    "cost": 2,
    "power": 5000,
    "races": ["デビルマスク"],
    "mana": 1,
    "text": FULL_TEXT,
    "keywords": list(KEYWORDS),
    "abilities": FORM,
}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_registered_and_family_not_cleared():
    rows = _reject_rows()
    mine = {r["id"]: r for r in rows}
    assert TARGET not in mine            # 対象行は登録で解消
    # ファミリーは pure 2件のうち dmrp09-074 が残る（解消しない）
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == [OTHER]
    # もう1件は勝者参照が要るため残置（素行のまま）
    assert mine[OTHER]["gaps"] == [GAP]
    assert "partial" not in mine[OTHER]
    assert "reason" not in mine[OTHER]
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT                 # 登録形 == 提出形
    assert len(c["abilities"]) == 1      # abilities は trigger 1件ちょうど
    assert c["abilities"][0]["kind"] == "trigger"
    assert c["abilities"][0]["when"] == {"event": "battle_end",
                                         "subject": "self"}
    assert c["keywords"] == KEYWORDS     # [blocker, cannot_attack] のまま
    assert c["text"] == FULL_TEXT        # 公式全文
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し
    # 正本は対象自身・alias 無し
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []
    # 判断待ちの stale 行には触っていない
    assert mine["dm02-046"]["gaps"] == [
        "destroy_self_after_attacking_player"]


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.types == ["creature"]
    assert d.cost == 2 and d.power == 5000
    proto = proto_card("T1212")
    for k in ("name", "types", "civs", "cost", "power",
              "races", "mana", "text", "keywords", "abilities"):
        assert proto[k] == SUBMIT[k], k
    assert len(proto["abilities"]) == 1


def test_official_row_matches_skeleton_and_text():
    off = None
    for line in (ROOT / "data/cards/raw/by_product/rp14.jsonl") \
            .read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("id") == TARGET:
            off = r
    assert off is not None
    assert off["name"] == NAME
    assert off["text"] == FULL_TEXT
    assert int(off["cost"]) == 2
    assert int(off["power"]) == 5000
    assert off["race"] == "デビルマスク"
    assert off["civilization"] == "闇"
    assert off["card_type"] == "クリーチャー"
    assert int(off["mana"]) == 1
