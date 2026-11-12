"""旧名の互換モジュール。定義元は dmsim.eval.shrink（P1-S4 で評価を eval/ へ集めた）。

この名前は定義元と同じモジュールオブジェクトを指す（sys.modules を差し替え）ので、
旧名に対する monkeypatch も定義元に効く。新しいコードは dmsim.eval.shrink を import すること。
"""
import sys

from dmsim.eval import shrink as _m

if __name__ == "__main__":   # python -m dmsim.discovery.shrink を保つ
    _m.main()
else:
    sys.modules[__name__] = _m
