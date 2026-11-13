"""旧名の互換モジュール。定義元は dmsim.discovery.combo_search（P1-S5 で発見を discovery/ へ集めた）。

この名前は定義元と同じモジュールオブジェクトを指す（sys.modules を差し替え）ので、
旧名に対する monkeypatch も定義元に効く。新しいコードは dmsim.discovery.combo_search を import すること。
"""
import sys

from dmsim.discovery import combo_search as _m

if __name__ == "__main__":   # python -m dmsim.combo_search（README の使い方）を保つ
    _m.main()
else:
    sys.modules[__name__] = _m
