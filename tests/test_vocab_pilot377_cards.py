"""語彙パイロット第377弾の対象カード検証（登録形）。

対象は pure な battle_power_against_specific_civ の全1件:
- dmd05-001 無限鉄拳オニナグリ
ラウンド412で登録済み。登録形は提出形と完全一致:
partial の組立て済み部分（進化クリーチャー / 闇・火 /
コスト6 / パワー7000 / 種族 ヒューマノイド・ハンター・
エイリアン、mana 1、evolve_from {races: [ハンター]}、
keywords [double_breaker]、battle_win アンタップ誘発）
に第377弾の確立形 static〔battle_power {amount: 2000,
opponent_filter {civs: [light]}}、公式テキストの条項順〕
を誘発の前に足し、unsupported を外したもの。abilities は
この2件ちょうど。text は行の公式テキスト全文と一致する
ので補完は無い。単面カードで未検証の面は無い。alias は
無い。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (["double_breaker"], 残りテキスト, [])
を返し定型所有は無いことを第377弾で実測済みで、
ラウンド412は通常どおり submit できた。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので _conv_cache を直接使う（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card  # noqa: E402
from tests._conv_cache import find, proto_card  # noqa: E402

ROOT = Path(__file__).parent.parent
CONVERTED = cardstore.converted_path(DATA)
TABLES = load_tables()
TARGET = "dmd05-001"
GAP = "battle_power_against_specific_civ"

STATIC = {"kind": "static", "affects": "self",
          "mod": {"battle_power": {"amount": 2000,
                                   "opponent_filter": {"civs": ["light"]}}}}
UNTAP = {"kind": "trigger",
         "when": {"event": "battle_win", "subject": "self"},
         "effect": [{"op": "untap", "select": {"ref": "self"}}]}
FORM = [STATIC, UNTAP]
FULL_TEXT = ("マナゾーンに置く時、このカードはタップして置く。\n"
             "進化-自分のハンター・クリーチャー１体の上に置く。\n"
             "光のクリーチャーとバトル中、このクリーチャーのパワーは+2000される。\n"
             "このクリーチャーがバトルに勝った時、このクリーチャーをアンタップする。\n"
             "W・ブレイカー(このクリーチャーはシールドを２枚ブレイクする)")


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
    assert TARGET not in rows            # 登録により対象行は解消
    fam = [i for i, x in rows.items() if GAP in (x.get("gaps") or [])]
    assert fam == []                     # ファミリーはこの1件だけだった
    assert find(CONVERTED, TARGET) is not None


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["types"] == ["creature", "evolution"]
    assert c["civs"] == ["darkness", "fire"]
    assert c["cost"] == 6 and c["power"] == 7000
    assert c["races"] == ["ヒューマノイド", "ハンター", "エイリアン"]
    assert c["mana"] == 1
    assert c["evolve_from"] == {"races": ["ハンター"]}
    assert c["keywords"] == ["double_breaker"]
    assert c["text"] == FULL_TEXT                      # 公式テキスト全文（補完なし）
    # 登録形は提出形と完全一致: 確立形2能力ちょうど（条項順）
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("aliases")                        # alias は無い
    assert not (c.get("source") or {}).get("aliases")
    assert not (c.get("source") or {}).get("unsupported")
    # parse は double_breaker を breaks 常在型に展開するので
    # 包含で確認する（第372弾の作法）
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities and UNTAP in d.abilities
    # プロト T1125 と abilities・text が完全一致
    proto = proto_card("T1125")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT.replace("\n", "")
