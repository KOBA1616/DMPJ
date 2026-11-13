"""旧名の互換モジュール。定義元は dmsim.eval.deckeval（P1-S6 でデッキ案の採否評価を評価 eval/ へ下ろした）。

この名前は定義元と同じモジュールオブジェクトを指す（sys.modules を差し替え）ので、
旧名に対する monkeypatch も定義元に効く。新しいコードは dmsim.eval.deckeval を import すること。
"""
import sys

from dmsim.eval import deckeval as _m

sys.modules[__name__] = _m
