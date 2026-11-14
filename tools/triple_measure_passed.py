"""試し打ちを通った部品をそのまま物差しにかける（部品に勝ち手段が入っている組、2026-11-14）。
  python tools/triple_measure_passed.py --trial trial.json --shard 0/4 --out out.json [--seeds 4] [--budget 1500]
置き方は試し打ちで通った置き方（layouts の名前）を使う。速さは speed_bound.static_bound（入口に届く上限ターン）を記録する。"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.discovery import triples as X  # noqa: E402
from dmsim.discovery import basebuild as B  # noqa: E402
from dmsim.eval import speed_bound as S  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trial", required=True)
    ap.add_argument("--bases", required=True)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--budget", type=int, default=1500)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    t0 = time.time()
    rules = load_rules()
    raw = B._raw_cards(rules)
    bases = {tuple(d["cards"]): d for d in json.loads(Path(a.bases).read_text(encoding="utf-8"))["bases"]}
    rows = [r for r in json.loads(Path(a.trial).read_text(encoding="utf-8"))["rows"] if r["ok"]]
    i, n = map(int, a.shard.split("/"))
    out = []
    for r in rows[i::n]:
        d = bases[tuple(r["cards"])]
        b = X.Base(cards=d["cards"], names=d["names"], gains={tuple(k.split(":")): v for k, v in d["gains"].items()},
                   has_win=d["has_win"], unknown=d["unknown"], turn=d["turn"], score=d.get("score", 0), layout=d.get("layout", {}),
                   grave=d.get("grave", []))
        lo = next(x for x in X.layouts(rules, b, raw) if x["name"] == r["layout"])
        deck = X.deck_of(rules, lo["parts"], raw)
        m = X.measure(rules, deck, lo["parts"], T=3, seeds=range(1, a.seeds + 1), budget=a.budget, layout=lo["layout"], grave=b.grave)
        sb = S.static_bound(rules, b.cards)["turn"]
        out.append({"cards": b.cards, "names": b.names, "layout": r["layout"], "trial_laps": r["laps"], "entry_bound": sb,
                    **{k: m[k] for k in m if k != "rows"}, "vias": sorted({x["via"] for x in m["rows"] if x["via"]})})
        print(f"{'+'.join(b.names)}: 段1 {m['stage1']}/{m['games']} 段2 {m['stage2']} 最速 {m['best_turn']} 上限T {sb} [{time.time()-t0:.0f}s]", flush=True)
    Path(a.out).write_text(json.dumps({"rows": out}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
