"""語彙パイロット第193弾のカード適用テスト（登録形）。

ラウンド229で marshal_touch 単独9件を新規登録し、dm37-s05 を差し戻した。
- 登録9件: converted.yaml から読み、マーシャル・タッチのイディオム
  （CIP → may[ move（他の自分のクリーチャー→手札）, if exists → 後続 ]）を
  含むことを確認。dm37-031 / dmex08-060 はマナ爆誕フィールドも併せて持つ。
  dmex12-098 の K・ソウルは種族として登録されている。
- dm37-s05 は差し戻し: 「『マナ爆誕』能力を持つ／『マーシャル・タッチ』
  能力を持つクリーチャー」で山札の上を絞る能力持ちフィルタが無い
  （新ギャップ has_ability_filter）。mana_bakutan: 9 は partial に保存。
"""
import json
from pathlib import Path

from dmsim.cards import cardstore
from dmsim.cards.defs import DATA, load_tables, parse_card

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"

REGISTERED = ("dm36-033", "dm36-062", "dm36-095", "dm37-014", "dm37-031",
              "dm39-048", "dmex08-060", "dmex08-088", "dmex12-098")


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
    import copy
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        trig = card["abilities"][0]
        body = trig["effect"][0]
        assert body["op"] == "may", cid
        move_op, if_op = body["body"]
        assert move_op["op"] == "move" and move_op["as"] == "bounced", cid
        assert move_op["select"]["other"] is True, cid
        assert if_op["op"] == "if" and if_op["cond"] == {"exists": {"ref": "bounced"}}, cid


def test_bakutan_and_soul_details():
    assert _converted("dm37-031")["mana_bakutan"] == 7
    assert _converted("dmex08-060")["mana_bakutan"] == 5
    assert "K・ソウル" in (_converted("dmex12-098").get("races") or [])


def test_s05_bounced_with_banked_bakutan():
    r = _reject("dm37-s05")
    assert r["gaps"] == ["has_ability_filter"]
    assert r["partial"]["mana_bakutan"] == 9
