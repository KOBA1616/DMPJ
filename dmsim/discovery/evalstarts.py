"""旧名の互換モジュール。定義元は dmsim.eval.evalstarts（P1-S4 で評価を eval/ へ集めた）。

この名前は定義元と同じモジュールオブジェクトを指す（sys.modules を差し替え）ので、
旧名に対する monkeypatch も定義元に効く。新しいコードは dmsim.eval.evalstarts を import すること。
"""
import sys

from dmsim.eval import evalstarts as _m

sys.modules[__name__] = _m
