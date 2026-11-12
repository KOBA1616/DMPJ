"""旧名の互換モジュール。定義元は dmsim.search.reachsearch（P1-S3 で探索・プレイを search/ へ集めた）。

この名前は定義元と同じモジュールオブジェクトを指す（sys.modules を差し替え）ので、
旧名に対する monkeypatch も定義元に効く。新しいコードは dmsim.search.reachsearch を import すること。
"""
import sys

from dmsim.search import reachsearch as _m

sys.modules[__name__] = _m
