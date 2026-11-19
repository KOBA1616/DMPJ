"""語彙パイロット第180弾のカード側テスト（登録形）: ラウンド216で登録した
Jトルネード 6件が converted.yaml にあり parse が通ること。差し戻した 4件は
rejects に残り、洗練したギャップ名（cip_reuse / attack_cancel / gr_summon /
attack_count_limit_next_turn）を持ち、解けた Jトルネード節を partial に残すこと。
"""
import json
from pathlib import Path

import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()
ROOT = Path(__file__).parent.parent

REGISTERED = [
    "dm26ex4-020", "dmrp11-004", "dmrp12-042",
    "dmsd13-013", "dmsd13-019", "dm26rp3-033",
]

BOUNCED = {
    # dmrp12-078 は第251弾（cancel_attack）＋ラウンド285で登録済みのため除外
    "dmsd13-007": ["gr_summon"],
    "dmrp11-040": ["attack_count_limit_next_turn"],
}


def _converted():
    data = yaml.safe_load(
        (ROOT / "data" / "cards" / "converted.yaml").read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["cards"]}


def _rejects():
    return {json.loads(line)["id"]: json.loads(line) for line in
            (ROOT / "data" / "cards" / "raw" / "rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()}


def _jtornado_trigger(ability):
    """攻撃時（またはブロック時）Jトルネード誘発の形か。"""
    assert ability["kind"] == "trigger"
    assert ability["when"]["event"] in ("attack", "block")
    assert ability["when"]["subject"] == "self"
    assert json.dumps(ability, ensure_ascii=False).count("jtornado") >= 1


def test_jtornado_cards_registered():
    conv = _converted()
    for cid in REGISTERED:
        assert cid in conv, cid
        d = parse_card(conv[cid], TABLES)
        assert d.id == cid
    # dm26ex4-020: 合計コスト形（2回展開＋modal の無料唱え）
    c = conv["dm26ex4-020"]
    assert c["keywords"] == ["g_strike"]
    s = json.dumps(c["abilities"], ensure_ascii=False)
    assert s.count("jt1") >= 2 and s.count("jt2") >= 2
    assert '"modal"' in s and "resolve_position" in s
    # dmrp11-004: 最大2回（repeat）＋1回につき無料唱え
    c = conv["dmrp11-004"]
    assert c["keywords"] == ["double_breaker"]
    assert '"repeat"' in json.dumps(c["abilities"], ensure_ascii=False)
    # dmrp12-042: ブロック時 Jトルネード＋自アンタップ
    c = conv["dmrp12-042"]
    assert c["keywords"] == ["blocker", "cannot_attack"]
    assert c["abilities"][0]["when"] == {"event": "block", "subject": "self"}
    # dmsd13-013: 手札5枚以上条件の static grant＋T408型
    c = conv["dmsd13-013"]
    assert c["source"]["aliases"] == ["dmrp11-018", "promoy18-049", "promoy18-054"]
    static = [a for a in c["abilities"] if a["kind"] == "static"]
    assert len(static) == 1
    assert static[0]["mod"]["grant"] == ["cannot_be_attacked", "unblockable"]
    assert static[0]["if"]["cmp"][2] == 5
    # dmsd13-019: 後続は bounce（相手のパワー6000以下）
    c = conv["dmsd13-019"]
    assert c["source"]["aliases"] == ["dmrp11-077"]
    assert '"bounce"' in json.dumps(c["abilities"], ensure_ascii=False)
    assert "power_le" in json.dumps(c["abilities"], ensure_ascii=False)
    # dm26rp3-033: CIP節＋T411型の2能力
    c = conv["dm26rp3-033"]
    assert c["keywords"] == ["s_trigger"]
    assert len(c["abilities"]) == 2
    assert c["abilities"][0]["when"] == {"event": "move", "to": "bz", "subject": "self"}
    _jtornado_trigger(c["abilities"][1])


def test_jtornado_bounced_cards_keep_refined_gaps():
    rej = _rejects()
    for cid, gaps in BOUNCED.items():
        assert cid in rej, cid
        assert rej[cid]["gaps"] == gaps, (cid, rej[cid]["gaps"])
        partial = rej[cid]["partial"]
        assert partial["id"] == cid
        # 解けた Jトルネード節が partial に残っている
        assert any(a["kind"] == "trigger" for a in partial.get("abilities") or [])
        _jtornado_trigger(
            next(a for a in partial["abilities"] if a["kind"] == "trigger"))
