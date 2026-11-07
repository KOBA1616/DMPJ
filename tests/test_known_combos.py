import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import known_combos as kc


def test_registered_set_is_clean():
    assert kc.check(kc.load()) == []


def test_overlap_across_splits_detected():
    a = {"id": "a", "split": "tuning", "status": "draft", "parts": [{"id": "x", "name": "X", "role": "core"}]}
    b = {"id": "b", "split": "holdout", "status": "draft", "parts": [{"id": "x", "name": "X", "role": "core"}]}
    assert any("共有" in e for e in kc.check([a, b]))
    b["parts"][0]["role"] = "support"
    b["parts"].append({"id": "y", "name": "Y", "role": "core"})
    assert kc.check([a, b]) == []
