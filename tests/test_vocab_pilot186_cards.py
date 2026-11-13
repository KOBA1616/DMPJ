"""語彙パイロット第186弾のカード側テスト（登録形）: ラウンド222の結果。

- 登録7件: converted.yaml にあり、スーパーガードマンの置換能力を持つ。
- 差し戻し3件: rejects に洗練した gap で残り、解けた節が partial にある。
"""
import json
from pathlib import Path

import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()
ROOT = Path(__file__).parent.parent

REGISTERED = [
    "dm26rp2-046", "dm26rp2-069", "dm26rp2-073", "dm26rp3-041",
    "dm26rp3-s009", "dm26rp3-sec010", "dm26rp2-s008",
]
BOUNCED = {
    "dm26ex3-088": ["choose_restriction"],
    "dm26rp2-027": ["ignore_cannot_attack_abilities"],
    "dm26rp3-010": ["cip_reuse", "play_limit"],
}

GUARDMAN = {
    "kind": "replace",
    "when": {"event": "battle",
             "subject": {"owner": "you", "filter": {"types": ["creature"]},
                         "other": True}},
    "instead": [{"op": "battle_substitute", "tap": True}],
}


def _converted():
    data = yaml.safe_load(
        (ROOT / "data" / "cards" / "converted.yaml").read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["cards"]}


def _rejects():
    return {json.loads(line)["id"]: json.loads(line) for line in
            (ROOT / "data" / "cards" / "raw" / "rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()}


def _has_guardman(card):
    return any(
        a.get("kind") == "replace"
        and a.get("when", {}).get("event") == "battle"
        and a.get("instead") == [{"op": "battle_substitute", "tap": True}]
        for a in card.get("abilities") or [])


def test_registered_have_guardman():
    conv = _converted()
    for cid in REGISTERED:
        assert cid in conv, cid
        assert _has_guardman(conv[cid]), cid
        d = parse_card(conv[cid], TABLES)
        assert d.id == cid
        guard = [a for a in d.abilities
                 if a["kind"] == "replace"
                 and a["when"].get("event") == "battle"]
        assert len(guard) == 1, cid
        assert guard[0]["instead"] == [{"op": "battle_substitute", "tap": True}]


def test_registered_distinct_clauses():
    conv = _converted()
    # dm26rp2-046: 手札以外からの出現で force_battle。
    abs46 = conv["dm26rp2-046"]["abilities"]
    fb = [a for a in abs46 if a["kind"] == "trigger"
          and a.get("when", {}).get("from") == ["graveyard", "mana", "deck", "shield"]]
    assert len(fb) == 1
    assert fb[0]["effect"][0]["body"][0]["op"] == "force_battle"
    # dm26rp2-069: 条件つき攻撃不可（turn_count）。
    abs69 = conv["dm26rp2-069"]["abilities"]
    assert any(a["kind"] == "static" and "turn_count" in str(a.get("if", {}))
               and a.get("mod", {}).get("deny") == ["attack_player", "attack_creature"]
               for a in abs69)
    # dm26rp2-073: シンパシー（partial）＋置換。
    abs73 = conv["dm26rp2-073"]["abilities"]
    assert any(a["kind"] == "static" and a.get("zone") == "hand"
               and "cost" in (a.get("mod") or {}) for a in abs73)
    # dm26rp3-041: CIP の1ブレイク。
    abs41 = conv["dm26rp3-041"]["abilities"]
    assert any(a["kind"] == "trigger"
               and a.get("effect") == [{"op": "break", "player": "opp", "count": 1}]
               for a in abs41)
    # dm26rp3-s009 / sec010: 初回攻撃時アンタップ＋攻撃時ドロー・コスト比較出し。
    for cid in ("dm26rp3-s009", "dm26rp3-sec010"):
        ab = conv[cid]["abilities"]
        assert any(a["kind"] == "trigger"
                   and a.get("when", {}).get("event") == "attack_end"
                   for a in ab), cid
        atk = [a for a in ab if a["kind"] == "trigger"
               and a.get("when", {}).get("event") == "attack"]
        assert len(atk) == 1, cid
        assert "cost_of" in str(atk[0]["effect"]), cid
    # dm26rp2-s008: partial の4能力＋置換（alias 付き）。
    abs08 = conv["dm26rp2-s008"]["abilities"]
    assert len(abs08) == 5
    assert conv["dm26rp2-s008"]["source"].get("aliases") == ["dm26rp2-sec009"]


def test_bounced_with_refined_gaps():
    rej = _rejects()
    for cid, gaps in BOUNCED.items():
        assert cid in rej, cid
        assert rej[cid]["gaps"] == gaps, (cid, rej[cid]["gaps"])
        partial = rej[cid]["partial"]
        assert partial is not None, cid
        assert _has_guardman(partial), cid
        needs = [u["need"] for u in partial["source"]["unsupported"]]
        assert needs == gaps, (cid, needs)
    # dm26ex3-088: 破壊時シールド化の置換が partial に残る。
    assert any(a["kind"] == "replace" and a.get("when", {}).get("to") == "graveyard"
               for a in rej["dm26ex3-088"]["partial"]["abilities"])
    # dm26rp2-027: ガードマンへの付与が partial に残る。
    assert any(a["kind"] == "static"
               and (a.get("mod") or {}).get("grant") == ["speed_attacker", "powered_breaker"]
               for a in rej["dm26rp2-027"]["partial"]["abilities"])
    # dm26rp3-010: CIP のマナ送りが partial に残る。
    assert any(a["kind"] == "trigger"
               and any(op.get("op") == "move" and op.get("to") == "mana"
                       for op in a.get("effect", [{}])[0].get("body", []))
               for a in rej["dm26rp3-010"]["partial"]["abilities"])
