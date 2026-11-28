"""語彙パイロット第411弾の対象カード検証（登録形）。

対象は madness（pure 2件、multi にも現れない）のうち1件:
- dmx18-047 有毒類罠顎目 ドクゲーター
ラウンド446で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 自然 / コスト5 /
パワー4000 / 種族 ジュラシック・コマンド・ドラゴン、
mana 1、keywords・abilities ともに無し）に
第411弾の確立形 abilities 2件〔第1条項: replace
{zone: hand, optional: true, when: {event: move,
from: hand, to: graveyard, reason: discard,
subject: self, by: opp}, instead: [move {select:
{ref: self, count: 1}, to: bz, reason: put}]}
（登録済み dm26ex3-dcr005 と完全一致）／第2条項:
trigger {when: {event: move, to: bz, subject:
self}, effect: [choose {select: {zone: bz,
owner: opp, filter: {cost_le: 4}, count: 1},
as: pick}, mana_put {select: {ref: pick}}]}
（第389弾形のフィルタ違い）〕を足し、unsupported
を外したもの。abilities はこの2件ちょうど、
keywords は無いまま。**補完あり: text のみ**
（partial の text は断片「捨てられる時」のため、
text には行の公式テキスト全文を入れた。登録後の
全文一致も照合済み）。

ファミリーの残り1件 dmx26-028 熱血提督
ザーク・タイザーは対象外（CIP が公開＋種族抜き＋
残りを順序付けて山札の下へ戻す複合で未確立機構が
要る）で、ラウンド446で差し戻して残置した
（gaps・partial を保ったまま rejects に残る）。
madness は完全解消しない。alias は無い（identity
実測で canon_id は対象自身、aliases_for = []）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は None を返し定型所有は無い
（第411弾で実測）。

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
from tests.test_vocab_pilot411 import EXPANDED, FORM, FULL_TEXT  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmx18-047"
REMAINING = "dmx26-028"
GAP = "madness"
NAME = "有毒類罠顎目 ドクゲーター"

# 提出形: partial の骨格＋確立形 abilities 2件（補完は text のみ）
SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["nature"],
    "cost": 5,
    "power": 4000,
    "races": ["ジュラシック・コマンド・ドラゴン"],
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


def test_target_registered_and_family_not_cleared():
    rows = _reject_rows()
    assert len(rows) <= 1920  # 件数は減る一方（スナップショット固定をやめた）
    assert TARGET not in rows            # 登録により対象行は解消
    fam = sorted(i for i, x in rows.items()
                 if GAP in (x.get("gaps") or []))
    # ファミリーは残り1件（差し戻し）が残り、完全解消しない
    assert fam == [REMAINING]
    b = rows[REMAINING]
    assert b.get("gaps") == [GAP] and b.get("reason") == "vocab"
    bp = b["partial"]
    assert bp["name"] == "熱血提督 ザーク・タイザー"
    assert (bp.get("source") or {}).get("unsupported") == [
        {"need": GAP, "text": "捨てる時、かわりにバトルゾーンに出す"}]
    assert identity.canon_id(TARGET) == TARGET
    assert identity.aliases_for(NAME, TARGET) == []
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["nature"]
    assert c["cost"] == 5 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ジュラシック・コマンド・ドラゴン"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完は text のみ）
    # 登録形は提出形と完全一致: abilities は確立形2件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("keywords")          # text 由来キーワードは union されない
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert not src.get("aliases")        # alias 無し（自動付与なし）
    d = parse_card(c, TABLES)
    assert d.abilities == EXPANDED
    assert not d.keywords
    # プロト T1179 と abilities・text・骨格が完全一致
    proto = proto_card("T1179")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    for k in ("name", "types", "civs", "cost", "power", "races", "mana"):
        assert proto[k] == SUBMIT[k]
    assert not proto.get("keywords")
