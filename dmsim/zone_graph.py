"""旧名の互換モジュール。定義元は dmsim.engine.zone_graph（P1 で S2 ゲームエンジンを engine/ へ集めた）。

この名前は定義元と同じモジュールオブジェクトを指す（sys.modules を差し替え）ので、
旧名に対する monkeypatch も定義元に効く。新しいコードは dmsim.engine.zone_graph を import すること。
"""
import sys

from dmsim.engine import zone_graph as _m

if __name__ != '__main__':
    sys.modules[__name__] = _m

if __name__ == "__main__":      # python -m dmsim.zone_graph（旧名での起動経路）を保つ
    _m.main()
