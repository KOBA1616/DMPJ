"""第172弾 recycle の再変換ラウンド208: 対象14件の生成と登録形の検証。

生成は rejects の partial に recycle 語彙（`recycle: {cost, civs?}`）を足す
決定的な変換。古典形（数字コスト ②/③/⑥/⑧）は呪文効果を公式テキストから
既存 idiom で組み立て、dm26rp2 の5枚は partial が既に持つアタック・チャンス
declare＋呪文効果に `[xx04]` 形（cost 6＋civs 2枚）を足す。
14件すべて新規登録（差し戻しなし）。recycle の単独ギャップは 0 残り。
"""
import copy
import json
import subprocess

import yaml

from dmsim.defs import load_tables, parse_card

ROOT = __import__("pathlib").Path(__file__).parent.parent
# reopen 前の rejects は第172弾コミットの親ツリーに残っている
PILOT_COMMIT = "57ef6a0"
TABLES = load_tables()

TARGETS = ["dmd24-033", "dmex03-068", "dmr16g-026", "dmr16g-026d", "dmr16g-034",
           "dmr16g-040", "dmr16g-040d", "dmr16g-049", "dmr16g-053",
           "dm26rp2-031", "dm26rp2-035", "dm26rp2-039", "dm26rp2-043", "dm26rp2-047"]
NOTES = "再変換ラウンド208。第172弾 recycle の再変換。"
NOTES_RP2 = NOTES + "アタック・チャンスは declare + play_free で変換済み。"


def _rows():
    out = subprocess.check_output(
        ["git", "show", f"{PILOT_COMMIT}:data/cards/raw/rejects.jsonl"],
        cwd=ROOT, text=True)
    return {json.loads(line)["id"]: json.loads(line)
            for line in out.splitlines() if line.strip()}


def _move_top(n):
    return [{"op": "move", "select": {"zone": "deck", "owner": "you", "from_top": n},
             "to": "mana", "reason": "put"}]


def _mod_power(n):
    return [{"op": "modify",
             "select": {"zone": "bz", "owner": "opp",
                        "filter": {"types": ["creature"]}, "count": 1},
             "mod": {"power": n}, "duration": "end_of_turn"}]


# 古典形9枚: (呪文効果, recycle)
SPEC = {
    "dmd24-033": ([{"op": "draw", "count": 1}], {"cost": 3}),
    "dmex03-068": (_move_top(2), {"cost": 8}),
    "dmr16g-026": (_mod_power(-6000), {"cost": 6}),
    "dmr16g-026d": (_mod_power(-6000), {"cost": 6}),
    "dmr16g-034": ([{"op": "tap", "select": {"zone": "bz", "owner": "opp",
                     "filter": {"types": ["creature"]}, "count": 2, "up_to": True}}],
                  {"cost": 3}),
    "dmr16g-040": ([{"op": "draw", "count": 1}], {"cost": 3}),
    "dmr16g-040d": ([{"op": "draw", "count": 1}], {"cost": 3}),
    "dmr16g-049": ([{"op": "destroy", "select": {"zone": "bz", "owner": "opp",
                     "filter": {"types": ["creature"], "keyword": "blocker"},
                     "count": 1}}], {"cost": 2}),
    "dmr16g-053": (_move_top(2), {"cost": 8}),
}
CIVS_RP2 = {"dm26rp2-031": ["light", "light"], "dm26rp2-035": ["water", "water"],
            "dm26rp2-039": ["darkness", "darkness"], "dm26rp2-043": ["fire", "fire"],
            "dm26rp2-047": ["nature", "nature"]}


def build():
    rows = _rows()
    cards = []
    for cid in TARGETS:
        row = rows[cid]
        p = copy.deepcopy(row["partial"])
        if cid in SPEC:
            spell, rec = SPEC[cid]
            card = {"id": p["id"], "name": p["name"], "types": p["types"],
                    "civs": p["civs"], "cost": p["cost"], "mana": p["mana"],
                    "spell": copy.deepcopy(spell), "recycle": copy.deepcopy(rec),
                    "text": row["text"],
                    "source": {"official": p["id"], "review": "pending",
                               "notes": NOTES, "unsupported": []}}
        else:
            card = {"id": p["id"], "name": p["name"], "types": p["types"],
                    "civs": p["civs"], "cost": p["cost"], "mana": p["mana"],
                    "abilities": copy.deepcopy(p["abilities"]),
                    "spell": copy.deepcopy(p["spell"]),
                    "recycle": {"cost": 6, "civs": CIVS_RP2[cid]},
                    "text": row["text"],
                    "source": {"official": p["id"], "review": "pending",
                               "notes": NOTES_RP2, "unsupported": []}}
            if "aliases" in p.get("source", {}):
                card["source"]["aliases"] = list(p["source"]["aliases"])
        cards.append(card)
    return {"cards": cards}


def test_build_forms_parse():
    built = build()["cards"]
    assert len(built) == len(TARGETS)
    for card in built:
        parse_card(card, TABLES)


def test_registered_forms():
    built = {c["id"]: c for c in build()["cards"]}
    conv = {c["id"]: c for c in yaml.safe_load(open(ROOT / "data/cards/converted.yaml"))["cards"]}
    for cid in TARGETS:
        assert cid in conv, cid
        assert conv[cid] == built[cid], cid
    # 形の要点だけ確認する（詳細な挙動は test_vocab_pilot172.py の proto で検証済み）
    assert conv["dmd24-033"]["recycle"] == {"cost": 3}
    assert conv["dmd24-033"]["spell"] == [{"op": "draw", "count": 1}]
    assert conv["dmex03-068"]["recycle"] == {"cost": 8}
    assert conv["dmex03-068"]["spell"][0]["select"]["from_top"] == 2
    assert conv["dmr16g-026"]["spell"][0]["mod"] == {"power": -6000}
    assert conv["dmr16g-026"]["spell"][0]["duration"] == "end_of_turn"
    assert conv["dmr16g-034"]["spell"][0]["select"]["up_to"] is True
    assert conv["dmr16g-034"]["spell"][0]["select"]["count"] == 2
    assert conv["dmr16g-049"]["spell"][0]["select"]["filter"]["keyword"] == "blocker"
    assert conv["dm26rp2-031"]["recycle"] == {"cost": 6, "civs": ["light", "light"]}
    assert conv["dm26rp2-035"]["recycle"] == {"cost": 6, "civs": ["water", "water"]}
    assert conv["dm26rp2-035"]["source"]["aliases"] == ["promoy25-048"]
    assert conv["dm26rp2-039"]["recycle"] == {"cost": 6, "civs": ["darkness", "darkness"]}
    assert conv["dm26rp2-043"]["recycle"] == {"cost": 6, "civs": ["fire", "fire"]}
    assert conv["dm26rp2-047"]["recycle"] == {"cost": 6, "civs": ["nature", "nature"]}
    for cid in ("dm26rp2-031", "dm26rp2-035", "dm26rp2-039", "dm26rp2-043", "dm26rp2-047"):
        assert conv[cid]["abilities"][0]["kind"] == "declare"
        assert conv[cid]["abilities"][0]["effect"][0]["op"] == "play_free"


def test_round208_not_in_rejects():
    rows = [json.loads(line) for line in open(ROOT / "data/cards/raw/rejects.jsonl")
            if line.strip()]
    ids = {r["id"] for r in rows}
    for cid in TARGETS:
        assert cid not in ids, cid
