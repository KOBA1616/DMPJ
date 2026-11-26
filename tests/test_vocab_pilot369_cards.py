"""語彙パイロット第369弾の対象カード検証（登録形）。

対象は pure な no_shield_break の全1件:
- dmex03-061 夜のポンの助
ラウンド404で登録済み。登録形は提出形と完全一致:
partial の骨格〔types [creature] / civs [zero] /
cost 1 / power 820 / races [ジョーカーズ] / mana 1、
abilities・keywords ともに無し〕に第369弾の確立形
2能力〔static {affects: self, mod: {breaks: 0}}
（dmex17-106 の登録先例と同形）＋ static {affects:
{zone: shield, owner: you}, mod: {deny: [s_trigger]}}
（dm04-022 の登録先例の変種）〕を足し、unsupported を
外したもの。補完あり: partial の text は第1条項だけの
ため、提出時に text へ行の公式テキスト全文（3条項）を
入れた。第3条項はデッキ構築ルールで dmex13-057 の
先例どおりエンジン側に委ねる。単面カードで未検証の
面は無い。alias は無い。

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
TARGET = "dmex03-061"
GAP = "no_shield_break"

BREAKS0 = {"kind": "static", "affects": "self", "mod": {"breaks": 0}}
STRIGGER_DENY = {"kind": "static",
                 "affects": {"zone": "shield", "owner": "you"},
                 "mod": {"deny": ["s_trigger"]}}
FORM = [BREAKS0, STRIGGER_DENY]
FULL_TEXT = ("このクリーチャーはシールドをブレイクできない。\n"
             "自分は「S・トリガー」能力を使えない。\n"
             "このカードは、４枚より多くデッキに入れることができる。")


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
    assert c["types"] == ["creature"] and c["civs"] == ["zero"]
    assert c["cost"] == 1 and c["power"] == 820
    assert c["races"] == ["ジョーカーズ"] and c["mana"] == 1
    assert c["text"] == FULL_TEXT       # 公式テキスト全文（補完）
    assert c["abilities"] == FORM
    assert len(c["abilities"]) == 2      # static 2件ちょうど
    assert not c.get("keywords")         # keywords は無いまま
    assert not (c.get("source") or {}).get("unsupported")
    d = parse_card(c, TABLES)
    assert BREAKS0 in d.abilities and STRIGGER_DENY in d.abilities
    # プロト T1112 と abilities が完全一致
    proto = proto_card("T1112")
    assert proto["abilities"] == FORM
