"""語彙パイロット第26弾: フェーズ4の代表カードの手変換が parse_card を通ること。

変換の型:
- ガチンコ・ジャッジ: op gachinko {times / until_lose+stoppable, as} で勝ち数を変数に書き、後続が {var} で参照する
- スーパー・S・トリガー: キーワード super_s_trigger + 追加能力は sst: true 印（クリーチャー）/ sst_spell（呪文）
- 超魂X: 能力に choukon: true 印（下に重なっている時に一番上のクリーチャーが得る）
- バズレンダ: 面の宣言 bazurenda {cost, civs} + [OL] 能力に bazurenda: true 印
"""
import pytest

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # 真実の名 タイガー・レジェンド: 出た時、負けるか中止するまでガチンコ → 勝った回数まで手札から出す
        "id": "dm22rp2x-tr9", "name": "真実の名 タイガー・レジェンド", "types": ["creature"], "civs": ["light"],
        "cost": 7, "power": 7500, "keywords": ["blocker", "double_breaker"],
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "gachinko", "until_lose": True, "stoppable": True, "as": "wins"},
                 {"op": "move", "select": {"zone": "hand", "owner": "you", "count": {"var": "wins"}, "up_to": True,
                                           "filter": {"types": ["creature"], "civs": ["light"],
                                                      "not_types": ["evolution"], "keyword": "blocker"}},
                  "to": "bz", "reason": "put"}]},
        ],
    },
    {   # 冥王の牙: スーパー・S・トリガー呪文。本体は破壊、追加能力は sst_spell
        "id": "dm22ex2-017", "name": "冥王の牙", "types": ["spell"], "civs": ["darkness"], "cost": 7,
        "keywords": ["super_s_trigger"],
        "spell": [
            {"op": "move", "select": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}, "count": 1},
             "to": "graveyard", "reason": "destroy"},
        ],
        "sst_spell": [
            {"op": "move", "select": {"zone": "deck", "owner": "you", "count": 3}, "to": "graveyard", "reason": "put"},
            {"op": "move", "select": {"zone": "graveyard", "owner": "you", "count": 1,
                                       "filter": {"types": ["creature"], "civs": ["darkness"], "not_types": ["evolution"]}},
             "to": "bz", "reason": "put"},
        ],
    },
    {   # フラワー・ハート: 超魂X（下にあれば、上のクリーチャーは攻撃時にドロー+捨てる誘発を得る）
        "id": "dm25ex1-080", "name": "フラワー・ハート", "types": ["creature"], "civs": ["water"],
        "cost": 1, "power": 1000, "keywords": ["blocker"],
        "abilities": [
            {"kind": "static", "affects": "self", "mod": {"deny": ["attack_player", "attack_creature"]}},
            {"kind": "trigger", "choukon": True, "when": {"event": "attack", "subject": "self"},
             "effect": [
                 {"op": "may", "body": [
                     {"op": "draw", "count": 1},
                     {"op": "move", "select": {"zone": "hand", "owner": "you", "count": 1},
                      "to": "graveyard", "reason": "discard"}]}]},
        ],
    },
    {   # 遊戯の超人: バズレンダ[3]。出た時に山札上2枚をタップしてマナへ（1+追加回数）
        "id": "dm23bd5-029", "name": "遊戯の超人", "types": ["creature"], "civs": ["nature"],
        "cost": 5, "power": 2000, "bazurenda": {"cost": 3, "civs": []},
        "abilities": [
            {"kind": "trigger", "bazurenda": True, "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "move", "select": {"zone": "deck", "owner": "you", "count": 2},
                  "to": "mana", "reason": "charge", "tapped": True}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_phase4_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
