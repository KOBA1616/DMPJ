from dmsim.autofix.gate import check_paths, compare


def test_paths():
    assert check_paths([("M", "dmsim/search/prep.py"), ("A", "tests/test_x.py")]) == []
    assert len(check_paths([("M", ".github/workflows/a.yml"), ("D", "tests/test_a.py"), ("M", "dmsim/eval/harness.py")])) == 3


def test_compare():
    base = {"kill": [None] * 20}
    better = {"kill": [3] * 20}
    assert compare(base, better)["verdict"] == "accept_candidate"
    assert compare(better, base)["verdict"] == "reject"
    assert compare(base, base)["verdict"] == "inconclusive"
