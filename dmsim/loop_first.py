"""旧名の互換モジュール。定義元は dmsim.search.loop_first（P1-S3 で探索・プレイを search/ へ集めた）。

この名前は定義元と同じモジュールオブジェクトを指す（sys.modules を差し替え）ので、
旧名に対する monkeypatch も定義元に効く。新しいコードは dmsim.search.loop_first を import すること。
"""
import sys

from dmsim.search import loop_first as _m

if __name__ == "__main__":   # python -m dmsim.loop_first（README の使い方）を保つ
    _m.main()
else:
    sys.modules[__name__] = _m
