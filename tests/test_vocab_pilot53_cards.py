"""第53弾の実カード parse テスト: メテオバーン「攻撃できる時」形の4枚。

- dm23-s05 / promoy5-007 は「このクリーチャーが攻撃できる時」形（保持者ゲート）
- sp-015 / sp-016 は「自分のクリーチャーが攻撃できる時」形（any_attacker: true）
"""
import os

os.environ.setdefault("DMSIM_SKIP_CONVERTED", "1")

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

_TAP2 = {"op": "may", "body": [
    {"op": "tap", "select": {"zone": "bz", "owner": "opp",
                             "filter": {"types": ["creature"]}, "count": 2, "up_to": True}}]}

CARDS = [
    {
        "id": "dm23-s05",
        "name": "超神龍アルグロス・クリューソス",
        "types": ["creature", "evolution"],
        "civs": ["light"],
        "cost": 8,
        "power": 9500,
        "races": ["アポロニア・ドラゴン"],
        "evolve_from": {"races": ["ドラゴン"]},
        "mana": 1,
        "keywords": ["double_breaker"],
        "text": "進化-自分のドラゴン１体の上に置く。\nこのクリーチャーをバトルゾーンに出した時、バトルゾーンにある相手のクリーチャーを２体まで選び、タップしてもよい。\nメテオバーン-このクリーチャーが攻撃できる時、このクリーチャーの下にあるカードを１枚選び墓地に置いてもよい。そうした場合、バトルゾーンにある相手のクリーチャーを２体まで選び、タップしてもよい。\nW・ブレイカー",
        "abilities": [
            {"kind": "trigger",
             "when": {"event": "move", "to": "bz", "subject": "self"},
             "effect": [_TAP2]},
            {"kind": "activate",
             "cost": {"under": 1},
             "effect": [_TAP2]},
        ],
        "source": {"official": "dm23-s05", "review": "pending"},
    },
    {
        "id": "promoy5-007",
        "name": "炎竜凰シャイニング・ノヴァ",
        "types": ["creature", "evolution"],
        "civs": ["fire"],
        "cost": 7,
        "power": 8000,
        "races": ["ティラノ・ドレイク"],
        "evolve_from": {"races": ["ティラノ・ドレイク"]},
        "mana": 1,
        "keywords": ["double_breaker"],
        "text": "進化-自分のティラノ・ドレイク１体の上に置く。メテオバーン - このクリーチャーが攻撃できる時、このクリーチャーの下にあるカードを１枚選び墓地に置いてもよい。そうした場合、バトルゾーンにある相手のコスト５以下のカードを１枚選び、持ち主の墓地に置く。Ｗ・ブレイカー（このクリーチャーはシールドを２枚ブレイクする）",
        "abilities": [
            {"kind": "activate",
             "cost": {"under": 1},
             "effect": [
                 {"op": "move",
                  "select": {"zone": "bz", "owner": "opp",
                             "filter": {"cost_le": 5}, "count": 1},
                  "to": "graveyard", "reason": "destroy"}]},
        ],
        "source": {"official": "promoy5-007", "review": "pending"},
    },
    {
        "id": "sp-015",
        "name": "魔皇アゼルザード",
        "types": ["creature", "evolution"],
        "civs": ["darkness"],
        "cost": 6,
        "power": 9000,
        "races": ["グランド・デビル"],
        "evolve_from": {"races": ["グランド・デビル"]},
        "mana": 1,
        "keywords": ["double_breaker"],
        "text": "進化-自分のグランド・デビル１体の上に置く。\nメテオバーン-自分のクリーチャーが攻撃できる時、このクリーチャーの下にあるカードを１枚選び墓地に置いてもよい。そうした場合、相手のシールドを１枚選び、相手はそれを自分自身の手札に加える。(相手はその「S・トリガー」を使うことができる)\nW・ブレイカー",
        "abilities": [
            {"kind": "activate",
             "any_attacker": True,
             "cost": {"under": 1},
             "effect": [
                 {"op": "move",
                  "select": {"zone": "shield", "owner": "opp", "count": 1},
                  "to": "hand", "reason": "break"}]},
        ],
        "source": {"official": "sp-015", "review": "pending"},
    },
    {
        "id": "sp-016",
        "name": "聖帝ソルダリオス",
        "types": ["creature", "evolution"],
        "civs": ["nature"],
        "cost": 6,
        "power": 6000,
        "races": ["アーク・セラフィム"],
        "evolve_from": {"races": ["アーク・セラフィム"]},
        "mana": 1,
        "keywords": ["double_breaker"],
        "text": "進化-自分のアーク・セラフィム１体の上に置く。\nメテオバーン-自分のクリーチャーが攻撃できる時、このクリーチャーの下にあるカードを１枚選び墓地に置いてもよい。そうした場合、進化クリーチャーではないアーク・セラフィムまたはビーストフォーク１体を、自分のマナゾーンからバトルゾーンに出す。\nW・ブレイカー",
        "abilities": [
            {"kind": "activate",
             "any_attacker": True,
             "cost": {"under": 1},
             "effect": [
                 {"op": "move",
                  "select": {"zone": "mana", "owner": "you",
                             "filter": {"types": ["creature"], "evolution": False,
                                        "races": ["アーク・セラフィム", "ビーストフォーク"]},
                             "count": 1},
                  "to": "bz", "reason": "put"}]},
        ],
        "source": {"official": "sp-016", "review": "pending"},
    },
]


def test_pilot53_real_cards_parse():
    for c in CARDS:
        cd = parse_card(c, TABLES, where=c["id"])
        acts = [a for a in cd.abilities if a["kind"] == "activate"]
        assert len(acts) == 1 and acts[0]["cost"] == {"under": 1}
    by_id = {c["id"]: c for c in CARDS}
    assert by_id["sp-015"]["abilities"][0]["any_attacker"] is True
    assert "any_attacker" not in by_id["dm23-s05"]["abilities"][1]
