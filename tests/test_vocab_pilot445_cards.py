"""語彙パイロット第445弾（cards 側）:
fury_charge — 対象は dmx12b-015 Tatsurion
（pure 1件、multi にも現れない）。

提出形は partial の骨格（text 公式全文、keywords
[double_breaker]）に確立形の abilities を足し、
unsupported を外したもの: 条項「フュリー・
チャージ」はマッハファイターの確立形（第58弾・
keyword_patterns.yaml の mach_fighter パターン、
登録済み195件）の鏡像 = trigger {when: {event:
move, to: bz, subject: self}, effect: [modify
{select: {ref: self}, mod: {allow: [{action:
attack_creature, other: {tapped: true}}]},
duration: end_of_turn}]}（マッハファイターは
other: {tapped: false} でアンタップ対象を広げる。
フュリー・チャージはタップ対象のみ）。成立には
combat._attack_options の最小エンジン修正が
要る（第445弾本体の docstring 参照）。**補完
あり: abilities**（trigger 1件のみ。text・
keywords の補完なし）。

登録ブロッカーの確認（第375弾の教訓）:
rule_convert.split は keywords [double_breaker]
のみ定型所有し、フュリー・チャージ条項の text は
定型化されず残る＝ツール側ブロッカーなし
（提出形の keywords は partial のまま使う）。

alias は無し（identity 実測で canon_id は対象
自身、aliases_for = []、rejects に同名の別行も
無い）。
ラウンド479で登録済み（reopen の出力は対象1件
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
from tests.test_vocab_pilot445 import ABILITIES, NAME, TEXT  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
GAP = "fury_charge"
TARGET = "dmx12b-015"

SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["fire"],
    "cost": 6,
    "power": 6000,
    "races": ["アーマード・ドラゴン", "ビーストフォーク"],
    "mana": 1,
    "keywords": ["double_breaker"],
    "text": TEXT,
    "abilities": ABILITIES,
}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_registered_and_family_cleared():
    rows = _reject_rows()
    mine = {r["id"]: r for r in rows}
    # ラウンド479で登録済み: 対象行は rejects から解消
    assert TARGET not in mine
    # ファミリー完全解消（pure 1件のみだった）
    fam = sorted(x["id"] for x in rows if GAP in (x.get("gaps") or []))
    assert fam == []
    # 登録形 == 提出形（source 以外の全フィールド）
    c = find(CONVERTED, TARGET)
    assert c is not None
    assert {k: v for k, v in c.items() if k != "source"} == SUBMIT
    assert len(c["abilities"]) == 1
    assert c["abilities"][0]["kind"] == "trigger"
    assert c["keywords"] == ["double_breaker"]
    assert c["text"] == TEXT
    assert not (c.get("source") or {}).get("unsupported")


def test_alias_and_canon():
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []
    # proto には対象 id のカードは無い（T1236 は型カード）
    assert find(str(PROTO), TARGET) is None


def test_submit_form_parses_and_matches_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    assert d.name == NAME and d.power == 6000
    proto = proto_card("T1236")
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "keywords", "text", "abilities"):
        assert proto[k] == SUBMIT[k], k


def test_official_row_consistency():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/x12.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    off = next(r for r in rows if r["id"] == TARGET)
    assert off["name"] == NAME
    assert off["card_type"] == "クリーチャー"
    assert off["civilization"] == "火"
    assert int(off["cost"]) == 6
    assert int(off["power"]) == 6000
    assert off["race"] == "アーマード・ドラゴン/ビーストフォーク"
    assert int(off["mana"]) == 1
    assert off["text"] == TEXT
