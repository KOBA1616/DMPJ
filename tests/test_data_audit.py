import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import audit_cards
from dmsim.dataaudit import new_violations
from dmsim.defs import _dedupe_abilities


def test_no_new_data_violations():
    """原文と構造化データの食い違いが、基準線（data/audit/baseline.json）より増えていない。"""
    assert audit_cards.main([]) == 0


def test_new_violations_ratchet():
    assert new_violations({"a": ["1", "2"]}, {"a": ["1"]}) == {"a": ["2"]}
    assert new_violations({"a": ["1"]}, {"a": ["1", "2"]}) == {}


def test_dedupe_abilities_removes_exact_duplicates():
    ab = {"kind": "static", "affects": "self", "mod": {"power_when": {"amount": 3000, "when": "attacking"}}}
    raw = {"id": "x", "abilities": [ab, {"kind": "static", "mod": {}}, dict(ab)]}
    _dedupe_abilities(raw)
    assert len(raw["abilities"]) == 2
