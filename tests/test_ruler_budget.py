from types import SimpleNamespace

from dmsim.eval import loop_entry as le


def test_measure_budget_uses_ruler_standard():
    assert le.RULER_BUDGET == 1500
    assert le.measure_budget(SimpleNamespace(source={"budget": 200})) == 1500
    assert le.measure_budget(SimpleNamespace(source={})) == 1500
    assert le.measure_budget(SimpleNamespace(source={"budget": 4000})) == 4000
    assert le.measure_budget(SimpleNamespace(source={"budget": 200}), 300) == 300   # 明示した予算が優先
