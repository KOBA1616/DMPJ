"""語彙パイロット第20弾: Zラッシュの代表カードの手変換が parse_card を通ること。

変換の型: キーワード z_rush を付けるだけ（解放と期限はキーワードの誘発とターン開始処理が担う）。
ハイパーモードでだけ働く能力があれば、条件 {hyper: true} を付ける。
"""
import pytest

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # ボルシャック・マントラ: S・トリガー + 出た時、3体までタップし、相手のタップしているクリーチャーの数だけ引く + Zラッシュ
        "id": "dm26ex2-067", "name": "ボルシャック・マントラ", "types": ["creature"],
        "civs": ["light", "water"], "cost": 7, "power": 4500,
        "races": ["メカ・アーマード・ドラゴン", "シノビ", "超化獣"],
        "keywords": ["s_trigger", "z_rush"],
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "tap", "select": {"zone": "bz", "owner": "any", "filter": {"types": ["creature"]}, "count": 3, "up_to": True}},
                 {"op": "draw", "count": {"count": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"], "tapped": True}}}},
             ]},
        ],
    },
    {   # 一神のI ガナストラ: ブロッカー + ハイパーモードでなければプレイヤーを攻撃できない + Zラッシュ
        "id": "dm26rp1-054", "name": "一神のI ガナストラ", "types": ["creature"], "civs": ["light"],
        "cost": 4, "power": 3000, "races": ["ゴッド"],
        "keywords": ["blocker", "z_rush"],
        "abilities": [
            {"kind": "static", "affects": "self", "if": {"hyper": False},
             "mod": {"deny": ["attack_player"]}},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_z_rush_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
