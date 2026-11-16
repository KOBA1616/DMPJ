"""互換の入口（本体は dmsim.discovery.loop_screen、S5 に移した 2026-11-14）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dmsim.discovery.loop_screen as _m  # noqa: E402

if __name__ == "__main__":
    _m.main()
else:
    sys.modules[__name__] = _m
