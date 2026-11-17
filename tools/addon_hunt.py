"""既知ループに足す1枚を探す（dmsim/discovery/addon_hunt.py の CLI）。

  python tools/addon_hunt.py --entry saga --deck data/decks/basebuild_saga_v3.yaml --seeds 40 --workers 4
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", default="saga")
    ap.add_argument("--deck", default="data/decks/basebuild_saga_v3.yaml")
    ap.add_argument("--seeds", type=int, default=40)
    ap.add_argument("--turn", type=int, default=4)
    ap.add_argument("--opp", type=int, default=1)
    ap.add_argument("--budget", type=int, default=200)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--per", type=int, default=6)
    ap.add_argument("--linked", type=int, default=8)
    ap.add_argument("--slot", default=None, help="差し替える基盤の id（抜き取りの測定を省く）")
    ap.add_argument("--ckpt", default=None, help="途中結果の JSON（中断後に続きから）")
    ap.add_argument("--pick-only", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    import yaml
    from dmsim.cards.defs import load_rules
    from dmsim.discovery import addon_hunt as A
    rules = load_rules()
    if a.pick_only:
        deck = yaml.safe_load(Path(a.deck).read_text(encoding="utf-8"))["deck"]
        for c in A.pick(rules, deck, A.core_of(a.entry), per=a.per, linked=a.linked):
            print(c["id"], c["name"], c["why"])
        return 0
    r = A.run(rules, a.entry, a.deck, seeds=a.seeds, turn=a.turn, opp=a.opp, budget=a.budget, workers=a.workers,
              per=a.per, linked=a.linked, ckpt=Path(a.ckpt) if a.ckpt else None, log=lambda *x: print(*x, flush=True), slot=a.slot)
    if not a.no_write:
        print("significant", A.record(r, note=f"段階{a.opp}・同一シード{a.seeds}局・入口{a.turn}T以内"))
    for c in r["candidates"]:
        print(c["id"], c["name"], c["entry"], c["diff"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
