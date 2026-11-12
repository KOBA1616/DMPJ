"""語彙パイロット第191弾のカード適用テスト（登録形）。

ラウンド227で mana_bakutan 単独9件のうち8件を登録、1件を差し戻し。
- 登録8件: converted.yaml から読み、mana_bakutan の値を確認
  （dmex08-072 は「マナゾーンから召喚していたら」の出た時誘発も確認。
  召喚の移動イベント from: mana / reason: summon への trigger と、
  自然カードが無ければ破壊する if/else は既存語彙）。
- dm37-s05（大地竜機シロガシラ・ジュカイ）は差し戻し: 召喚誘発が
  「マーシャル・タッチ能力を持つクリーチャー」節を含むため marshal_touch が
  必要（新ギャップ marshal_touch）。mana_bakutan: 9 は partial に残した。
  「マナゾーンに置く時タップして置く」は多色カードのルール（405.1）で自動。
"""
import copy
import json
from pathlib import Path

from dmsim import cardstore
from dmsim.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

BAKUTAN = {
    "dm36-037": 3,    # 桜丸パグのすけ
    "dm36-066": 7,    # 霊騎オメン・オズボーン
    "dm36-105": 4,    # ビートル・モグッタン
    "dm36-108": 2,    # 雪布妖精ユウコ
    "dmex10-036": 4,  # 馬番の騎手 アリマ＆キッカ
    "dmx11-056": 4,   # 絢爛の超人
    "dmx12b-044": 9,  # 恵みの大地ババン・バン・バン（CIP は元から partial にあった）
    "dmex08-072": 0,  # 陰陽の舞（出た時誘発も登録形にある）
}

FROM_MANA_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from": "mana", "to": "bz",
             "reason": "summon", "subject": "self"},
    "effect": [
        {"op": "if",
         "cond": {"exists": {"zone": "mana", "owner": "you",
                             "filter": {"civs": ["nature"]}}},
         "then": [{"op": "move",
                   "select": {"zone": "mana", "owner": "you",
                              "filter": {"civs": ["nature"]}, "count": 1},
                   "to": "graveyard", "reason": "put"}],
         "else": [{"op": "destroy", "select": {"ref": "self"}}]},
    ],
}


def _converted(cid):
    for c in cardstore.read(CONVERTED):
        if c["id"] == cid:
            return c
    raise KeyError(cid)


def _reject(cid):
    for line in open(REJECTS, encoding="utf-8"):
        r = json.loads(line)
        if r["id"] == cid:
            return r
    raise KeyError(cid)


def test_registered_forms():
    for cid, n in BAKUTAN.items():
        card = _converted(cid)
        d = parse_card(copy.deepcopy(card), TABLES)
        assert d.mana_bakutan == n, cid


def test_from_mana_trigger_registered():
    card = _converted("dmex08-072")
    assert FROM_MANA_TRIGGER in (card.get("abilities") or [])


def test_dm37s05_bounced_with_banked_bakutan():
    r = _reject("dm37-s05")
    # ラウンド227 では marshal_touch で差し戻し。第193弾で marshal_touch を実装した後、
    # 残る障害は能力所持フィルタ has_ability_filter に細分された（tests/test_vocab_pilot193_cards.py）
    assert r["gaps"] == ["has_ability_filter"]
    assert r["partial"].get("mana_bakutan") == 9, "解けた節（マナ爆誕9）が残っていない"
