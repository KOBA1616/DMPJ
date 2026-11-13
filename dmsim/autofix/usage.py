"""旧名の互換モジュール。定義元は dmsim.eval.usage（P1-S5 で使用実績の収集を評価 eval/ へ下ろした）。

この名前は定義元と同じモジュールオブジェクトを指す（sys.modules を差し替え）ので、
旧名に対する monkeypatch も定義元に効く。新しいコードは dmsim.eval.usage を import すること。
"""
import sys

from dmsim.eval import usage as _m

sys.modules[__name__] = _m
