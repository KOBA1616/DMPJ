"""語彙パイロット第212弾のカード適用テスト（登録形）。

ラウンド248: mana_number_change 単独9件のうち8件を新規登録し、
dmx08-010 は支払いのマナタップがイベント化されていない不足
（mana_tap_trigger）で差し戻した（ブースト側は partial に保存）。
ファミリーは全解消した。
"""
import copy
import json
from pathlib import Path

from dmsim.cards import cardstore

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = ("dm26rp1-006", "dmrp18-008", "dmx06-002", "dmx19-s42",
              "dmx19-v01", "dm24bd5-014", "dmsp02-006", "dm23rp1-014")


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _flat(card):
    return json.dumps(card, ensure_ascii=False)


def test_registered_forms():
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
    # 面 mana_boost（出すカード自身の宣言）
    assert _converted("dmx19-s42")["mana_boost"]["value"] == 2
    assert _converted("dmsp02-006")["mana_boost"]["value"] == 3
    v01 = _converted("dmx19-v01")
    assert v01["mana_boost"]["optional"] is True
    assert set(v01["keywords"]) == {"triple_breaker", "speed_attacker"}
    # 常在型 mana_boost
    assert "mana_boost" in _flat(_converted("dmx06-002"))
    assert "spell" in _flat(_converted("dmrp18-008"))
    assert "turn_count" in _flat(_converted("dm23rp1-014"))   # 初回詠唱の制限
    # mod mana_number
    assert "mana_number" in _flat(_converted("dm26rp1-006"))
    bd = _converted("dm24bd5-014")
    assert "mana_number" in _flat(bd)
    assert "dm22rp2-7a" in (bd["source"].get("aliases") or [])


def test_bounce_state():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    b = next(r for r in rows if r["id"] == "dmx08-010")
    assert b["gaps"] == ["mana_tap_trigger"]
    # 解けたブースト側は partial に保存されている
    assert "mana_boost" in json.dumps(b.get("partial"), ensure_ascii=False)


def test_family_cleared():
    rows = [json.loads(l) for l in open(REJECTS, encoding="utf-8")]
    # 単独は全解消。複合の dm23ex1-012 は multi_race_exclusion_filter が残る
    assert not [r for r in rows
                if (r.get("gaps") or []) == ["mana_number_change"]]
    multi = [r for r in rows if "mana_number_change" in (r.get("gaps") or [])]
    assert [r["id"] for r in multi] == ["dm23ex1-012"]
    left = {r["id"] for r in rows}
    for cid in REGISTERED:
        assert cid not in left
