"""語彙パイロット第182弾のカード側テスト（登録形）: ラウンド218で登録した
play_restriction 7件が converted.yaml にあり parse が通ること。差し戻した
4件は rejects に残り、洗練したギャップ名を持ち、解けた節を partial に残すこと。
"""
import json
from pathlib import Path

import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()
ROOT = Path(__file__).parent.parent

REGISTERED = [
    "dm25bd2-006", "dm25ex3-rp2tr3", "dm26ex2-001", "dm26ex4-035",
    "dm26ex4-sec006", "dm26rp1-std004", "dmpcd01-t01",
]

BOUNCED = {
    "dm26ex2-036": ["play_restriction_origin_zone"],
    "dmex08-128": ["play_restriction_break_and_deck"],
    "dmex12-s05": ["hyperdimensional_zone"],
    "dmrp18-a12": ["play_restriction_non_summon_entry"],
}


def _converted():
    data = yaml.safe_load(
        (ROOT / "data" / "cards" / "converted.yaml").read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["cards"]}


def _rejects():
    return {json.loads(line)["id"]: json.loads(line) for line in
            (ROOT / "data" / "cards" / "raw" / "rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()}


def _deny_static(card, owner, deny):
    """指定の owner・deny を持つ実行制限の常在型を返す。"""
    for a in card.get("abilities") or []:
        if (a["kind"] == "static" and a.get("mod", {}).get("deny") == deny
                and a.get("affects", {}).get("owner") == owner):
            return a
    raise AssertionError(f"deny static not found: {card['id']} {owner} {deny}")


def test_play_restriction_cards_registered():
    conv = _converted()
    for cid in REGISTERED:
        assert cid in conv, cid
        d = parse_card(conv[cid], TABLES)
        assert d.id == cid
    # dm25bd2-006: 手札枚数 cap の実行制限＋相手の実行時2ドロー
    c = conv["dm25bd2-006"]
    st = _deny_static(c, "opp", ["summon", "cast"])
    assert st["affects"]["filter"]["cost_le"] == {
        "count": {"zone": "hand", "owner": "opp"}}
    trigs = [a for a in c["abilities"] if a["kind"] == "trigger"]
    assert {t["when"]["event"] for t in trigs} == {"summon", "cast"}
    assert all(t["when"].get("player") == "opp"
               and t["effect"] == [{"op": "draw", "count": 2}] for t in trigs)
    # dm25ex3-rp2tr3 / dmpcd01-t01: 光以外の実行禁止
    for cid in ("dm25ex3-rp2tr3", "dmpcd01-t01"):
        st = _deny_static(conv[cid], "any", ["summon", "cast"])
        assert st["affects"]["filter"] == {
            "types": ["creature", "spell"], "not_civs": ["light"]}
    # dm26ex2-001: bzのクリーチャー全員につき1軽減（下限1）＋CIPバウンス＋次ターン制限
    c = conv["dm26ex2-001"]
    cost = next(a for a in c["abilities"]
                if a["kind"] == "static" and "cost" in a.get("mod", {}))
    assert cost["mod"]["cost"] == {
        "amount": -1,
        "count": {"zone": "bz", "owner": "any",
                  "filter": {"types": ["creature"]}}}
    assert cost["mod"]["cost_min"] == 1
    cip = next(a for a in c["abilities"]
               if a["kind"] == "trigger"
               and a["when"] == {"event": "move", "to": "bz", "subject": "self"}
               and any(e["op"] == "move" for e in a["effect"]))
    assert any(e["op"] == "modify"
               and e["mod"] == {"deny": ["summon", "enter_bz"]}
               for e in cip["effect"])
    # dm26ex4-035 / dm26ex4-sec006: CIPで4枚までマナ＋自ターン中の多色でない禁止＋ターン終了時マナ→手札
    for cid in ("dm26ex4-035", "dm26ex4-sec006"):
        c = conv[cid]
        assert c["keywords"] == ["ex_life", "blocker", "double_breaker"]
        cip = next(a for a in c["abilities"]
                   if a["kind"] == "trigger"
                   and a["when"] == {"event": "move", "to": "bz", "subject": "self"})
        s = json.dumps(cip, ensure_ascii=False)
        assert '"times": 4' in s and '"from_top": 1' in s and '"to": "mana"' in s
        st = _deny_static(c, "opp", ["summon", "enter_bz"])
        assert st["if"] == {"is_turn": "you"}
        assert st["affects"]["filter"] == {
            "types": ["creature"], "multicolor": False}
        assert any(a["kind"] == "trigger"
                   and a.get("when") == {"event": "turn_end", "player": "you"}
                   and a["effect"] == [{"op": "move",
                                        "select": {"zone": "mana", "owner": "you", "count": 1},
                                        "to": "hand", "reason": "return"}]
                   for a in c["abilities"])
    # dm26rp1-std004: マナの光/火5枚以上でコスト-3＋CIP破壊（自パワーより小さい）＋次ターン1体制限
    c = conv["dm26rp1-std004"]
    cost = next(a for a in c["abilities"]
                if a["kind"] == "static" and a.get("mod") == {"cost": -3})
    assert cost["if"]["cmp"][1] == ">="
    assert cost["if"]["cmp"][2] == 5
    assert "light" in json.dumps(cost["if"], ensure_ascii=False)
    cip = next(a for a in c["abilities"]
               if a["kind"] == "trigger"
               and a["when"] == {"event": "move", "to": "bz", "subject": "self"})
    s = json.dumps(cip, ensure_ascii=False)
    assert '"power_of": {"ref": "self"}' in s
    assert '"max_per_turn": 1' in s and '"count": "enter"' in s


def test_play_restriction_bounced_cards_keep_refined_gaps():
    rej = _rejects()
    for cid, gaps in BOUNCED.items():
        assert cid in rej, cid
        assert rej[cid]["gaps"] == gaps, (cid, rej[cid]["gaps"])
        partial = rej[cid]["partial"]
        assert partial["id"] == cid
        assert partial["source"]["unsupported"][0]["need"] == gaps[0]
    # dmex08-128: S・トリガー禁止節が partial に残っている
    p = rej["dmex08-128"]["partial"]
    st = _deny_static(p, "you", ["s_trigger"])
    assert st["affects"] == {"zone": "shield", "owner": "you"}
