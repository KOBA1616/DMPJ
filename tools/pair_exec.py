"""2枚組の有限ループ候補を『仕込み局面』（cyclesetup が部品を並べた開始）で実行層として検証する。
通常開幕の到達率は別（reach_table）。陽性対照: ドリル・スコール＋ジョバンニが高得点になること。
得点 = 探索中に見えた『相手の墓地の枚数＋失った盾』の最大値（相手は受け身）。
使い方: python tools/pair_exec.py --pairs /tmp/pairs.json --out /tmp/pair_exec.jsonl --limit 500"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dmsim.defs import load_rules  # noqa: E402
from dmsim.discovery.bestfirst import priority  # noqa: E402
from dmsim.discovery.cyclesetup import setup_from_cycle  # noqa: E402
from dmsim.discovery.reachsearch import reach_target  # noqa: E402
from dmsim.eval.opp_pressure import make_term  # noqa: E402
from dmsim.eval.vfeatures import v_priority  # noqa: E402
from dmsim.scenario import build  # noqa: E402
from loop_enum import cycles_among, lap_bound, lap_ok  # noqa: E402


def score(rules, pair, width=100, max_turn=10):
    cyc = [c for c in cycles_among(rules, list(pair), max_len=2) if lap_ok(c) or lap_bound(c)[1]]
    cyc = [c for c in cyc if lap_bound(c)[1]]          # 相手に効くものだけ
    if not cyc:
        return None
    spec = setup_from_cycle(rules, cyc[0], mana_n=8)
    spec["seed"] = 1
    st = build(rules, spec)
    best, term = [0], make_term()

    def prio(en, me, w):
        best[0] = max(best[0], len(en.zlist("graveyard", 1)) + max(0, 5 - len(en.zlist("shield", 1))))
        return v_priority(en, me, w, priority, under_w=0, res_w=0, terms=[term])
    reach_target(st, {"graveyard": {"*": 999}}, 0, width=width, max_turn=max_turn, max_depth=300, prio=prio)
    return best[0]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--width", type=int, default=100)
    ap.add_argument("--max-turn", type=int, default=10)
    a = ap.parse_args(argv)
    rules = load_rules()
    pairs = json.loads(Path(a.pairs).read_text())
    out = Path(a.out)
    done = {tuple(json.loads(l)["pair"]) for l in out.read_text().splitlines()} if out.exists() else set()
    n = 0
    for p in pairs:
        if tuple(p) in done or n >= a.limit:
            continue
        t = time.time()
        try:
            rec = {"pair": p, "names": [rules.cards[c].name for c in p], "score": score(rules, p, a.width, a.max_turn)}
        except Exception as ex:  # noqa: BLE001
            rec = {"pair": p, "error": f"{type(ex).__name__}: {ex}"}
        rec["sec"] = round(time.time() - t, 1)
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        n += 1
        print(rec, flush=True)


if __name__ == "__main__":
    main()
