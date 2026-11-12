"""旧名の互換モジュール。定義元は dmsim.engine.loop（P1 で S2 ゲームエンジンを engine/ へ集めた）。

この名前は定義元と同じモジュールオブジェクトを指す（sys.modules を差し替え）ので、
旧名に対する monkeypatch も定義元に効く。新しいコードは dmsim.engine.loop を import すること。
"""
import sys

from dmsim.engine import loop as _m

sys.modules[__name__] = _m
