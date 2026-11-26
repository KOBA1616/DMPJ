"""語彙パイロット第437弾（cards 側）: shield_faceup_trigger —
対象はまだ rejects に残る（登録はラウンド471）。

対象は dmd11-006 大焔団 フォルクス（pure 1件、multi にも
現れない）。提出形は partial（骨格〔クリーチャー / 火 /
コスト7 / パワー7000 / 種族 アウトレイジMAX、mana 1〕＋
keywords [speed_attacker, double_breaker]、text は公式
全文）に第437弾の確立形 ability 1件〔trigger
{when: {event: move, from: shield, reason: break,
subject: {owner: you}, face_up: true}, effect:
[destroy {select: {zone: bz, owner: opp, filter:
{types: [creature], power_le: 6000}, count: 1}}]}〕を
足し、unsupported を外したもの。**補完あり: abilities**
（partial に未構築）。シールド離脱の監視は登録済み
dm23rp3-017 等の確立形、表向きの照合は第176弾で
move レコードに載る face_up を when で見る形、
ブレイクの区別は h_break が付ける reason: break。

alias は無し（identity 実測で canon_id は対象自身、
aliases_for = []）。登録ブロッカーの確認（第375弾の
教訓）: rule_convert.split（対象行）は
(['speed_attacker', 'double_breaker'], 残り原文, []) を
返し、定型所有はキーワード2件のみで partial の
keywords と完全一致（欠落なし）、定型所有の ability は
無い。対象行は gaps=[shield_faceup_trigger]・
reason == "vocab" のため、ラウンド471の reopen の
出力は対象1件ちょうどのはず。

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
from tests.test_vocab_pilot437 import FORM, FULL_TEXT  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
TARGET = "dmd11-006"
GAP = "shield_faceup_trigger"
NAME = "大焔団 フォルクス"

SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 7,
    "power": 7000,
    "races": ["アウトレイジMAX"],
    "mana": 1,
    "text": FULL_TEXT,
    "keywords": ["speed_attacker", "double_breaker"],
    "abilities": FORM,
}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_still_rejected_and_family_shape():
    rows = _reject_rows()
    mine = {r["id"]: r for r in rows}
    assert TARGET in mine                # 対象行はまだ残る
    row = mine[TARGET]
    assert row["gaps"] == [GAP]
    assert row["reason"] == "vocab"
    # ファミリーはこの1件のみ（pure / multi 問わず）
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == [TARGET]
    partial = row["partial"]
    assert partial["text"] == FULL_TEXT  # partial の時点で公式全文
    assert partial["keywords"] == ["speed_attacker", "double_breaker"]
    assert "abilities" not in partial    # ability は未構築（補完対象）
    needs = [u["need"] for u in
             (partial.get("source") or {}).get("unsupported") or []]
    assert needs == [GAP]
    # 未登録の確認
    assert find(CONVERTED, TARGET) is None
    assert find(str(PROTO), TARGET) is None
    # 正本は対象自身・alias 無し
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []
    # 判断待ちの stale 行には触っていない
    assert mine["dm02-046"]["gaps"] == [
        "destroy_self_after_attacking_player"]


def test_submit_form_parses_and_matches_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    assert d.types == ["creature"]
    assert d.cost == 7 and d.power == 7000
    proto = proto_card("T1227")
    for k in ("name", "types", "civs", "cost", "power",
              "races", "mana", "text", "abilities", "keywords"):
        assert proto[k] == SUBMIT[k], k


def test_official_row_consistency():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/d11.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    off = next(r for r in rows if r["id"] == TARGET)
    assert off["name"] == NAME
    assert off["text"] == FULL_TEXT
    assert int(off["cost"]) == 7 and int(off["power"]) == 7000
    assert off["race"] == "アウトレイジMAX"
