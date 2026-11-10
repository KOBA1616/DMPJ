"""到達率の表: 候補（閉路の札）を仕込み局面にし、通常の開幕からその局面（手札・場・墓地に札がそろう）へ探索で届く割合を出す。
既知コンボと新しい候補を同じ尺度で並べる。強さではなく「到達可能性」の判定（探索は真の山札順を見る）。
  PYTHONPATH=. python tools/reach_table.py --known [--seeds 6] [--width 200]
  PYTHONPATH=. python tools/reach_table.py --cards ID,ID,... [--seeds 6]
"""
import argparse
import sys
import time
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.defs import load_rules  # noqa: E402
from dmsim.discovery.cyclesetup import FILLER, setup_from_cycle  # noqa: E402
from dmsim.discovery.reachsearch import reach_rate  # noqa: E402
from dmsim.zone_graph import Cycle, bundles_of  # noqa: E402


def target_of(spec: dict) -> dict:
    """仕込みspecから、到達目標（札のゾーン別の最低枚数）。マナと身代わり札は除く。"""
    out = {}
    for z in ("hand", "bz", "graveyard"):
        c = Counter(i for i in spec["p0"].get(z, []) if i != FILLER and not i.startswith("T"))
        if c:
            out[z] = dict(c)
    return out


def deck_of(cards: list[str], size: int = 40) -> list[str]:
    d = [c for c in cards for _ in range(4)][:size]
    return d + [FILLER] * (size - len(d))


def run(rules, cards: list[str], seeds, **kw) -> dict:
    bs = bundles_of(rules)
    spec = setup_from_cycle(rules, Cycle(bundles=[b for b in bs if b.card in cards]), mana_n=8)
    tgt = target_of(spec)
    t0 = time.time()
    r = reach_rate(rules, deck_of(cards), tgt, seeds, **kw)
    return {"cards": cards, "target": tgt, "rate": r["rate"], "turns": r["turns"], "sec": round(time.time() - t0)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--known", action="store_true")
    ap.add_argument("--cards")
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--width", type=int, default=200)
    ap.add_argument("--max-turn", type=int, default=5)
    a = ap.parse_args(argv)
    rules = load_rules()
    kw = {"width": a.width, "max_turn": a.max_turn}
    seeds = range(1, a.seeds + 1)
    if a.known:
        y = yaml.safe_load(Path("data/known_combos/combos.yaml").read_text(encoding="utf-8"))["combos"]
        for c in y:
            cores = [p["id"] for p in c["parts"] if p.get("role") == "core" and p.get("id")]
            if c["id"] == "drill_lock":
                cores = ["dm16-051", "dm36-015", "dm36-078"]
            cores = [i for i in cores if i in rules.cards][:10]
            r = run(rules, cores, seeds, **kw)
            print(c["id"], c["split"], f"到達率 {r['rate']:.2f}", f"ターン {sorted(r['turns'].values())}", f"{r['sec']}s", flush=True)
    if a.cards:
        r = run(rules, a.cards.split(","), seeds, **kw)
        print(r)


if __name__ == "__main__":
    main()
