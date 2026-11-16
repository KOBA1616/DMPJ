"""旧名の互換モジュール。定義元は dmsim.search.bestfirst（P1-S3 で探索・プレイを search/ へ集めた）。

この名前は定義元と同じモジュールオブジェクトを指す（sys.modules を差し替え）ので、
旧名に対する monkeypatch も定義元に効く。新しいコードは dmsim.search.bestfirst を import すること。
"""
import sys

from dmsim.search import bestfirst as _m

sys.modules[__name__] = _m
