"""語彙パイロット第444弾（cards 側）:
attacker_cost_restriction — 対象は dmr05-098
ヨケッピ・チョーナン と dmr06-028 ボルカニック・
ザウルス（pure 2件、multi にも現れない）。

提出形はいずれも partial の骨格（text 公式全文）
に確立形の abilities を足し、unsupported を
外したもの:
- 共通条項「コスト6以下のクリーチャーに攻撃
  されない」= static {affects: self, mod:
  {deny: [{action: be_attacked, other:
  {cost_le: 6}}]}}。deny の辞書形＋other
  フィルタは登録先例 dm01-009（deny
  [{action: be_blocked, other: {power_le: 4000}}]）
  の鏡像で、ドリフト。
- dmr05-098: keywords [speed_attacker] のまま、
  abilities は deny static 1件のみ。**補完
  あり: abilities**。
- dmr06-028: keywords [double_breaker] のまま、
  abilities は power_when static ＋ deny static
  の2件。パワーアタッカーは split の定型所有形
  static {affects: self, mod: {power_when:
  {amount: 2000, when: attacking}}}（登録済み
  186件）で、partial の attack trigger＋modify
  {power: 2000}（end_of_turn）下書きは置き換え
  る。**補完あり: abilities**（置き換え＋追加）。

登録ブロッカーの確認（第375弾の教訓）:
rule_convert.split は dmr05-098 でキーワード
のみ、dmr06-028 でキーワード＋power_when
static を定型所有し、本条項の text は定型化
されず残る＝ツール側ブロッカーなし。

alias は両件とも無し（identity 実測で canon_id
は対象自身、aliases_for = []、rejects に同名の
別行も無い）。
ラウンド478で登録済み（reopen の出力は対象2件
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
from tests.test_vocab_pilot444 import (  # noqa: E402
    ABILITIES_A, ABILITIES_B, NAME_A, NAME_B, TEXT_A, TEXT_B)

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
GAP = "attacker_cost_restriction"
TARGETS = ("dmr05-098", "dmr06-028")

SUBMIT_A = {
    "id": "dmr05-098",
    "name": NAME_A,
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 4,
    "power": 2000,
    "races": ["ファイアー・バード", "ハンター"],
    "mana": 1,
    "keywords": ["speed_attacker"],
    "text": TEXT_A,
    "abilities": ABILITIES_A,
}

SUBMIT_B = {
    "id": "dmr06-028",
    "name": NAME_B,
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 5,
    "power": 4000,
    "races": ["ロック・ビースト"],
    "mana": 1,
    "keywords": ["double_breaker"],
    "text": TEXT_B,
    "abilities": ABILITIES_B,
}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_targets_registered_and_family_cleared():
    rows = _reject_rows()
    mine = {r["id"]: r for r in rows}
    # ラウンド478で登録済み: 対象2行は rejects から解消
    for tid in TARGETS:
        assert tid not in mine
    # ファミリー完全解消（pure 2件のみだった）
    fam = sorted(x["id"] for x in rows if GAP in (x.get("gaps") or []))
    assert fam == []
    # 登録形 == 提出形（source 以外の全フィールド）
    ca = find(CONVERTED, "dmr05-098")
    assert ca is not None
    assert {k: v for k, v in ca.items() if k != "source"} == SUBMIT_A
    assert len(ca["abilities"]) == 1
    assert ca["abilities"][0]["mod"] == {
        "deny": [{"action": "be_attacked", "other": {"cost_le": 6}}]}
    assert ca["keywords"] == ["speed_attacker"]
    assert ca["text"] == TEXT_A
    assert not (ca.get("source") or {}).get("unsupported")
    cb = find(CONVERTED, "dmr06-028")
    assert cb is not None
    assert {k: v for k, v in cb.items() if k != "source"} == SUBMIT_B
    assert len(cb["abilities"]) == 2
    assert cb["abilities"][0]["mod"] == {
        "power_when": {"amount": 2000, "when": "attacking"}}
    assert cb["abilities"][1]["mod"] == {
        "deny": [{"action": "be_attacked", "other": {"cost_le": 6}}]}
    assert cb["keywords"] == ["double_breaker"]
    assert cb["text"] == TEXT_B
    assert not (cb.get("source") or {}).get("unsupported")


def test_alias_and_canon():
    for tid, name in (("dmr05-098", NAME_A), ("dmr06-028", NAME_B)):
        assert canon_id(tid) == tid
        assert aliases_for(name, tid) == []
        # proto には対象 id のカードは無い（T1234 / T1235 は型カード）
        assert find(str(PROTO), tid) is None


def test_submit_forms_parse_and_match_proto():
    for submit, tid_proto, power in ((SUBMIT_A, "T1234", 2000),
                                     (SUBMIT_B, "T1235", 4000)):
        d = parse_card(copy.deepcopy(submit), TABLES)
        assert d.name == submit["name"] and d.power == power
        proto = proto_card(tid_proto)
        for k in ("name", "types", "civs", "cost", "power", "races",
                  "mana", "keywords", "text", "abilities"):
            assert proto[k] == submit[k], (tid_proto, k)


def test_official_row_consistency():
    for prod, submit in (("r05", SUBMIT_A), ("r06", SUBMIT_B)):
        rows = [json.loads(x) for x in
                (ROOT / f"data/cards/raw/by_product/{prod}.jsonl")
                .read_text(encoding="utf-8").splitlines() if x.strip()]
        off = next(r for r in rows if r["id"] == submit["id"])
        assert off["name"] == submit["name"]
        assert off["card_type"] == "クリーチャー"
        assert off["civilization"] == "火"
        assert int(off["cost"]) == submit["cost"]
        assert int(off["power"]) == submit["power"]
        assert off["race"] == "/".join(submit["races"])
        assert int(off["mana"]) == 1
        assert off["text"] == submit["text"]
