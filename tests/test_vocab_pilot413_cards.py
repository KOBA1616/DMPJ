"""語彙パイロット第413弾の対象カード検証（登録形）。

対象は battle_result_destruction（pure 1件、multi にも
現れない）:
- dmx03-036 ブラッディ・シンバル
ラウンド448で登録済み。登録形は提出形と完全一致:
partial の骨格（クリーチャー / 闇 / コスト2 /
パワー4000 / 種族 ガーゴイル、mana 1、keywords
[blocker, cannot_attack] が構築済み）に第413弾の
確立形 trigger {when: {event: battle_win, subject:
self}, effect: [destroy {select: {ref: self}}]}
（登録済み dm01-026 / dm01-056 / dm01-089 / dm06-027 /
dm06-087 の5件と完全一致）を足し、unsupported を
外したもの。abilities は誘発1件ちょうど、keywords は
そのまま。**補完なし**（partial の text は行の公式
テキスト全文と一致）。

alias は dm14-091 / dmc42-071 の2件で rejects に
独自行は無く、登録エントリの source.aliases に
validate が自動付与した。identity 実測で canon_id は
対象自身（alias 側の canon も dmx03-036）、
aliases_for = [dm14-091, dmc42-071]。
battle_result_destruction は完全解消。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (['blocker', 'cannot_attack'],
「このクリーチャーはバトルに勝っても、バトルの後、
破壊される。」, []) を返し、part[2] の定型所有は空
（キーワードは partial と一致）＝ツール側ブロッカー
なし。ラウンド448の登録で、登録後の abilities は
誘発1件ちょうどであることを実測確認済み。

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
from tests.test_vocab_pilot413 import FORM, FULL_TEXT, PARSED_TRIG  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmx03-036"
ALIASES = ["dm14-091", "dmc42-071"]
GAP = "battle_result_destruction"
NAME = "ブラッディ・シンバル"

# 提出形: partial の骨格＋確立形 trigger（補完なし）
SUBMIT = {
    "id": TARGET,
    "name": NAME,
    "types": ["creature"],
    "civs": ["darkness"],
    "cost": 2,
    "power": 4000,
    "races": ["ガーゴイル"],
    "mana": 1,
    "text": FULL_TEXT,
    "keywords": ["blocker", "cannot_attack"],
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
    assert len(rows) == 1918
    assert TARGET not in rows            # 登録により対象行は解消
    fam = sorted(i for i, x in rows.items()
                 if GAP in (x.get("gaps") or []))
    assert fam == []                     # ファミリー完全解消
    for a in ALIASES:
        assert a not in rows             # alias に独自行なし
        assert identity.canon_id(a) == TARGET
        assert find(CONVERTED, a) is None
    assert identity.canon_id(TARGET) == TARGET
    assert identity.aliases_for(NAME, TARGET) == ALIASES
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["name"] == NAME
    assert c["types"] == ["creature"] and c["civs"] == ["darkness"]
    assert c["cost"] == 2 and c["power"] == 4000 and c["mana"] == 1
    assert c["races"] == ["ガーゴイル"]
    assert c["text"] == FULL_TEXT        # 公式全文（補完なし）
    # 登録形は提出形と完全一致: abilities は誘発1件ちょうど
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 1
    assert c["keywords"] == ["blocker", "cannot_attack"]
    assert not c.get("aliases")
    src = c.get("source") or {}
    assert not src.get("unsupported")
    assert src.get("aliases") == ALIASES  # validate の自動付与
    d = parse_card(c, TABLES)
    assert PARSED_TRIG in d.abilities
    assert len(d.abilities) == 3         # キーワード static 2件＋誘発
    assert d.keywords == ["blocker", "cannot_attack"]
    # プロト T1181 と abilities・text・骨格が完全一致
    proto = proto_card("T1181")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
    assert proto["keywords"] == ["blocker", "cannot_attack"]
    for k in ("name", "types", "civs", "cost", "power", "races", "mana"):
        assert proto[k] == SUBMIT[k]
