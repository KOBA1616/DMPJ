"""語彙パイロット第179弾のカード側テスト（登録形）: ラウンド215で登録した
ACEタマシード 10件が converted.yaml にあり、`ace: true`・types [tamaseed]
で parse が通ること。差し戻した dm22rp2x-4a は rejects に残り、洗練した
ギャップ名 tamaseed_attack_reuse_cip / add_types_power_set を持つこと。
"""
import json
from pathlib import Path

import yaml

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()
ROOT = Path(__file__).parent.parent

REGISTERED = [
    "dm22rp1-10b", "dm22rp1-2b", "dm22rp1-3a", "dm22rp1-6a",
    "dm22rp2x-2a", "dm22rp2x-6a", "dm22sd1-001", "dm23sp1-006",
    "dm25sd1-001", "dm25sd1-003",
]


def _converted():
    data = yaml.safe_load(
        (ROOT / "data" / "cards" / "converted.yaml").read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["cards"]}


def _rejects():
    return {json.loads(line)["id"]: json.loads(line) for line in
            (ROOT / "data" / "cards" / "raw" / "rejects.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()}


def test_ace_cards_registered():
    conv = _converted()
    for cid in REGISTERED:
        assert cid in conv, cid
        d = parse_card(conv[cid], TABLES)
        assert d.ace is True
        assert d.types == ["tamaseed"]
        assert d.id == cid


def test_ace_bounced_card_keeps_refined_gaps():
    rej = _rejects()
    assert "dm22rp2x-4a" in rej
    assert rej["dm22rp2x-4a"]["gaps"] == [
        "tamaseed_attack_reuse_cip", "add_types_power_set"]
    assert rej["dm22rp2x-4a"]["partial"]["ace"] is True
    # 複合ギャップの dm26sd1-p005 は本ラウンドの対象外で rejects に残る
    assert "dm26sd1-p005" in rej
    assert "ace_tamaseed_conditional_creature" in rej["dm26sd1-p005"]["gaps"]
