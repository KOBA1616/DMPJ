"""3枚組の探索を回す（本体は dmsim/discovery/triples.py、2026-11-14）。

  python tools/triple_hunt.py collect --out bases.json [--max-turn 5]
  python tools/triple_hunt.py attach --bases bases.json --out triples.json [--per-base 8]
  python tools/triple_hunt.py measure --triples triples.json --out meas.json [--top 60] [--per-base 2] [--seeds 4] [--time-limit 3600]
measure は対象とその対照（勝ち手段の代わりにランダムな札、同じ部品）を交互に測り、打ち切っても数が揃うようにする。
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.discovery import triples as X  # noqa: E402


def _base_from(d):
    return X.Base(cards=d["cards"], names=d["names"], gains={tuple(k.split(":")): v for k, v in d["gains"].items()},
                  has_win=d["has_win"], unknown=d["unknown"], turn=d["turn"], score=d["score"],
                  layout=d.get("layout", {}), grave=d.get("grave", []))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["collect", "attach", "measure", "trial"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--bases")
    ap.add_argument("--triples")
    ap.add_argument("--max-turn", type=int, default=5)
    ap.add_argument("--per-base", type=int, default=8)
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--per-win", type=int, default=3, help="同じ勝ち手段の札を何組まで測るか（偏り防止）")
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--budget", type=int, default=1500)
    ap.add_argument("--entry-turn", type=int, default=3)
    ap.add_argument("--shard", default="0/1", help="trial: i/n（n 個に分けた i 番目）")
    ap.add_argument("--trial-budget", type=int, default=50)
    ap.add_argument("--trial-seeds", type=int, default=1)
    ap.add_argument("--time-limit", type=int, default=0)
    a = ap.parse_args()
    t0 = time.time()
    log = lambda m: print(f"{m} [{time.time()-t0:.0f}s]", flush=True)  # noqa: E731
    rules = load_rules()
    by = X.by_card_of(rules)
    if a.cmd == "collect":
        bases, drop = X.collect(rules, by, max_turn=a.max_turn, log=log)
        gk = Counter(k for b in bases for k, v in b.gains.items() for k in [f"{k[0]}:{k[1]}:{'+' if v > 0 else '-'}"])
        out = {"bases": [{**b.__dict__, "gains": {f"{o}:{z}": v for (o, z), v in b.gains.items()}} for b in bases],
               "drop": dict(drop), "gain_keys": dict(gk.most_common()), "seconds": round(time.time() - t0)}
        log(f"(a) 部品 {len(bases)} 落ち {dict(drop)}")
    elif a.cmd == "attach":
        bases = [_base_from(d) for d in json.loads(Path(a.bases).read_text(encoding="utf-8"))["bases"]]
        tr = X.attach(rules, by, bases, per_base=a.per_base, log=log)
        out = {"triples": [X.as_row(t) for t in tr], "static": dict(Counter(t.static for t in tr)),
               "bases_with_hits": len({tuple(t.base) for t in tr}), "bases": len(bases), "seconds": round(time.time() - t0)}
    elif a.cmd == "trial":
        from dmsim.discovery import basebuild as B
        raw = B._raw_cards(rules)
        i, n = map(int, a.shard.split("/"))
        bases = [_base_from(d) for d in json.loads(Path(a.bases).read_text(encoding="utf-8"))["bases"]][i::n]
        rows = []
        for k, b in enumerate(bases):
            r = X.trial(rules, b, T=4, seeds=range(1, a.trial_seeds + 1), budget=a.trial_budget, raw=raw)
            rows.append({"cards": b.cards, "names": b.names, "turn": b.turn, **r})
            if k % 20 == 0:
                log(f"{k}/{len(bases)} 通過 {sum(x['ok'] for x in rows)} 理由 {dict(Counter(x['reason'] for x in rows if x['reason']))}")
        out = {"rows": rows, "shard": a.shard, "seconds": round(time.time() - t0)}
    else:
        rows = json.loads(Path(a.triples).read_text(encoding="utf-8"))["triples"]
        per, pw, pick = Counter(), Counter(), []
        for t in rows:
            k = tuple(t["base"])
            if per[k] >= a.per_base or pw[t["win"]] >= a.per_win:
                continue
            per[k] += 1
            pw[t["win"]] += 1
            pick.append(t)
            if len(pick) >= a.top:
                break
        from dmsim.discovery import basebuild as B
        raw = B._raw_cards(rules)
        wins = X.win_cards(rules, raw)
        pool = sorted(i for i, d in rules.cards.items() if not B._test(i) and isinstance(d.cost, int)
                      and i not in wins and not (i in raw and B.missing_effect(d)))
        rng = random.Random(20261114)
        seeds = range(1, a.seeds + 1)
        out_rows, cut = [], None
        for n, t in enumerate(pick):
            if a.time_limit and time.time() - t0 > a.time_limit:
                cut = {"at": n, "of": len(pick)}
                break
            cards = t["base"] + [t["win"]]
            m = X.measure(rules, X.deck_of(rules, cards, raw), t["base"], T=a.entry_turn, seeds=seeds, budget=a.budget,
                          win_ids=[t["win"]], layout=t.get("layout"), grave=t.get("grave", ()))
            ctl = X.control_card(rules, pool, set(cards), rng)
            c = X.measure(rules, X.deck_of(rules, t["base"] + [ctl], raw), t["base"], T=a.entry_turn, seeds=seeds, budget=a.budget,
                          layout=t.get("layout"), grave=t.get("grave", ()))
            v = X.value(m, c)
            out_rows.append({**t, "measured": {k: m[k] for k in m if k != "rows"}, "control": {"card": ctl, "name": rules.cards[ctl].name,
                             **{k: c[k] for k in c if k != "rows"}}, "value": v, "rows": m["rows"]})
            log(f"{'+'.join(t['names'])}: 段1 {m['stage1']}/{m['games']} 段2 {m['stage2']} 最速 {m['best_turn']} 殴り {m['beat']} "
                f"誤り {m['errors']} | 対照 段1 {c['stage1']} 段2 {c['stage2']}")
        out = {"rows": out_rows, "cut": cut, "args": vars(a), "seconds": round(time.time() - t0)}
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
