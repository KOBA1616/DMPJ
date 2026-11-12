"""語彙パイロット第185弾のカード側テスト（登録形）: ラウンド221で登録した
break_bonus 10件が converted.yaml にあり parse が通ること。
差し戻しは0件（break_bonus ギャップは全消し）。3件の「シールドをさらに
1枚ブレイクする」は既存の breaks_add 1 で表現した（dmr19-047 / dmd11-009型）。
"""
import json
from pathlib import Path

import yaml

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()
ROOT = Path(__file__).parent.parent

REGISTERED = [
    "dm33-004", "dm33-010", "dm33-010hc", "dm33-025", "dm33-034",
    "dm33-s03", "dmc64-037",
    "dmrp08-051", "dm24ex3-rp3s07", "dmr12-048",
]

BREAK_BONUS = REGISTERED[:7]

ALIASES = {
    "dm33-025": ["dm33-025hc"],
    "dmc64-037": ["dm33-032", "dm33-032hc"],
    "dmrp08-051": ["promoy17-102"],
    "dm24ex3-rp3s07": ["dm24ex3-rp3sec08", "dm24rp3-s07", "dm24rp3-sec008"],
    "dmr12-048": ["dmr12-048m"],
}


def _converted():
    data = yaml.safe_load(
        (ROOT / "data" / "cards" / "converted.yaml").read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["cards"]}


def _rejects():
    return {json.loads(line)["id"]: json.loads(line) for line in
            (ROOT / "data" / "cards" / "raw" / "rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()}


def _bonus_trigger(card):
    trigs = [a for a in card["abilities"]
             if a["kind"] == "trigger"
             and a["when"] == {"event": "attack_end", "subject": "self",
                               "broke": True}]
    assert len(trigs) == 1, card["id"]
    rep = trigs[0]["effect"][0]
    assert rep["op"] == "repeat"
    assert rep["times"] == {"turn_count": {"kind": "broke_by_self_attack"}}
    assert len(rep["body"]) == 1 and rep["body"][0]["op"] == "may"
    return rep["body"][0]["body"]


def test_break_bonus_cards_registered():
    conv = _converted()
    for cid in REGISTERED:
        assert cid in conv, cid
        d = parse_card(conv[cid], TABLES)
        assert d.id == cid
        if cid in ALIASES:
            assert conv[cid]["source"].get("aliases") == ALIASES[cid], cid

    # dm33-004: 進化＋相手パワー7000以下を1体破壊。
    c = conv["dm33-004"]
    assert c["types"] == ["creature", "evolution"]
    assert c["evolve_from"] == {"races": ["アーマード・ドラゴン", "オリジン"]}
    body = _bonus_trigger(c)
    assert body == [{"op": "destroy",
                     "select": {"zone": "bz", "owner": "opp",
                                "filter": {"types": ["creature"], "power_le": 7000},
                                "count": 1}}]

    # dm33-010 / dm33-010hc: 自分の他のクリーチャー1体破壊→reveal_until（破壊数）。
    for cid in ("dm33-010", "dm33-010hc"):
        c = conv[cid]
        assert c["types"] == ["creature", "evolution"]
        assert c["evolve_from"] == {"any_of": [{"race_has": "サイバー"},
                                               {"races": ["オリジン"]}]}
        body = _bonus_trigger(c)
        assert body[0]["op"] == "destroy" and body[0]["as"] == "d"
        assert body[0]["select"]["owner"] == "you"
        assert body[1] == {"op": "reveal_until", "filter": {"types": ["creature"]},
                           "count": {"var": "d"}, "as": "hit", "rest_as": "rest"}
        assert body[2]["op"] == "may" and body[3]["op"] == "move"
        assert body[3]["to"] == "deck" and body[4] == {"op": "shuffle", "player": "you"}

    # dm33-025: 相手は山札の上から4枚を墓地に置く。
    body = _bonus_trigger(conv["dm33-025"])
    assert body == [{"op": "mill", "owner": "opp", "count": 4}]

    # dm33-034: 自分の山札の上から2枚をマナゾーンに置く。
    body = _bonus_trigger(conv["dm33-034"])
    assert body == [{"op": "move",
                     "select": {"zone": "deck", "owner": "you",
                                "from_top": 2, "count": "all"},
                     "to": "mana", "reason": "put"}]

    # dm33-s03: 相手の手札を1枚見ないで選び、捨てさせる。
    c = conv["dm33-s03"]
    assert c["evolve_from"] == {"races": ["デーモン・コマンド"]}
    body = _bonus_trigger(c)
    assert body[0]["op"] == "choose"
    assert body[0]["select"]["chooser"] == "random"
    assert body[0]["select"]["zone"] == "hand" and body[0]["select"]["owner"] == "opp"
    assert body[1] == {"op": "move", "select": {"ref": "d", "count": "all"},
                       "to": "graveyard", "reason": "discard"}

    # dmc64-037: 山札の上から1枚目を見せる。ファイアー・バードなら出してもよい。
    body = _bonus_trigger(conv["dmc64-037"])
    assert body[0] == {"op": "reveal_until",
                       "filter": {"types": ["creature"], "races": ["ファイアー・バード"]},
                       "count": 1, "limit": 1, "as": "hit", "rest_as": "rest"}
    assert body[1]["op"] == "may" and body[2]["to"] == "graveyard"

    # dmrp08-051: 呪文面はアンタップ自クリーチャー1体へ power+5000 & breaks_add 1。
    c = conv["dmrp08-051"]
    assert c["faces"][0]["keywords"] == ["s_trigger"]
    assert any(op.get("op") == "cast_face"
               for a in c["faces"][0]["abilities"]
               for op in a["effect"][0]["body"])
    spell = c["faces"][1]["spell"]
    assert spell == [{"op": "modify",
                      "select": {"zone": "bz", "owner": "you",
                                 "filter": {"types": ["creature"], "tapped": False},
                                 "count": 1},
                      "mod": {"power": 5000, "breaks_add": 1},
                      "duration": "end_of_turn"}]

    # dm24ex3-rp3s07: 攻撃トリガーはアンタップ＋breaks_add 1（このターン）。
    c = conv["dm24ex3-rp3s07"]
    assert c["keywords"] == ["hyper_energy", "speed_attacker", "double_breaker"]
    trig = c["abilities"][0]
    assert trig["when"] == {"event": "attack", "subject": "self"}
    assert trig["effect"][1] == {"op": "untap", "select": {"ref": "t"}}
    assert trig["effect"][2] == {"op": "modify", "select": {"ref": "t"},
                                 "mod": {"breaks_add": 1}, "duration": "end_of_turn"}
    assert c["abilities"][1]["kind"] == "replace"
    assert c["abilities"][1]["once_per_turn"] is True

    # dmr12-048: 全体付与 static の mod に breaks_add 1（dmd11-009型）。
    c = conv["dmr12-048"]
    grant = c["abilities"][0]
    assert grant["kind"] == "static"
    assert grant["mod"]["breaks_add"] == 1
    assert grant["mod"]["gain"][0]["mod"] == {
        "power_when": {"amount": 2000, "when": "attacking"}}
    assert any(a["kind"] == "trigger"
               and a["when"].get("reason") == "destroy"
               for a in c["abilities"])
    assert sum(1 for a in c["abilities"]
               if a["kind"] == "static"
               and a.get("mod", {}).get("deny") == ["enter_bz"]) == 5


def test_break_bonus_gap_fully_cleared():
    rej = _rejects()
    assert not any("break_bonus" in r.get("gaps", []) for r in rej.values())
    for cid in REGISTERED:
        assert cid not in rej, cid
