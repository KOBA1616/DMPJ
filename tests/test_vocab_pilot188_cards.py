"""語彙パイロット第188弾のカード側テスト（登録形）: ラウンド224の結果。

- 登録16件: converted.yaml にあり、敗北の防止／置換の節を持つ。
- 差し戻し1件: rejects に洗練した gap で残り、解けた節が partial にある。
- lose_replacement / lose_prevention 単独は解消（0件）。
"""
import json
from pathlib import Path

import yaml

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()
ROOT = Path(__file__).parent.parent

REGISTERED = [
    "dm25ex3-rp4s08", "dm26sd1-j008", "dmartkiwami02-003", "dm26sd1-l003",
    "dmex08-176", "dmex08-226", "dmex19-m39", "dmrp20-s04", "dm23rp1-022",
    "dm24ex3-rp1s07", "dmex08-256", "dmex15-b017", "dm24bd2-011",
    "dmex08-221", "dm25sd2-005", "dmrp08-s08",
]
BOUNCED = {
    "dmex08-003": ["reveal_top_cost_parity"],
}


def _converted():
    data = yaml.safe_load(
        (ROOT / "data" / "cards" / "converted.yaml").read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["cards"]}


def _rejects():
    return {json.loads(line)["id"]: json.loads(line) for line in
            (ROOT / "data" / "cards" / "raw" / "rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()}


def _has_lose(node):
    if isinstance(node, dict):
        if "no_lose" in node or node.get("op") == "no_lose":
            return True
        if (node.get("when") or {}).get("event") == "lose":
            return True
        return any(_has_lose(v) for v in node.values())
    if isinstance(node, list):
        return any(_has_lose(v) for v in node)
    return False


def _face(card, idx=0):
    faces = card.get("faces")
    if faces:
        return faces[idx]
    return card


def test_registered_have_lose_clauses():
    conv = _converted()
    for cid in REGISTERED:
        assert cid in conv, cid
        d = parse_card(conv[cid], TABLES)
        assert d.id == cid
        assert _has_lose(conv[cid]), cid


def test_registered_distinct_clauses():
    conv = _converted()
    # dm25ex3-rp4s08: シールド S・トリガー付与＋マナ置き置換。
    a = conv["dm25ex3-rp4s08"]["abilities"]
    assert any(x["kind"] == "static" and x.get("zone") == "shield"
               and (x.get("mod") or {}).get("grant") == ["s_trigger"]
               for x in a)
    rep = [x for x in a if x["kind"] == "replace"][0]
    assert rep["instead"] == [{"op": "move", "select": {"ref": "self"},
                               "to": "mana", "reason": "put"}]
    # dm26sd1-j008 / dmartkiwami02-003: 山札切れ防止＋空山札からの引く置換。
    for cid in ("dm26sd1-j008", "dmartkiwami02-003"):
        a = conv[cid]["abilities"]
        assert any(x["kind"] == "static"
                   and x.get("no_lose") == {"deck_out_only": True} for x in a)
        assert any(x["kind"] == "replace"
                   and (x.get("when") or {}).get("event") == "draw"
                   for x in a)
    # dm26sd1-l003: 破壊置換＋破壊時そのターン防止。
    a = conv["dm26sd1-l003"]["abilities"]
    rep = [x for x in a if x["kind"] == "replace"][0]
    assert rep["instead"] == [{"op": "move", "select": {"ref": "self"},
                               "to": "graveyard", "reason": "destroy"}]
    assert any(x["kind"] == "trigger"
               and (x.get("when") or {}).get("reason") == "destroy"
               and x["effect"] == [{"op": "no_lose", "player": "you",
                                    "duration": "end_of_turn"}]
               for x in a)
    # dmex08-176: 山札送り置換＋そのターン防止。
    # （破壊される時の身代わり破壊の replace もあるため when.event == lose で選ぶ）
    rep = [x for x in conv["dmex08-176"]["abilities"]
           if x["kind"] == "replace"
           and (x.get("when") or {}).get("event") == "lose"][0]
    assert [o["op"] for o in rep["instead"]] == ["move", "shuffle", "no_lose"]
    assert rep["instead"][0]["to"] == "deck"
    # dmex08-226: 攻撃による勝利の置換（reason: direct_attack）＋攻撃禁止＋遅延敗北。
    rep = [x for x in conv["dmex08-226"]["abilities"]
           if x["kind"] == "replace"][0]
    assert rep["when"] == {"event": "lose", "reason": "direct_attack"}
    assert rep["instead"][1] == {
        "op": "modify",
        "select": {"zone": "bz", "owner": "any",
                   "filter": {"types": ["creature"]}, "count": "all"},
        "mod": {"grant": ["cannot_attack"]}, "duration": "end_of_turn"}
    assert rep["instead"][2]["op"] == "delayed_trigger"
    assert "free_if" in conv["dmex08-226"]
    # dmex19-m39: マナ8枚の山札送り置換。
    rep = [x for x in conv["dmex19-m39"]["abilities"]
           if x["kind"] == "replace"][0]
    assert rep["instead"] == [{"op": "move",
                               "select": {"zone": "mana", "owner": "you",
                                          "count": 8},
                               "to": "deck", "position": "bottom",
                               "reason": "put", "order": "shuffle"}]
    # dmrp20-s04: シールド0枚の時だけ、進化でないクリーチャー2体破壊で置換。
    rep = [x for x in conv["dmrp20-s04"]["abilities"]
           if x["kind"] == "replace"][0]
    assert rep["if"] == {"cmp": [{"count": {"zone": "shield", "owner": "you"}},
                                "==", 0]}
    # dm23rp1-022: {x+} は stp_spell 形で一度だけ防止。
    assert conv["dm23rp1-022"]["stp_spell"] == [
        {"op": "no_lose", "player": "you",
         "duration": "end_of_turn", "once": True}]
    # dm24ex3-rp1s07: 敗北の2節はハイパー条件付き。
    a = conv["dm24ex3-rp1s07"]["abilities"]
    lose_abs = [x for x in a if x["kind"] == "replace"
                or (x.get("when") or {}).get("reason") == "destroy"]
    assert len(lose_abs) == 2
    assert all(x.get("if") == {"hyper": True} for x in lose_abs)
    # dmex08-256: 自分のターン中だけ防止＋ビートジョッキーは破壊されず。
    a = conv["dmex08-256"]["abilities"]
    assert any(x["kind"] == "static" and x.get("if") == {"is_turn": "you"}
               and x.get("no_lose") is True for x in a)
    assert any(x["kind"] == "static"
               and (x.get("mod") or {}).get("indestructible") is True
               for x in a)
    # dmex15-b017: 呪文全体。次の自分のターンのはじめまで防止。
    # （destroy はマクロのまま格納される。parse 時に move へ展開される）
    assert conv["dmex15-b017"]["spell"] == [
        {"op": "destroy",
         "select": {"zone": "bz", "owner": "opp",
                    "filter": {"types": ["creature"], "power_le": 14000},
                    "count": "all"}},
        {"op": "no_lose", "player": "you",
         "duration": "until_next_own_turn_start"}]
    # dm24bd2-011: {x+} の出た時誘発で、このターン誰も負けない。
    trig = [x for x in conv["dm24bd2-011"]["abilities"]
            if x.get("stp")][0]
    assert trig["effect"] == [{"op": "no_lose", "player": "each",
                               "duration": "end_of_turn"}]
    # dmex08-221: マナ武装9の常在防止。
    static = [x for x in conv["dmex08-221"]["abilities"]
              if x["kind"] == "static" and "no_lose" in x][0]
    assert static["no_lose"] is True
    assert static["if"] == {"cmp": [{"count": {"zone": "mana", "owner": "you",
                                               "filter": {"civs": ["light"]}}},
                                   ">=", 9]}
    # dm25sd2-005: {xB} の出た時誘発で、そのターン中防止。
    trig = [x for x in conv["dm25sd2-005"]["abilities"]
            if x.get("sst")][0]
    assert trig["effect"] == [{"op": "no_lose", "player": "you",
                               "duration": "end_of_turn"}]
    # dmrp08-s08: 呪文面。破壊してもよい。そうしたら次の自分のターンのはじめまで防止。
    sp = conv["dmrp08-s08"]["faces"][1]["spell"]
    assert sp == [{"op": "may",
                   "body": [{"op": "destroy",
                             "select": {"zone": "bz", "owner": "you",
                                        "filter": {"types": ["creature"]},
                                        "count": 1}},
                            {"op": "no_lose", "player": "you",
                             "duration": "until_next_own_turn_start"}]}]


def test_bounced_with_refined_gap():
    rej = _rejects()
    for cid, gaps in BOUNCED.items():
        assert cid in rej, cid
        assert rej[cid]["gaps"] == gaps, (cid, rej[cid]["gaps"])
        partial = rej[cid]["partial"]
        assert partial is not None, cid
        needs = [u["need"] for u in partial["source"]["unsupported"]]
        assert needs == gaps, (cid, needs)
    # dmex08-003: 手札10枚以上条件の static が partial に残る。
    a = rej["dmex08-003"]["partial"]["abilities"]
    assert len(a) == 1
    assert a[0]["kind"] == "static"
    assert a[0]["if"] == {"cmp": [{"count": {"zone": "hand", "owner": "you"}},
                                 ">=", 10]}
    assert a[0]["mod"] == {"power": 10000,
                           "grant": ["quad_breaker", "unblockable"]}
    # lose_replacement / lose_prevention 単独は解消。
    assert not [r for r in rej.values()
                if r.get("gaps") in (["lose_replacement"], ["lose_prevention"])]
