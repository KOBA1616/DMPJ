"""語彙パイロット第27弾: フェーズ5の代表カードの手変換が parse_card を通ること。

変換の型:
- ムゲンクライム: 面の宣言 mugen_climb {tap, cost, civs}
- S・トリガー・プラス: キーワード s_trigger_plus + stp_spell
- O・ドライブ: 面の宣言 o_drive {civ, count} + odrive: true 印の能力
- シールド・ゴー: キーワード shield_go（置換2つに展開される）
- タップしてマナに置く: move の tapped: true（既存。新規実装なし）
- ドロン・ゴー: 破壊された時の誘発 + move（name_has フィルタ）+ deny enter_bz の常在型（既存の組み合わせ）
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # 罪無 ドロキオ垓: ムゲンクライム2 [水水2]
        "id": "dm24ex3-tf06", "name": "罪無 ドロキオ垓", "types": ["creature"], "civs": ["water"],
        "cost": 6, "power": 3000, "keywords": ["s_trigger", "blocker"],
        "mugen_climb": {"tap": 2, "cost": 2, "civs": ["water"]},
        "abilities": [
            {"kind": "trigger", "when": {"event": "tap", "subject": "self"},
             "effect": [
                 {"op": "choose", "select": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}, "count": 1}, "as": "tg"},
                 {"op": "modify", "select": {"ref": "tg"}, "mod": {"deny": ["attack_player", "attack_creature", "block"]},
                  "duration": "until_next_own_turn_start"}]},
        ],
    },
    {   # 極閃呪文「バリスパーク」: S・トリガー・プラス。本体は全タップ、追加はシールド化
        "id": "dm23rp1-012", "name": "極閃呪文「バリスパーク」", "types": ["spell"], "civs": ["light"], "cost": 5,
        "keywords": ["s_trigger_plus"],
        "spell": [
            {"op": "tap", "select": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}, "count": "all"}},
        ],
        "stp_spell": [
            {"op": "move", "select": {"zone": "deck", "owner": "you", "count": 1}, "to": "shield", "reason": "put"},
        ],
    },
    {   # 宣凶師ルギアス: O・ドライブ 水x2
        "id": "dm24-012", "name": "宣凶師ルギアス", "types": ["creature"], "civs": ["light"],
        "cost": 5, "power": 4500, "o_drive": {"civ": "water", "count": 2},
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "tap", "select": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}, "count": 1}}]},
            {"kind": "trigger", "odrive": True, "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "move", "select": {"zone": "bz", "owner": "any", "filter": {"types": ["creature"]}, "count": 1},
                  "to": "hand", "reason": "return"}]},
        ],
    },
    {   # 凄惨なる牙 パラノーマル: シールド・ゴー + 表向きシールドの間の常在型
        "id": "dm23ex1-036", "name": "凄惨なる牙 パラノーマル", "types": ["creature"], "civs": ["darkness"],
        "cost": 7, "power": 7000, "keywords": ["double_breaker", "shield_go"],
        "abilities": [
            {"kind": "static", "zone": "shield", "if": {"face_up": True},
             "affects": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}},
             "mod": {"power": -3000}},
        ],
    },
    {   # 神秘の石柱: タップしてマナに置く（move の tapped）
        "id": "dmrp14-084", "name": "神秘の石柱", "types": ["spell"], "civs": ["nature"], "cost": 3,
        "spell": [
            {"op": "move", "select": {"zone": "deck", "owner": "you", "count": 2}, "to": "mana", "reason": "charge", "tapped": True},
            {"op": "move", "select": {"zone": "mana", "owner": "you", "count": 1}, "to": "graveyard", "reason": "put"},
        ],
    },
    {   # 暴剣王邪 ハリケーン: ドロン・ゴー（ETB部分は省略）
        "id": "dmd11-001", "name": "暴剣王邪 ハリケーン", "types": ["creature"], "civs": ["water", "fire"],
        "cost": 9, "power": 12000, "keywords": ["triple_breaker"],
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "from": "bz", "to": "graveyard", "reason": "destroy", "subject": "self"},
             "effect": [
                 {"op": "may", "body": [
                     {"op": "move", "select": {"zone": "hand", "owner": "you", "count": 1,
                                                "filter": {"types": ["creature"], "name_has": "暴剣"}},
                      "to": "bz", "reason": "put"}]}]},
            {"kind": "static", "affects": {"zone": "bz", "owner": "you", "other": True,
                                            "filter": {"types": ["creature"], "name_has": "暴剣"}},
             "mod": {"deny": ["enter_bz"]}},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_phase5_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
