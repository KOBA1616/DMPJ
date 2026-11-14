"""局ごとのプロセス並列（eval.parallel、2026-11-14）。"""
import os

from dmsim.eval.parallel import map_ordered


def test_map_ordered_matches_sequential_and_keeps_order():
    base = 7
    f = lambda x: (x, x * base, os.environ.get("DMSIM_CHECK"))   # 閉包と親の環境変数を引き継ぐ
    xs = list(range(10))
    assert map_ordered(f, xs, 3) == [f(x) for x in xs] == map_ordered(f, xs, 1)
    assert map_ordered(f, [], 4) == []
