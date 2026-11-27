"""語彙パイロット第442弾（cards 側）:
destroy_attack_target_without_battle — 対象は
dm20-028 エンドブリンガー・ドラグーン（pure 1件、
multi にも現れない）。

提出形は partial の骨格〔クリーチャー / 闇 /
コスト3 / パワー2000 / 種族 ティラノ・ドレイク、
mana 1、text 公式全文（partial では改行が空白に
潰れており、提出形は公式の改行形に復元する）、
keywords 無し〕に abilities
2件〔(1) trigger {when: {event: attack, subject:
self, target: creature}, effect: [destroy {select:
{ref: event.target}}]}、(2) trigger {when: {event:
attack, target: self}, effect: [destroy {select:
{ref: self}}]}〕を足し、unsupported を外したもの。
**補完あり: abilities**（trigger 2件とも。
unsupported の text は第1条項だけだが、第2条項も
同一機構で text から構築）**＋text の改行復元**
（keywords の補完は無い）。

第1条項の subject: self ＋ event.target 参照は
登録済み dmd15-009 の確立形、target: "creature" は
defs の検証許可値（_match_when 実装済み・
schema.py は無制限）で既存部品の初使用。第2条項の
when {event: attack, target: self} は登録済み
17件の確立形。「(バトルは行われない)」は攻撃宣言時
誘発の解決後に combat.h_attack の既存チェック
（505.6a 相当）が攻撃を終わらせるため専用 op は
不要で、cancel_attack は併記しない（破壊が通ら
なければバトルが行われるのが公式どおり）。
登録ブロッカーの確認（第375弾の教訓）:
rule_convert.split（対象行）は None（キーワードが
無い行は定型所有の対象外）。

alias は無し（identity 実測で canon_id は対象自身、
aliases_for = []、rejects に独自行なし）。
ラウンド476で登録済み（reopen の出力は対象1件
ちょうど、登録形は提出形と完全一致）。本ファイルは
登録形に書き換え済み。

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
from tests.test_vocab_pilot442 import ABILITIES, FULL_TEXT, NAME  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
TARGET = "dm20-028"
GAP = "destroy_attack_target_without_battle"

SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["darkness"],
    "cost": 3,
    "power": 2000,
    "races": ["ティラノ・ドレイク"],
    "mana": 1,
    "text": FULL_TEXT,
    "abilities": ABILITIES,
}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_registered_and_family_cleared():
    rows = _reject_rows()
    mine = {r["id"]: r for r in rows}
    # ラウンド476で登録済み: 対象行は rejects から解消
    assert TARGET not in mine
    # ファミリー完全解消（pure 1件のみだった）
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == []
    # 登録形 == 提出形（source 以外の全フィールド）
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT
    assert len(c["abilities"]) == 2
    assert all(a["kind"] == "trigger" for a in c["abilities"])
    assert "keywords" not in c
    assert c["text"] == FULL_TEXT
    src = c.get("source") or {}
    assert not src.get("unsupported")


def test_not_in_proto_and_no_alias():
    # proto には対象 id のカードは無い（T1232 は型カード）
    assert find(str(PROTO), TARGET) is None
    assert canon_id(TARGET) == TARGET
    assert aliases_for(NAME, TARGET) == []


def test_submit_form_parses_and_matches_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    assert d.name == NAME and d.power == 2000
    assert len(d.abilities) == 2
    proto = proto_card("T1232")
    for k in ("name", "types", "civs", "cost", "power", "races",
              "mana", "text", "abilities"):
        assert proto[k] == SUBMIT[k], k


def test_official_row_consistency():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/20.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    off = next(r for r in rows if r["id"] == TARGET)
    assert off["name"] == NAME
    assert off["card_type"] == "クリーチャー"
    assert off["civilization"] == "闇"
    assert int(off["cost"]) == 3
    assert int(off["power"]) == 2000
    assert off["race"] == "ティラノ・ドレイク"
    assert int(off["mana"]) == 1
    assert off["text"] == FULL_TEXT
