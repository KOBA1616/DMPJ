"""再生の同一視（設計書 §20）: 同じ札を同じ結果になる形で使う手を同じ手とみなす。"""
from dmsim.engine import loop as L


def _d(kind, keys):
    return {"kind": kind, "options": [{"key": k} for k in keys]}


def test_paid_play_maps_to_free():
    assert L._equiv_keys(_d("main", ["play:dm01-001:3:free", "end"]), ["play:dm01-001:3"]) == ["play:dm01-001:3:free"]


def test_payment_maps_to_first_option():
    assert L._equiv_keys(_d("pay_mana", ["mana:a", "mana:b"]), ["mana:z"]) == ["mana:a"]


def test_unrelated_key_is_not_mapped():
    assert L._equiv_keys(_d("main", ["play:x:free"]), ["play:y"]) is None
    assert L._equiv_keys(_d("main", ["end"]), ["mana:z"]) is None       # 支払い以外の決定では代えない


class _C:
    delta = {"deck:1": -1, "mana_untapped:0": 0}


def test_delta_allows_only_more_untapped_mana_after_substitution():
    assert L._delta_ok({"deck:1": -1, "mana_untapped:0": 2}, _C, True)
    assert not L._delta_ok({"deck:1": -1, "mana_untapped:0": 2}, _C, False)
    assert not L._delta_ok({"deck:1": -1, "mana_untapped:0": -1}, _C, True)
    assert not L._delta_ok({"deck:1": -2}, _C, True)
