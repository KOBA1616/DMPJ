"""既知ループに足す1枚の発見（dmsim/discovery/addon_hunt.py）の小さな部品。"""
from dmsim.discovery import addon_hunt as A


def test_core_of_saga():
    core = A.core_of("saga")
    assert "dm22ex2-021" in core and len(core) == 6 and set(core.values()) == {4}


def test_swap_and_paired():
    assert A.swap(["a", "b", "a"], "a", "c") == ["c", "b", "c"]
    base = [{"seed": 1, "entry_turn": None}, {"seed": 2, "entry_turn": 3}, {"seed": 3, "entry_turn": 5}]
    new = [{"seed": 1, "entry_turn": 4}, {"seed": 2, "entry_turn": 3}, {"seed": 3, "entry_turn": 4}]
    p = A.paired(base, new, 4)
    assert p["n"] == 3 and p["up"] == 2 and p["down"] == 0 and abs(p["mean"] - 0.667) < 1e-3


def test_record_keeps_other_entries(tmp_path):
    f = tmp_path / "x.yaml"
    A.record({"entry": "akashic", "candidates": []}, f)
    n = A.record({"entry": "saga", "candidates": [{"diff": {"lo": 0.1}}, {"diff": {"lo": -0.1}}]}, f)
    import yaml
    y = yaml.safe_load(f.read_text(encoding="utf-8"))
    assert n == 1 and set(y) == {"akashic", "saga"}
