"""語彙パイロット第378弾の対象カード検証（登録形）。

対象は pure な battle_power_against_high_power の全1件:
- dmd15-003 超竜サンバースト・NEX
ラウンド413で登録済み。登録形は提出形と完全一致:
partial の組立て済み部分（進化クリーチャー / 火 /
コスト7 / パワー11000 / 種族 アーマード・ドラゴン、
mana 1、evolve_from {races: [アーマード・ドラゴン]}、
keywords [double_breaker]、battle_win may アンタップ
誘発）に第378弾の確立形 static〔battle_power
{amount: 11000, opponent_filter: {power_ge: 12000}}、
公式テキストの条項順〕を誘発の後に足し、unsupported
を外したもの。abilities はこの2件ちょうど。text は
行の公式テキスト全文と一致するので補完は無い。単面
カードで未検証の面は無い。alias は dmc62-002 /
dmc67-004 / promoy11-027 / promoy8-010（いずれも
rejects に独自行は無く、登録形の source.aliases に
入っている）。

登録ブロッカーの確認（第375弾の教訓）: rule_convert.
split（対象行）は (["double_breaker"], 残りテキスト, [])
を返し定型所有は無いことを第378弾で実測済みで、
ラウンド413は通常どおり submit できた。

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
TARGET = "dmd15-003"
GAP = "battle_power_against_high_power"
ALIASES = ["dmc62-002", "dmc67-004", "promoy11-027", "promoy8-010"]

UNTAP = {"kind": "trigger",
         "when": {"event": "battle_win", "subject": "self"},
         "effect": [{"op": "may", "body": [
             {"op": "untap", "select": {"ref": "self"}}]}]}
STATIC = {"kind": "static", "affects": "self",
          "mod": {"battle_power": {"amount": 11000,
                                   "opponent_filter": {"power_ge": 12000}}}}
FORM = [UNTAP, STATIC]
FULL_TEXT = ("進化-自分のアーマード・ドラゴン１体の上に置く。"
             "このクリーチャーがバトルに勝った時、このクリーチャーをアンタップしてもよい。"
             "パワー12000以上のクリーチャーとバトル中、このクリーチャーのパワーは+11000される。"
             "W・ブレイカー")


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
    # alias に rejects の独自行は無い
    for a in ALIASES:
        assert a not in rows


def test_registered_form_parses_and_matches_proto():
    c = find(CONVERTED, TARGET)
    assert c["types"] == ["creature", "evolution"]
    assert c["civs"] == ["fire"]
    assert c["cost"] == 7 and c["power"] == 11000
    assert c["races"] == ["アーマード・ドラゴン"]
    assert c["mana"] == 1
    assert c["evolve_from"] == {"races": ["アーマード・ドラゴン"]}
    assert c["keywords"] == ["double_breaker"]
    assert c["text"] == FULL_TEXT                      # 公式テキスト全文（補完なし）
    # 登録形は提出形と完全一致: 確立形2能力ちょうど（条項順）
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2
    assert not c.get("aliases")
    # alias 4件は source.aliases に入っている
    assert (c.get("source") or {}).get("aliases") == ALIASES
    assert not (c.get("source") or {}).get("unsupported")
    # parse は double_breaker を breaks 常在型に展開するので
    # 包含で確認する（第372弾の作法）
    d = parse_card(c, TABLES)
    assert STATIC in d.abilities and UNTAP in d.abilities
    # プロト T1128 と abilities・text が完全一致
    proto = proto_card("T1128")
    assert proto["abilities"] == FORM
    assert proto["text"] == FULL_TEXT
