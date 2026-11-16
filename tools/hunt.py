"""部品探索を端から端まで回す（本体は dmsim/discovery/hunt_pipeline.py）。途中で止まっても同じ --out で再開する。
  python tools/hunt.py --out runs/hunt-YYYYMMDD [--workers 4] [--cheap] [--fresh] [--stages check,trial] [--no-register]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.discovery import hunt_pipeline as H  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int)
    ap.add_argument("--cheap", action="store_true")
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--stages")
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("--opp-level", type=int, default=1)
    ap.add_argument("--no-register", action="store_true")
    a = ap.parse_args()
    cfg = H.Config(cheap=a.cheap, workers=a.workers, top=a.top, opp_level=a.opp_level, register=not a.no_register)
    if a.stages:
        cfg.stages = tuple(a.stages.split(","))
    r = H.run(load_rules(), a.out, cfg, fresh=a.fresh)
    print(r)
    sys.exit(2 if r.get("stopped") else 0)


if __name__ == "__main__":
    main()
