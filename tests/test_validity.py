import json

from dmsim import validity as v


def _rows(p):
    return [{"combo": "a", "split": "tuning", "percentile": p}, {"combo": "h", "split": "holdout", "percentile": 0.0}]


def test_judge():
    assert v.judge(_rows(0.95))[0]
    assert not v.judge(_rows(0.5))[0]
    assert not v.judge([])[0]                       # 対照なしは不合格（信じない）
    assert v.judge(_rows(0.95))[0]                  # holdout は合否に使わない


def test_stamp_expires_when_instrument_changes(tmp_path):
    root = tmp_path
    (root / "dmsim").mkdir()
    (root / "dmsim" / "a.py").write_text("x=1")
    (root / "data" / "cards").mkdir(parents=True)
    stamp = root / "stamp.json"
    assert not v.status(stamp, root)[0]             # 印なし
    v.write_stamp(_rows(0.95), stamp, root)
    assert v.status(stamp, root)[0]
    (root / "dmsim" / "a.py").write_text("x=2")     # 測定器が変わると失効
    ok, why = v.status(stamp, root)
    assert not ok and "古い" in why
    v.write_stamp(_rows(0.1), stamp, root)
    assert "届かない" in v.status(stamp, root)[1]
    assert v.annotate({"n": 1}, stamp, root)["validity"]["valid"] is False


def test_judge_detects_flat_scores():
    from dmsim.validity import judge
    rows = [{"combo": c, "split": "tuning", "k": 2, "core_score": 7.0, "random_median": 7.0, "random_p95": 7.0, "percentile": 0.0}
            for c in ("a", "b")]
    ok, why = judge(rows)
    assert not ok and "張り付" in why
