"""旧名の互換モジュール。定義元は dmsim.base.loopspec（P1 で S0 へ移した）。

この名前は定義元と同じモジュールオブジェクトを指す（sys.modules を差し替え）ので、
旧名に対する monkeypatch も定義元に効く。新しいコードは dmsim.base.loopspec を import すること。
"""
import sys

from dmsim.base import loopspec as _m

sys.modules[__name__] = _m
