"""語彙パイロット第4弾（2026-10-30）の検証。

鬼タイム（rejects: oni_time）は新語彙ではなく、条件「自分と相手のシールドの数が合計6つ以下」を
既存の if 条件（cmp の sum に両者の count）で書くことで、常在型の付与・コスト軽減や
誘発内の分岐として表せる。ここでは常在型のパワー付与がシールド合計で切り替わることを固定する。
"""
from conftest import setup


def test_oni_time_static_power_switches_by_total_shields(rules):
    e = setup(rules, {"bz": ["T035"], "shield": ["T001"] * 5}, {"shield": ["T001"] * 5})
    cid = e.bz_tops(0)[0]
    assert e.chars(cid)["power"] == 2000                       # 合計10 > 6: 鬼タイム不成立
    e = setup(rules, {"bz": ["T035"], "shield": ["T001"] * 3}, {"shield": ["T001"] * 3})
    cid = e.bz_tops(0)[0]
    assert e.chars(cid)["power"] == 5000                       # 合計6 <= 6: パワー+3000
    e = setup(rules, {"bz": ["T035"], "shield": ["T001"] * 2}, {"shield": ["T001"] * 5})
    cid = e.bz_tops(0)[0]
    assert e.chars(cid)["power"] == 2000                       # 合計7 > 6: 不成立
