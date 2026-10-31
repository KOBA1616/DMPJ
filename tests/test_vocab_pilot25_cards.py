"""語彙パイロット第25弾: フェーズ3の代表カードの手変換が parse_card を通ること。

変換の型:
- D2フィールド: types: [field]（出す処理と常在型・誘発は既存。フィールドの一意性は第25弾で実装）
- D・D・D: declare（zone: hand）+ play_self {cost, civs}（キリフダッシュと同じ型）
- G・城: galaxy_shield 宣言 + zone: shield の常在型/置換（置換の発生源にシールドゾーンを追加したのは第25弾）
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # Dの天災 海底研究所: フィールド。出た時ドロー + 自分の進化クリーチャーはブロックされない
        # （「相手の進化クリーチャーは出たターン攻撃できない」は対象側の条件つき deny として別途）
        "id": "dm23ex2-071", "name": "Dの天災 海底研究所", "types": ["field"],
        "civs": ["water"], "cost": 2,
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [{"op": "draw", "count": 1}]},
            {"kind": "static", "affects": {"zone": "bz", "owner": "you", "filter": {"types": ["evolution"]}},
             "mod": {"grant": ["unblockable"]}},
        ],
    },
    {   # 魔誕妖蟲デンジャラス・ワーム: D・D・D [闇火自然6] + ガードマン（出た時・離れた時の効果は省略）
        "id": "dm25ex3-021", "name": "魔誕妖蟲デンジャラス・ワーム", "types": ["creature"], "civs": ["fire"],
        "cost": 2, "power": 2000, "races": ["パラサイトワーム"],
        "keywords": ["guardman"],
        "abilities": [
            {"kind": "declare", "zone": "hand",
             "when": {"event": "attack", "subject": {"owner": "you", "filter": {"types": ["creature"]}}},
             "effect": [{"op": "may", "body": [
                 {"op": "play_self", "cost": 6, "civs": ["darkness", "fire", "nature"]}]}]},
        ],
    },
    {   # 希望の太陽 マイハマタワー: G・城（表向きシールド化 + 離脱置換 + シールドから自分のアーマードに付与）
        "id": "dm26ex2-047", "name": "希望の太陽 マイハマタワー", "types": ["creature"], "civs": ["light", "fire"],
        "cost": 2, "power": None, "races": [],
        "galaxy_shield": {"cost": 2, "civs": ["light", "fire"]},
        "abilities": [
            {"kind": "static", "zone": "shield", "if": {"face_up": True},
             "affects": {"zone": "bz", "owner": "you", "filter": {"race_has": "アーマード"}},
             "mod": {"grant": ["blocker", "speed_attacker"]}},
            {"kind": "replace", "zone": "shield",
             "when": {"event": "move", "from": "shield", "subject": "self"}, "if": {"face_up": True},
             "instead": [{"op": "move", "select": {"ref": "self"}, "to": "graveyard", "reason": "put"}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_phase3_representative_parses(raw):
    raw = {k: v for k, v in raw.items() if v is not None}
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
