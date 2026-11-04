"""第54弾の実カード parse テスト: ビビッドロー使用を検出する3経路。

- dmrp16-054 回転者 シャッセロアー: when の vivid 印（召喚イベント／詠唱イベント）
- dmex14-018 「空が真っ赤に燃え尽きる！」: 解決 env の vivid_paid 条件分岐
（filter の vividraw 所持判定は test_vocab_pilot54.py の T151 で動作確認済み）
"""
import os

os.environ.setdefault("DMSIM_SKIP_CONVERTED", "1")

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARDS = [
    {
        "id": "dmrp16-054",
        "name": "回転者 シャッセロアー",
        "types": ["creature"],
        "civs": ["water", "fire"],
        "cost": 3,
        "power": 4000,
        "races": ["ムートピア", "美孔麗王国"],
        "mana": 1,
        "text": "自分のクリーチャーを「ビビッドロー」能力を使って召喚した時、このターン、そのクリーチャーに「スピードアタッカー」を与える。（「スピードアタッカー」を持つクリーチャーは召喚酔いしない）\n自分の呪文を「ビビッドロー」能力を使って唱えた時、カードを１枚引く。",
        "abilities": [
            {"kind": "trigger",
             "when": {"event": "move", "to": "bz", "reason": "summon", "vivid": True,
                      "subject": {"owner": "you", "filter": {"types": ["creature"]}}},
             "effect": [
                 {"op": "modify", "select": {"ref": "subject"},
                  "mod": {"grant": ["speed_attacker"]}, "duration": "end_of_turn"}]},
            {"kind": "trigger",
             "when": {"event": "cast", "vivid": True, "player": "you"},
             "effect": [{"op": "draw", "count": 1}]},
        ],
        "source": {"official": "dmrp16-054", "review": "pending"},
    },
    {
        "id": "dmex14-018",
        "name": "「空が真っ赤に燃え尽きる！」",
        "types": ["spell"],
        "civs": ["fire"],
        "cost": 4,
        "races": ["美孔麗王国"],
        "mana": 1,
        "keywords": ["s_trigger"],
        "vividraw": {"cost": 6, "civs": ["fire"]},
        "text": "ビビッドロー [ff06] （自分のターン中、攻撃の前にこの呪文をドローした時、表向きにしてもよい。そうしたら、このターンこの呪文を[ff06] 支払って唱えてもよい）\nS・トリガー（この呪文をシールドゾーンから手札に加える時、コストを支払わずにすぐ唱えてもよい）\n相手のパワー5000以下のクリーチャーを１体破壊する。\nこの呪文を「ビビッドロー」能力を使って唱えていれば、相手のパワー6000以下のクリーチャーをすべて破壊する。",
        "spell": [
            {"op": "if",
             "cond": {"vivid_paid": True},
             "then": [
                 {"op": "destroy",
                  "select": {"zone": "bz", "owner": "opp",
                             "filter": {"types": ["creature"], "power_le": 6000}}}],
             "else": [
                 {"op": "destroy",
                  "select": {"zone": "bz", "owner": "opp",
                             "filter": {"types": ["creature"], "power_le": 5000},
                             "count": 1}}]},
        ],
        "source": {"official": "dmex14-018", "review": "pending"},
    },
]


def test_pilot54_real_cards_parse():
    for c in CARDS:
        parse_card(c, TABLES, where=c["id"])
    shasse = CARDS[0]
    assert shasse["abilities"][0]["when"]["vivid"] is True
    assert shasse["abilities"][1]["when"]["event"] == "cast"
