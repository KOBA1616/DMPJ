"""語彙パイロット第47弾: 実カード定義（多文明O・ドライブ／呪文側）の parse 検証。"""
import os

os.environ.setdefault("DMSIM_SKIP_CONVERTED", "1")

from dmsim.defs import load_tables, parse_card

T = load_tables()

CARDS = [
    # dm26-031 勇猛機動ライオン・アームズ: まとめて形（火×1と自然×1）
    {
        "id": "dm26-031", "name": "勇猛機動ライオン・アームズ", "types": ["creature"],
        "civs": ["fire", "nature"], "cost": 6, "power": 8000, "mana": 1,
        "races": ["アーマロイド", "ホーン・ビースト"], "keywords": ["double_breaker"],
        "o_drive": {"civs": {"fire": 1, "nature": 1}},
        "abilities": [
            {"kind": "trigger", "odrive": True, "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [{"op": "modify", "select": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"]}, "count": "all"},
                         "mod": {"power": 2000, "grant": ["double_breaker"]}, "duration": "end_of_turn"}]},
        ],
    },
    # dmc55-067 猛菌恐皇ビューティシャン: まとめて形（水×1と闇×1）
    {
        "id": "dmc55-067", "name": "猛菌恐皇ビューティシャン", "types": ["creature"],
        "civs": ["water", "darkness"], "cost": 2, "power": 1000, "mana": 1,
        "races": ["サイバー・ウイルス", "ダークロード"], "keywords": ["blocker", "cannot_attack"],
        "o_drive": {"civs": {"water": 1, "darkness": 1}},
        "abilities": [
            {"kind": "trigger", "odrive": True, "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "move", "select": {"zone": "hand", "owner": "opp", "count": 1, "chooser": "opp"}, "to": "graveyard", "reason": "discard"},
                 {"op": "may", "body": [{"op": "draw", "count": 1}]},
             ]},
        ],
    },
    # dmc47-041 森の指揮官コアラ大佐: 文明別形（光/火）— 文明別の印で parse できることの確認（光の能力は ability_ignore のため未収録）
    {
        "id": "dmc47-041", "name": "森の指揮官コアラ大佐", "types": ["creature"],
        "civs": ["nature"], "cost": 3, "power": 2000, "mana": 1,
        "races": ["ドリームメイト"],
        "o_drive": {"civs": {"light": 1, "fire": 1}, "each": True},
        "abilities": [
            {"kind": "trigger", "odrive": "fire", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [{"op": "modify", "select": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"]}, "count": 1},
                         "mod": {"grant": ["double_breaker"]}, "duration": "end_of_turn"}]},
        ],
    },
    # dm24-078 ソーラー・ドライブ: 呪文側 O・ドライブ（odrive_spell）
    {
        "id": "dm24-078", "name": "ソーラー・ドライブ", "types": ["spell"],
        "civs": ["light"], "cost": 2, "mana": 1,
        "o_drive": {"civ": "water", "count": 1},
        "spell": [
            {"op": "choose", "select": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"]}, "count": 1}, "as": "t"},
            {"op": "delayed_trigger", "when": {"event": "turn_end"},
             "effect": [{"op": "untap", "select": {"ref": "t"}}]},
        ],
        "odrive_spell": [
            {"op": "tap", "select": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}, "count": 1}},
        ],
    },
]


def test_pilot47_real_cards_parse():
    for c in CARDS:
        parse_card(c, T, where=c["id"])
