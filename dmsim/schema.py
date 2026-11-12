"""旧名の互換モジュール。定義元は dmsim.cards.schema（P1 で S1 カードデータを cards/ へ集めた）。

この名前は定義元と同じモジュールオブジェクトを指す（sys.modules を差し替え）ので、
旧名に対する monkeypatch も定義元に効く。新しいコードは dmsim.cards.schema を import すること。
"""
import sys

from dmsim.cards import schema as _m

if __name__ != '__main__':
    sys.modules[__name__] = _m

if __name__ == "__main__":      # python -m dmsim.schema（旧名での起動経路）を保つ
    _m.main()
