"""Rust エンジンが一致を確かめた Python エンジンの版を記録する（rust/dmcore/verified_engine.txt）。

Python のエンジン（dmsim/engine の主要ファイル）を変えたら、dmcore を作り直して tests/test_rust_*.py を通した後にこれを実行する。
記録と今のエンジンが違う間は、対局・探索は Rust を使わず Python で進む（dmsim.engine.rustcore.enabled）。
  python tools/rust_stamp.py          # 記録する
  python tools/rust_stamp.py --check  # 今の版と記録が一致するか（終了コード 0/1）
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dmsim.engine import rustcore  # noqa: E402


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    h = rustcore.engine_hash()
    if "--check" in argv:
        try:
            cur = open(rustcore.STAMP, encoding="utf-8").read().split()[0]
        except (OSError, IndexError):
            cur = ""
        print("ok" if cur == h else f"stale: recorded {cur or '-'} / now {h}")
        return 0 if cur == h else 1
    with open(rustcore.STAMP, "w", encoding="utf-8") as fh:
        fh.write(h + "\n")
    print("recorded", h)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
