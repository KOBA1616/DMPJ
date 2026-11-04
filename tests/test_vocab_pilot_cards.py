"""語彙パイロット: rejects の代表カードを新しい語彙／既存語彙の組み合わせで手変換し、
defs.parse_card（登録時の検証）を通ることを示す。

新規語彙を使うもの:
- dmrp14-084 神秘の石柱        … move の tapped（旧 need: tapped_mana_placement）
- dm30-011 キサナティック・X   … op force_battle（旧 need: force_battle）
- dm22rp1-054 権力のコイン     … tap の no_untap_next（旧 need: does_not_untap_next_turn）
- dmex02-023 紅の猛り 天鎖     … キーワード enters_tapped（旧 need: enters_tapped）

実は既存語彙で表せたもの（変換側の知識不足で rejects に入っていた）:
- dm23ex2-060 影世界のシクミ   … duration until_next_own_turn_start は既存（旧 need: grant_until_next_turn_start）
- dm25ex1-036 ジェネラローズ   … filter の not_types: [evolution]（旧 need: not_evolution_filter。クリーチャー面のみで検証）
- dm25rp1-056 ～銀眼の看守～    … filter の types: [evolution]（旧 need: evolution_filter）
- dmr13-061 爆打者 猛トラック  … event battle_win（旧 need: won_battle）
- dmrp17-003 バフォロメア      … キーワード g_strike は既存（旧 need: g_strike）。
  「G・ストライクで見せた時」は既存の g_strike と同じ move（shield→hand）誘発で表す
"""
import pytest

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {   # 神秘の石柱: 山札の上から2枚をタップしてマナに置き、その後マナを1枚墓地へ
        "id": "dmrp14-084", "name": "神秘の石柱", "types": ["spell"], "civs": ["nature"],
        "cost": 3, "mana": 1,
        "spell": [
            {"op": "move", "select": {"zone": "deck", "owner": "you", "from_top": 2},
             "to": "mana", "reason": "put", "tapped": True},
            {"op": "move", "select": {"zone": "mana", "owner": "you", "count": 1},
             "to": "graveyard", "reason": "put"},
        ],
    },
    {   # キサナティック・X: クリーチャーを2体選びタップし、その同士をバトルさせる
        "id": "dm30-011", "name": "キサナティック・X", "types": ["spell"], "civs": ["water"],
        "cost": 5, "mana": 1,
        "spell": [
            {"op": "choose", "select": {"zone": "bz", "owner": "any",
                                        "filter": {"types": ["creature"]}, "count": 2}, "as": "pair"},
            {"op": "tap", "select": {"ref": "pair"}},
            {"op": "force_battle", "a": {"ref": "pair"}},
        ],
    },
    {   # 権力のコイン: 自分か同名のタマシードが出た時、相手クリーチャーをタップし次の相手ターン開始時にアンタップさせない
        "id": "dm22rp1-054", "name": "権力のコイン", "types": ["tamaseed"], "civs": ["light"],
        "cost": 3, "mana": 1, "keywords": ["s_trigger"],
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [{"op": "tap", "select": {"zone": "bz", "owner": "opp",
                                                 "filter": {"types": ["creature"]}, "count": 1},
                         "no_untap_next": True}]},
            {"kind": "trigger",
             "when": {"event": "move", "to": "bz",
                      "subject": {"owner": "you", "other": True,
                                  "filter": {"types": ["tamaseed"], "name": "権力のコイン"}}},
             "effect": [{"op": "tap", "select": {"zone": "bz", "owner": "opp",
                                                 "filter": {"types": ["creature"]}, "count": 1},
                         "no_untap_next": True}]},
        ],
    },
    {   # 紅の猛り 天鎖: タップして出る／シールド6つ以下ならアンタップしない／ラビリンス
        "id": "dmex02-023", "name": "紅の猛り 天鎖", "types": ["creature"], "civs": ["light"],
        "cost": 2, "power": 14500, "races": ["メタリカ"], "mana": 1,
        "keywords": ["triple_breaker", "enters_tapped"],
        "abilities": [
            {"kind": "static", "affects": "self",
             "if": {"cmp": [{"count": {"zone": "shield", "owner": "you"}}, "<=", 6]},
             "mod": {"deny": ["untap_at_start"]}},
            {"kind": "trigger", "when": {"event": "turn_start", "player": "you"},
             "if": {"cmp": [{"count": {"zone": "shield", "owner": "you"}}, ">",
                            {"count": {"zone": "shield", "owner": "opp"}}]},
             "effect": [{"op": "may", "body": [{"op": "draw", "count": 1}]}]},
        ],
    },
    {   # 影世界のシクミ: 3枚落として、コスト3以下を墓地/手札から出し、次の自分のターン開始までブロッカーを与える
        "id": "dm23ex2-060", "name": "影世界のシクミ", "types": ["spell"],
        "civs": ["light", "darkness"], "cost": 4, "races": ["月光王国"], "mana": 1,
        "keywords": ["s_trigger"],
        "spell": [
            {"op": "move", "select": {"zone": "deck", "owner": "you", "from_top": 3},
             "to": "graveyard", "reason": "put"},
            {"op": "may", "body": [
                {"op": "play_free",
                 "select": {"zone": ["graveyard", "hand"], "owner": "you",
                            "filter": {"types": ["creature"], "cost_le": 3}, "count": 1},
                 "as": "summoned"},
                {"op": "modify", "select": {"ref": "summoned"}, "mod": {"grant": ["blocker"]},
                 "duration": "until_next_own_turn_start"},
            ]},
        ],
    },
    {   # ジェネラローズ（クリーチャー面）: 出た時1枚引き、進化ではない光コスト6以下を手札から出してもよい
        "id": "dm25ex1-036", "name": "赤薔薇の精霊龍 ジェネラローズ", "types": ["creature"],
        "civs": ["light"], "cost": 7, "power": 7500,
        "races": ["エンジェル・コマンド・ドラゴン", "革命軍"], "mana": 1,
        "keywords": ["double_breaker"],
        "abilities": [
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "draw", "count": 1},
                 {"op": "may", "body": [
                     {"op": "play_free",
                      "select": {"zone": "hand", "owner": "you",
                                 "filter": {"types": ["creature"], "not_types": ["evolution"],
                                            "civs": ["light"], "cost_le": 6}, "count": 1}}]},
             ]},
        ],
    },
    {   # ～銀眼の看守～: セイバー：進化クリーチャー（types に evolution を含むものが対象）
        "id": "dm25rp1-056", "name": "～銀眼の看守～", "types": ["creature"], "civs": ["light"],
        "cost": 2, "power": 4000, "races": ["グレートメカオー", "スチーム・ナイト"], "mana": 1,
        "keywords": ["blocker", "cannot_attack_player"],
        "abilities": [
            {"kind": "replace", "optional": True,
             "when": {"event": "move", "from": "bz", "to": "graveyard", "reason": "destroy",
                      "subject": {"owner": "you", "other": True, "filter": {"types": ["evolution"]}}},
             "instead": [{"op": "move", "select": {"ref": "self"}, "to": "graveyard",
                          "reason": "destroy"}]},
        ],
    },
    {   # 爆打者 猛トラック: 自分の火のクリーチャーがバトルに勝った時、1枚引いてもよい
        "id": "dmr13-061", "name": "爆打者 猛トラック", "types": ["creature"], "civs": ["fire"],
        "cost": 4, "power": 3000, "races": ["ヒューマノイド爆"], "mana": 1,
        "abilities": [
            {"kind": "trigger",
             "when": {"event": "battle_win",
                      "subject": {"owner": "you", "filter": {"civs": ["fire"]}}},
             "effect": [{"op": "may", "body": [{"op": "draw", "count": 1}]}]},
        ],
    },
    {   # 滅界の魔将バフォロメア: G・ストライク＋見せた時に-3000＋出た時このターン全体-3000
        "id": "dmrp17-003", "name": "滅界の魔将バフォロメア", "types": ["creature"],
        "civs": ["darkness"], "cost": 5, "power": 6000, "races": ["デーモン・コマンド"], "mana": 1,
        "keywords": ["g_strike", "double_breaker"],
        "abilities": [
            {"kind": "trigger", "zone": "hand",
             "when": {"event": "move", "from": "shield", "to": "hand", "subject": "self"},
             "effect": [
                 {"op": "choose", "select": {"zone": "bz", "owner": "opp",
                                             "filter": {"types": ["creature"]}, "count": 1},
                  "as": "tgt"},
                 {"op": "modify", "select": {"ref": "tgt"}, "mod": {"power": -3000}}]},
            {"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [
                 {"op": "modify", "select": {"zone": "bz", "owner": "opp", "count": "all"},
                  "mod": {"power": -3000}, "dynamic": True}]},
        ],
    },
]


@pytest.mark.parametrize("raw", CARDS, ids=[c["id"] for c in CARDS])
def test_representative_reject_now_parses(raw):
    cd = parse_card(raw, TABLES, where=raw["id"])
    assert cd.id == raw["id"]
