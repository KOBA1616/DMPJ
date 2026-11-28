"""局ごとに独立な測定をプロセス並列で回す共通の口（S0）。

map_ordered(fn, items, workers) は [fn(x) for x in items] と同じ並びの結果を返す。
- fork で子を作るので、親の今の状態（読み込んだルール・環境変数・切り替え）をそのまま引き継ぐ。fn は閉包でもよい（pickle しない）。
- 各局は「親のその時点の状態」から始まる。逐次実行で局の間に残るキャッシュ等の影響を受けないので、結果が局の順に依存しないことの確認にもなる。
- workers は None なら環境変数 DMSIM_WORKERS（既定 1 = 逐次）。1 以下や fork が使えない環境では逐次に回す。
- 結果は pickle できる値であること。
- 乱数シードの扱い（再現性の約束）: シードは必ず items（各局の仕事）に明示して渡す。ワーカー番号・pid・実行順からシードを作らない。
  こうすれば workers が何でも各局の結果は同じになる。局をまとめて渡したい時は strided_chunks で割る（割り方が毎回同じなので測定間で局の対応が保たれる）。
- プロセス並列の窓口はこのファイルだけ（multiprocessing / ProcessPoolExecutor を直に使うと tests/test_parallel.py が落ちる）。
  外部コマンド待ちやAPI待ちのスレッド並列（ThreadPoolExecutor）は対象外。
"""
from __future__ import annotations

import multiprocessing as mp
import os
from typing import Callable, Iterator, Sequence

_FN: Callable | None = None
_ITEMS: Sequence | None = None


def default_workers() -> int:
    try:
        return max(1, int(os.environ.get("DMSIM_WORKERS", "1")))
    except ValueError:
        return 1


def _call(i: int):
    return _FN(_ITEMS[i])


def _use_fork(w: int) -> bool:
    return w > 1 and "fork" in mp.get_all_start_methods()


def imap_ordered(fn: Callable, items, workers: int | None = None, chunksize: int = 1) -> Iterator:
    """map_ordered の逐次版: 結果を items の順に1件ずつ返す。途中で打ち切って閉じれば残りの仕事は捨てる（時間上限の打ち切り用）。"""
    global _FN, _ITEMS
    items = list(items)
    w = default_workers() if workers is None else workers
    w = min(w, len(items))
    if not _use_fork(w):
        for x in items:
            yield fn(x)
        return
    prev = (_FN, _ITEMS)
    _FN, _ITEMS = fn, items
    try:
        with mp.get_context("fork").Pool(w) as pool:
            yield from pool.imap(_call, range(len(items)), chunksize=max(1, chunksize))
    finally:
        _FN, _ITEMS = prev


def map_ordered(fn: Callable, items, workers: int | None = None, chunksize: int = 1) -> list:
    return list(imap_ordered(fn, items, workers, chunksize))


def strided_chunks(seq, n: int) -> list[list]:
    """seq を n 個に飛び飛びで割る（空の組は除く）。重い局が偏らず、同じ入力なら割り方も毎回同じ。"""
    seq = list(seq)
    return [seq[i::n] for i in range(max(1, n)) if seq[i::n]]
