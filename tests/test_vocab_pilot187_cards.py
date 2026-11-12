"""語彙パイロット第187弾のカード側テスト（登録形）: ラウンド223の結果。

- 登録8件: converted.yaml にあり、クリーチャー面にフレンド・バースト誘発を持つ。
- 差し戻し1件: rejects に洗練した gap で残り、解けた節が partial にある。
- friend_burst 単独は解消（0件）。
"""
import json
from pathlib import Path

import yaml

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()
ROOT = Path(__file__).parent.parent

REGISTERED = [
    "dm23ex2-040", "dm23rp2x-009", "dm23rp2x-016", "dm23rp2x-020",
    "dm23rp2x-023", "dm23rp2x-057", "dm24ex4-095", "dm26sd1-i009",
]
BOUNCED = {
    "dm25ex4-036": ["hyperdimensional_summon"],
}

RACE_X = {
    "dm23ex2-040": "スノーフェアリー",
    "dm23rp2x-009": "メカ",
    "dm23rp2x-016": "アビス",
    "dm23rp2x-020": "アーマード",
    "dm23rp2x-023": "ジャイアント",
    "dm23rp2x-057": "マジック",
    "dm24ex4-095": "スノーフェアリー",
    "dm25ex4-036": "メカ",
    "dm26sd1-i009": "マジック",
}


def _converted():
    data = yaml.safe_load(
        (ROOT / "data" / "cards" / "converted.yaml").read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["cards"]}


def _rejects():
    return {json.loads(line)["id"]: json.loads(line) for line in
            (ROOT / "data" / "cards" / "raw" / "rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()}


def _fb_trigger(face, race):
    for a in face.get("abilities") or []:
        if a.get("kind") != "trigger":
            continue
        w = a.get("when") or {}
        if w.get("event") != "move" or w.get("to") != "bz":
            continue
        eff = a.get("effect") or []
        if not eff or eff[0].get("op") != "if":
            continue
        cond = str(eff[0].get("cond") or {})
        body = str((eff[0].get("then") or [{}])[0])
        if race in cond and "cast_face" in body:
            return a
    return None


def test_registered_have_friend_burst():
    conv = _converted()
    for cid in REGISTERED:
        assert cid in conv, cid
        d = parse_card(conv[cid], TABLES)
        assert d.id == cid
        faces = conv[cid]["faces"]
        assert len(faces) == 2, cid
        assert _fb_trigger(faces[0], RACE_X[cid]) is not None, cid


def test_registered_distinct_clauses():
    conv = _converted()
    # dm23ex2-040: 召喚コスト-2＋呪文面は墓地出し＋スピードアタッカー。
    f0 = conv["dm23ex2-040"]["faces"][0]
    assert any(a["kind"] == "static" and a.get("affects", {}).get("zone") == "hand"
               and (a.get("mod") or {}).get("cost") == -2
               for a in f0["abilities"])
    sp = conv["dm23ex2-040"]["faces"][1]["spell"]
    assert sp[0]["op"] == "play_free" and sp[0].get("as") == "sf"
    assert sp[1] == {"op": "modify", "select": {"ref": "sf"},
                     "mod": {"grant": ["speed_attacker"]},
                     "duration": "end_of_turn"}
    # dm23rp2x-009: ブロッカー＋W・ブレイカー、呪文面は repeat＋modal。
    f0 = conv["dm23rp2x-009"]["faces"][0]
    assert f0["keywords"] == ["blocker", "double_breaker"]
    sp = conv["dm23rp2x-009"]["faces"][1]["spell"]
    assert sp[0]["op"] == "repeat"
    assert sp[0]["body"][0]["op"] == "modal"
    assert len(sp[0]["body"][0]["modes"]) == 2
    # dm23rp2x-016: 破壊時ドロー（owner: any）＋呪文面はパワー-6000。
    f0 = conv["dm23rp2x-016"]["faces"][0]
    assert any(a["kind"] == "trigger"
               and (a.get("when") or {}).get("reason") == "destroy"
               and (a.get("when") or {}).get("subject", {}).get("owner") == "any"
               for a in f0["abilities"])
    sp = conv["dm23rp2x-016"]["faces"][1]["spell"]
    assert sp[0]["op"] == "modify" and sp[0]["mod"] == {"power": -6000}
    assert sp[0]["duration"] == "end_of_turn"
    # dm23rp2x-020: 他のファイアー・バード+2000、呪文面は1捨て2ドロー。
    f0 = conv["dm23rp2x-020"]["faces"][0]
    assert any(a["kind"] == "static"
               and (a.get("mod") or {}).get("power") == 2000
               and a.get("affects", {}).get("other") is True
               for a in f0["abilities"])
    sp = conv["dm23rp2x-020"]["faces"][1]["spell"]
    assert [o["op"] for o in sp] == ["discard", "draw"]
    assert sp[1]["count"] == 2
    # dm23rp2x-023: バトル勝利時1ドロー＋1ブレイク、呪文面は+4000＋バトル。
    f0 = conv["dm23rp2x-023"]["faces"][0]
    assert any(a["kind"] == "trigger"
               and (a.get("when") or {}).get("event") == "battle_win"
               and [o["op"] for o in a["effect"]] == ["draw", "break"]
               for a in f0["abilities"])
    sp = conv["dm23rp2x-023"]["faces"][1]["spell"]
    assert [o["op"] for o in sp] == ["choose", "modify", "may"]
    assert sp[2]["body"][0]["op"] == "force_battle"
    # dm23rp2x-057: 呪文面は3ドロー。
    sp = conv["dm23rp2x-057"]["faces"][1]["spell"]
    assert sp == [{"op": "draw", "count": 3}]
    # dm24ex4-095: 呪文面はS・トリガー＋マナへ2回。
    f1 = conv["dm24ex4-095"]["faces"][1]
    assert f1["keywords"] == ["s_trigger"]
    assert [o["op"] for o in f1["spell"]] == ["move", "move"]
    assert all(o["to"] == "mana" for o in f1["spell"])
    assert f1["spell"][0]["select"]["filter"] == {"types": ["creature"],
                                                  "tapped": False}
    # dm26sd1-i009: 2枚目以降ドロー時ドロー＋呪文面はエレメント2つまで手札へ。
    f0 = conv["dm26sd1-i009"]["faces"][0]
    assert any(a["kind"] == "trigger"
               and (a.get("when") or {}).get("event") == "draw"
               and (a.get("when") or {}).get("ord") == {"kind": "draw", "ge": 2}
               and a.get("if") == {"is_turn": "opp"}
               for a in f0["abilities"])
    sp = conv["dm26sd1-i009"]["faces"][1]["spell"]
    assert sp[0]["op"] == "move" and sp[0]["to"] == "hand"
    assert sp[0]["select"]["count"] == 2 and sp[0]["select"]["up_to"] is True


def test_bounced_with_refined_gap():
    rej = _rejects()
    for cid, gaps in BOUNCED.items():
        assert cid in rej, cid
        assert rej[cid]["gaps"] == gaps, (cid, rej[cid]["gaps"])
        partial = rej[cid]["partial"]
        assert partial is not None, cid
        assert _fb_trigger(partial["faces"][0], RACE_X[cid]) is not None, cid
        needs = [u["need"] for u in partial["source"]["unsupported"]]
        assert needs == gaps, (cid, needs)
    # dm25ex4-036: S・トリガーがクリーチャー面の keywords に残る。
    assert rej["dm25ex4-036"]["partial"]["faces"][0]["keywords"] == ["s_trigger"]
    # friend_burst 単独は解消。
    assert not [r for r in rej.values() if r.get("gaps") == ["friend_burst"]]
