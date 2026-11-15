"""局ごとに独立な測定をプロセス並列で回す共通の口（S4）。

map_ordered(fn, items, workers) は [fn(x) for x in items] と同じ並びの結果を返す。
- fork で子を作るので、親の今の状態（読み込んだルール・環境変数・切り替え）をそのまま引き継ぐ。fn は閉包でもよい（pickle しない）。
- 各局は「親のその時点の状態」から始まる。逐次実行で局の間に残るキャッシュ等の影響を受けないので、結果が局の順に依存しないことの確認にもなる。
- workers は None なら環境変数 DMSIM_WORKERS（既定 1 = 逐次）。1 以下や fork が使えない環境では逐次に回す。
- 結果は pickle できる値であること。
"""
from __future__ import annotations

import multiprocessing as mp
import os
from typing import Callable, Sequence

_FN: Callable | None = None
_ITEMS: Sequence | None = None


def default_workers() -> int:
    try:
        return max(1, int(os.environ.get("DMSIM_WORKERS", "1")))
    except ValueError:
        return 1


def _call(i: int):
    return _FN(_ITEMS[i])


def map_ordered(fn: Callable, items, workers: int | None = None) -> list:
    global _FN, _ITEMS
    items = list(items)
    w = default_workers() if workers is None else workers
    w = min(w, len(items))
    if w <= 1 or "fork" not in mp.get_all_start_methods():
        return [fn(x) for x in items]
    prev = (_FN, _ITEMS)
    _FN, _ITEMS = fn, items
    try:
        with mp.get_context("fork").Pool(w, maxtasksperchild=None) as pool:
            return pool.map(_call, range(len(items)), chunksize=1)
    finally:
        _FN, _ITEMS = prev
