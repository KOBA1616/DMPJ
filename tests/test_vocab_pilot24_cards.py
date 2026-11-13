"""語彙パイロット第24弾: フェーズ2の代表カードの手変換が parse_card を通ること。

変換の型:
- 革命チェンジ: declare（zone: hand）+ when attack + swap {out: event.subject, in: self}（既存）
- 侵略: declare + op invade {onto: event.subject}（第24弾で新設）
- アタック・チャンス: declare + play_free {ref: self}（既存）。「すべてを持つ」は filter の civs_all（第24弾で追加）
- J・チェンジ: 攻撃時誘発 + swap {out_to: mana, in: マナゾーンの選択}（第24弾で swap を拡張）
"""
import pytest

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # タイク・タイソンズ: J・チェンジ4 + 離れた時、山札の上から1枚をマナに置く（完全変換）
        "id": "dm24ex3-tf36", "name": "タイク・タイソンズ", "types": ["creature"], "civs": ["nature"],
        "cost": 2, "power": 1000, "races": ["ジョーカーズ"],
        "abilities": [
            {"kind": "trigger", "when": {"event": "attack", "subject": "self"},
             "effect": [{"op": "may", "body": [
                 {"op": "swap", "out": {"ref": "self"}, "out_to": "mana",
                  "in": {"zone": "mana", "owner": "you",
                         "filter": {"types": ["creature"], "cost_le": 4, "races": ["ジョーカーズ"]}, "count": 1}}]}]},
            {"kind": "trigger", "when": {"event": "move", "from": "bz", "subject": "self"},
             "effect": [
                 {"op": "move", "select": {"zone": "deck", "owner": "you", "count": 1}, "to": "mana", "reason": "charge"}]},
        ],
    },
    {   # 超音速 ターボ+1: 進化 + 侵略（ETB の「好きな枚数捨てて+1引く」は変数系の別パターンとして省略）
        "id": "dm22ex2-025", "name": "超音速 ターボ+1", "types": ["creature", "evolution"], "civs": ["darkness", "fire"],
        "cost": 5, "power": 7000, "races": ["ソニック・コマンド", "侵略者"],
        "keywords": ["slayer", "double_breaker"],
        "evolve_from": {"civs": ["darkness", "fire"], "types": ["creature"]},
        "abilities": [
            {"kind": "declare", "zone": "hand",
             "when": {"event": "attack", "subject": {"owner": "you", "filter": {"civs": ["darkness", "fire"], "race_has": "コマンド"}}},
             "effect": [{"op": "may", "body": [{"op": "invade", "onto": {"ref": "event.subject"}}]}]},
        ],
    },
    {   # 未来の法皇 ミラダンテSF: 革命チェンジ（ファイナル革命は「革命チェンジによって出た時」の via 照合が未対応のため省略）
        "id": "dm22rp1-tr2", "name": "未来の法皇 ミラダンテSF", "types": ["creature"], "civs": ["light", "water"],
        "cost": 8, "power": 12500, "races": ["エンジェル・コマンド・ドラゴン", "革命軍", "ドレミ団"],
        "keywords": ["triple_breaker"],
        "abilities": [
            {"kind": "declare", "zone": "hand",
             "when": {"event": "attack", "subject": {"owner": "you", "filter": {"civs": ["light", "water"], "cost_ge": 5, "race_has": "ドラゴン"}}},
             "effect": [{"op": "may", "body": [
                 {"op": "swap", "out": {"ref": "event.subject"}, "in": {"ref": "self"}}]}]},
        ],
    },
    {   # 禁時王秘伝エンドオブランド: アタック・チャンス（最後の文の唱え制限は省略）
        "id": "dm22ex1-cho10", "name": "禁時王秘伝エンドオブランド", "types": ["spell"], "civs": ["light", "water", "fire"],
        "cost": 5,
        "abilities": [
            {"kind": "declare", "zone": "hand",
             "when": {"event": "attack", "subject": {"owner": "you", "filter": {"civs_all": ["light", "water", "fire"], "race_has": "ディスペクター"}}},
             "effect": [{"op": "may", "body": [{"op": "play_free", "select": {"ref": "self"}}]}]},
        ],
        "spell": [
            {"op": "move", "select": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"], "cost_le": 8}, "count": 1},
             "to": "graveyard", "reason": "destroy"},
            {"op": "draw", "count": 2},
            {"op": "move", "select": {"zone": "hand", "owner": "you", "count": 1}, "to": "graveyard", "reason": "discard"},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_phase2_representative_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
