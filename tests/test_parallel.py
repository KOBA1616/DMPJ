"""局ごとのプロセス並列（base.parallel、2026-11-14）。"""
import os

from dmsim.base.parallel import map_ordered


def test_map_ordered_matches_sequential_and_keeps_order():
    base = 7
    f = lambda x: (x, x * base, os.environ.get("DMSIM_CHECK"))   # 閉包と親の環境変数を引き継ぐ
    xs = list(range(10))
    assert map_ordered(f, xs, 3) == [f(x) for x in xs] == map_ordered(f, xs, 1)
    assert map_ordered(f, [], 4) == []


def test_imap_ordered_and_strided_chunks():
    from dmsim.base.parallel import imap_ordered, strided_chunks
    it = imap_ordered(lambda x: x + 1, range(5), 2)
    assert list(it) == [1, 2, 3, 4, 5]
    assert strided_chunks(range(5), 3) == [[0, 3], [1, 4], [2]]
    assert strided_chunks([1], 4) == [[1]]
    first = imap_ordered(lambda x: x, range(10), 2)
    assert next(first) == 0
    first.close()


def test_process_parallel_only_through_base_parallel():
    """プロセス並列は dmsim.base.parallel だけを通る（multiprocessing / ProcessPoolExecutor / Pool の直使い禁止）。"""
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    pat = re.compile(r"^\s*(import multiprocessing|from multiprocessing|from concurrent\.futures import[^\n]*ProcessPoolExecutor|"
                     r"[^\n#]*ProcessPoolExecutor\()", re.M)
    bad = [str(p.relative_to(root)) for d in ("dmsim", "tools") for p in (root / d).rglob("*.py")
           if str(p.relative_to(root)) != "dmsim/base/parallel.py" and pat.search(p.read_text(encoding="utf-8"))]
    assert not bad, bad
