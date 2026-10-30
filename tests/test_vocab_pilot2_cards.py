"""語彙パイロット第2弾: rejects の代表カードを新しい語彙／既存語彙で手変換し、parse_card を通す。

新規語彙:
- dm22rp1-025 ブースト・ドライバー … first_time（旧 first_time_per_turn_trigger）
- dm23rp4x-054 仲接 … once_per_turn（旧 once_per_turn_trigger）
- dmc42-033 ビッグ・ナスディーン … civ_count 式を from_top に（旧 civ_count）
- dm27-022 ラ・フランシス … civ_count 式を filter の cost_le に（旧 civilization_count）

既存語彙で表せたもの:
- dm22rp1-029 ヴニース … シビルカウントは「自分の文明のクリーチャー/タマシードの合計数」なので count 式で足りる（旧 civil_count の大半）
- dm26ex4-084 Disエビンビー … 「次の自分のターンのはじめまでアンタップしない」は期限型:
  tap + modify {deny: [untap_at_start], duration: until_next_own_turn_start}（旧 grant_until_next_turn_start と申告されていた）
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # 各ターン、はじめて自分のクリーチャーが出た時／はじめて自分の他のタマシードが出た時、1枚引いてもよい
        "id": "dm22rp1-025", "name": "衝突型加速3番ブースト・ドライバー", "types": ["tamaseed"],
        "civs": ["nature"], "cost": 3, "mana": 1,
        "abilities": [
            {"kind": "trigger", "first_time": True,
             "when": {"event": "move", "to": "bz", "subject": {"owner": "you", "filter": {"types": ["creature"]}}},
             "effect": [{"op": "may", "body": [{"op": "draw", "count": 1}]}]},
            {"kind": "trigger", "first_time": True,
             "when": {"event": "move", "to": "bz",
                      "subject": {"owner": "you", "other": True, "filter": {"types": ["tamaseed"]}}},
             "effect": [{"op": "may", "body": [{"op": "draw", "count": 1}]}]},
        ],
    },
    {   # 各ターンに一度、自分のクリーチャーが攻撃する時1枚引く／自分のターンの終わりに自分のクリーチャーを1体アンタップ
        "id": "dm23rp4x-054", "name": "鎧撃の支え 仲接", "types": ["creature"], "civs": ["light"],
        "cost": 3, "power": 3000, "races": ["アーマード・メタリカ"], "mana": 1, "keywords": ["blocker"],
        "abilities": [
            {"kind": "trigger", "once_per_turn": True,
             "when": {"event": "attack", "subject": {"owner": "you", "filter": {"types": ["creature"]}}},
             "effect": [{"op": "draw", "count": 1}]},
            {"kind": "trigger", "when": {"event": "turn_end", "player": "you"},
             "effect": [{"op": "untap", "select": {"zone": "bz", "owner": "you",
                                                   "filter": {"types": ["creature"]}, "count": 1}}]},
        ],
    },
    {   # シビルカウント3: 出た時、自分の光のクリーチャー/タマシードが合計3つ以上あれば1枚引く
        "id": "dm22rp1-029", "name": "巡霊者ヴニース", "types": ["creature"], "civs": ["light"],
        "cost": 2, "power": 1000, "races": ["コスモ・ウォーカー"], "mana": 1,
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "if": {"cmp": [{"count": {"zone": "bz", "owner": "you",
                                       "filter": {"types": ["creature", "tamaseed"], "civs": ["light"]}}}, ">=", 3]},
             "effect": [{"op": "draw", "count": 1}]},
        ],
    },
    {   # 出た時、自分のマナの文明の数と同じ枚数を山札の上からマナへ／破壊された時マナから2枚手札へ
        "id": "dmc42-033", "name": "大菜王ビッグ・ナスディーン", "types": ["creature", "evolution"],
        "civs": ["nature"], "cost": 7, "power": 6000, "races": ["ワイルド・ベジーズ"], "mana": 1,
        "keywords": ["double_breaker"], "evolve_from": {"races": ["ワイルド・ベジーズ"]},
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [{"op": "move",
                         "select": {"zone": "deck", "owner": "you",
                                    "from_top": {"civ_count": {"zone": "mana", "owner": "you"}}},
                         "to": "mana", "reason": "put"}]},
            {"kind": "trigger",
             "when": {"event": "move", "from": "bz", "to": "graveyard", "reason": "destroy", "subject": "self"},
             "effect": [{"op": "move", "select": {"zone": "mana", "owner": "you", "count": 2},
                         "to": "hand", "reason": "return"}]},
        ],
    },
    {   # 自分のマナの文明の数以下のコストの自分のクリーチャーが破壊される時、かわりにこのクリーチャーを破壊してもよい
        "id": "dm27-022", "name": "電界の守護者ラ・フランシス", "types": ["creature"], "civs": ["light"],
        "cost": 4, "power": 3000, "races": ["ガーディアン"], "mana": 1,
        "abilities": [
            {"kind": "replace", "optional": True,
             "when": {"event": "move", "from": "bz", "to": "graveyard", "reason": "destroy",
                      "subject": {"owner": "you", "other": True,
                                  "filter": {"types": ["creature"],
                                             "cost_le": {"civ_count": {"zone": "mana", "owner": "you"}}}}},
             "instead": [{"op": "move", "select": {"ref": "self"}, "to": "graveyard", "reason": "destroy"}]},
        ],
    },
    {   # B型フリーズ: このクリーチャーまたは自分のコスト6以上のクリーチャーが出た時、相手を1体タップし次の自分のターンのはじめまでアンタップさせない
        "id": "dm26ex4-084", "name": "Disエビンビー", "types": ["creature"], "civs": ["light"],
        "cost": 2, "power": 1500, "races": ["ガーディアン", "スチーム・ナイト", "ディスタス"], "mana": 1,
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "choose", "select": {"zone": "bz", "owner": "opp",
                                             "filter": {"types": ["creature"]}, "count": 1}, "as": "tgt"},
                 {"op": "tap", "select": {"ref": "tgt"}},
                 {"op": "modify", "select": {"ref": "tgt"}, "mod": {"deny": ["untap_at_start"]},
                  "duration": "until_next_own_turn_start"}]},
            {"kind": "trigger",
             "when": {"event": "move", "to": "bz",
                      "subject": {"owner": "you", "other": True,
                                  "filter": {"types": ["creature"], "cost_ge": 6}}},
             "effect": [
                 {"op": "choose", "select": {"zone": "bz", "owner": "opp",
                                             "filter": {"types": ["creature"]}, "count": 1}, "as": "tgt"},
                 {"op": "tap", "select": {"ref": "tgt"}},
                 {"op": "modify", "select": {"ref": "tgt"}, "mod": {"deny": ["untap_at_start"]},
                  "duration": "until_next_own_turn_start"}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_representative_reject_now_parses2(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
