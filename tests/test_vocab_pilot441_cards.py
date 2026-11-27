"""語彙パイロット第441弾（cards 側）: count_face_up_shields —
対象は dm23bd7-019 煌メク聖晶 弩楼 / ビスティック・マース
（pure 1件、multi にも現れない）。

提出形はツインパクト登録形（dm23bd7-049 /
dm23bd7-050 / dm24ex1-036 の構造）: faces
[クリーチャー面〔光 / コスト9 / パワー11500 /
種族 メタリカ/サバキスト、keywords [blocker,
double_breaker]、abilities 1件〔trigger {when:
{event: move, to: bz, subject: self}, effect:
[repeat {times: {count: {bundle_of: {zone:
shield, owner: you}, filter: {face_up: true}}},
body: [may [draw {count: 1}]]}]}〕、呪文面
〔光 / コスト4、keywords [s_trigger]、spell
[if {cond: {cmp: [count mana opp > count mana
you]}, then: [mana_put {from_top: 2}]}]〕]、
mana 1、text は両面の公式全文を登録先例の
結合形式にしたもの。**補完あり: text（両面の
公式全文）＋keywords＋abilities＋呪文面
まるごと**（partial はクリーチャー面の骨格のみで
text は条項だけの断片、keywords 未記載、
abilities 未構築）。

表向きシールドのカード数は第169弾の確立形
（proto T338）、「〜につき1枚引いてもよい」は
登録済み dm21-024 の repeat + may、呪文面は
登録済み dm23bd7-026 と文面が完全一致でその
登録形そのもの。登録ブロッカーの確認（第375弾の
教訓）: rule_convert.split は二面カード行には
None を返す仕様で定型所有の対象外。

alias は dmbd07-b-002（identity 実測で canon_id
は対象自身、aliases_for = [dmbd07-b-002]、
rejects に独自行なし）。ラウンド475で登録済み
（reopen の出力は対象1件ちょうど、登録形は提出形と
完全一致、alias は source.aliases に validate が
自動付与）。本ファイルは登録形に書き換え済み。

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
from tests.test_vocab_pilot441 import FACES, FULL_TEXT, NAME  # noqa: E402

CONVERTED = cardstore.converted_path(DATA)

ROOT = Path(__file__).resolve().parents[1]
TABLES = load_tables()
TARGET = "dm23bd7-019"
GAP = "count_face_up_shields"
ALIAS = "dmbd07-b-002"

SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "faces": FACES,
    "mana": 1,
    "text": FULL_TEXT,
}


def _reject_rows():
    return [json.loads(x) for x in
            (ROOT / "data/cards/raw/rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]


def test_target_registered_and_family_cleared():
    rows = _reject_rows()
    mine = {r["id"]: r for r in rows}
    # ラウンド475で登録済み: 対象行は rejects から解消
    assert TARGET not in mine
    # ファミリー完全解消（pure 1件のみだった）
    fam = sorted(r["id"] for r in rows if GAP in (r.get("gaps") or []))
    assert fam == []
    # 登録形 == 提出形（source 以外の全フィールド）
    c = find(CONVERTED, TARGET)
    assert c is not None
    reg = {k: v for k, v in c.items() if k != "source"}
    assert reg == SUBMIT
    assert len(c["faces"]) == 2
    assert len(c["faces"][0]["abilities"]) == 1
    assert c["faces"][0]["keywords"] == ["blocker", "double_breaker"]
    assert c["faces"][1]["keywords"] == ["s_trigger"]
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == [ALIAS]
    # proto には対象 id のカードは無い（T1231 は型カード）
    assert find(str(PROTO), TARGET) is None
    # alias は独自行なし・正本は対象自身
    assert ALIAS not in mine
    assert canon_id(TARGET) == TARGET
    assert canon_id(ALIAS) == TARGET
    assert aliases_for(NAME, TARGET) == [ALIAS]


def test_submit_form_parses_and_matches_proto():
    d = parse_card(copy.deepcopy(SUBMIT), TABLES)
    f0, f1 = d.faces
    assert f0.name == "煌メク聖晶 弩楼" and f0.power == 11500
    assert f1.name == "ビスティック・マース" and f1.cost == 4
    proto = proto_card("T1231")
    for k in ("name", "mana", "text", "faces"):
        assert proto[k] == SUBMIT[k], k


def test_official_row_consistency():
    rows = [json.loads(x) for x in
            (ROOT / "data/cards/raw/by_product/23bd7.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    off = next(r for r in rows if r["id"] == TARGET)
    assert off["name"] == NAME
    faces = {f["name"]: f for f in off["faces"]}
    assert faces["煌メク聖晶 弩楼"]["text"] in FULL_TEXT
    assert faces["ビスティック・マース"]["text"] in FULL_TEXT
    assert int(faces["煌メク聖晶 弩楼"]["cost"]) == 9
    assert int(faces["煌メク聖晶 弩楼"]["power"]) == 11500
    assert faces["煌メク聖晶 弩楼"]["race"] == "メタリカ/サバキスト"
    assert int(faces["ビスティック・マース"]["cost"]) == 4
