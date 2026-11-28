"""fast_loop_screen.py で残った組（と同数のランダム組）に、物差し（入口局面での段1・段2）と上限ターンの実測を当てる（2026-11-13）。

入口局面は組ごとに作る汎用のもの: 自分の4ターン目のはじめ相当（マナ5）。手札に部品を1枚ずつ、マナに部品を1枚ずつ（文明を払えるように）と
つなぎの札、盾はつなぎの札。山札は残り（部品は4枚ずつ、つなぎの札 T022 で40枚）。相手は入口局面と同じ（盾5・手札5・マナ3・山札27、マナチャージだけ）。
ランダム組は全札から2枚をシードで選び、4T以内に届きうる組だけを同数取る。
使い方: python tools/fast_loop_measure.py --screen out.json --top 25 --seeds 4 --out meas.json
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
from dmsim.engine import scenario  # noqa: E402
from dmsim.eval import speed_bound as S  # noqa: E402
from dmsim.eval.lockcheck import lock_probe  # noqa: E402
from dmsim.eval.ruler import judge  # noqa: E402
from dmsim.play_api import play_cheat as play_game  # noqa: E402

FILLER = "T022"


def deck_of(parts):
    d = []
    for x in parts:
        d += [x] * 4
    return d + [FILLER] * (40 - len(d))


def entry(parts, seed):
    deck = deck_of(parts)
    p0 = {"hand": list(parts) + [FILLER] * 2, "mana": list(parts) + [FILLER] * max(0, 5 - len(parts)),
          "shield": [FILLER] * 5, "bz": [], "graveyard": []}
    left = list(deck)
    for ids in p0.values():
        for i in ids:
            left.remove(i)
    p0["deck"] = sorted(left)
    spec = {"p0": p0, "p1": {"hand": ["T001"] * 5, "mana": ["T001"] * 3}, "deck_size": 40, "deck_exact": [True, False],
            "deck_left": [None, 27], "seed": seed}
    return deck, spec


def ruler_rows(rules, parts, seeds, budget):
    rows = []
    for sd in seeds:
        deck, spec = entry(parts, sd)
        try:
            e = scenario.build(rules, spec, first_player=0)
            res, eng = play_game(rules, deck, [], sd, first_player=0, max_turn=2, budget=budget, start=e, lock_judge=lock_probe)
            vd = judge(res, eng)
            rows.append({"seed": sd, "stage1": vd.stage1.ok, "stage2": vd.stage2.ok, "via": vd.stage2.via, "error": res.error})
        except Exception as ex:          # 効果データが未対応で局面が作れない・対局が落ちる
            rows.append({"seed": sd, "stage1": False, "stage2": False, "via": None, "error": f"{type(ex).__name__}: {ex}"[:200]})
    return rows


def random_set(rng, ids, k, keep, rules):
    while True:
        xs = rng.sample(ids, k)
        if tuple(sorted(xs)) in keep:
            continue
        t = S.static_bound(rules, xs)["turn"]
        if t is not None and t <= 4:
            return xs, t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen", required=True)
    ap.add_argument("--top", type=int, default=25, help="2枚組の上位")
    ap.add_argument("--three", type=int, default=5, help="3枚組を上位から何組測るか")
    ap.add_argument("--per-base", type=int, default=1, help="3枚組: 同じ2枚の土台から何組まで")
    ap.add_argument("--extra", action="append", default=[], help="必ず測る組（ID をカンマ区切り）")
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--budget", type=int, default=1500)
    ap.add_argument("--bound-seeds", type=int, default=3)
    ap.add_argument("--bound-budget", type=int, default=300)
    ap.add_argument("--time-limit", type=int, default=0, help="秒。超えたら打ち切り、打ち切った位置を記録する")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    t0 = time.time()
    rules = load_rules()
    sc = json.loads(Path(a.screen).read_text(encoding="utf-8"))
    groups = [{"kind": "extra", "parts": x.split(","), "turn": S.static_bound(rules, x.split(","))["turn"]} for x in a.extra]
    groups += [{"kind": "passed", "parts": [p["a"], p["b"]], "rank": p["rank"], "turn": p["turn"], "unapproved": p["unapproved"]}
               for p in sc["passed_top"][:a.top]]
    per = Counter()
    n3 = 0
    for t in sc["three"]:
        k = (t["a"], t["b"])
        if per[k] >= a.per_base or n3 >= a.three:
            continue
        per[k] += 1
        n3 += 1
        groups.append({"kind": "three", "parts": [t["a"], t["b"], t["c"]], "turn": t["turn"], "unapproved": t["unapproved"]})
    keep = {tuple(sorted(g["parts"])) for g in groups}
    rng = random.Random(20261113)
    ids = sorted(c for c in rules.cards if not c.startswith("T") and rules.cards[c].cost is not None)
    order = []
    for g in groups:                       # 対象とランダム（同じ枚数）を交互に測る（打ち切っても数が揃う）
        xs, t = random_set(rng, ids, len(g["parts"]), keep, rules)
        order += [g, {"kind": "random", "parts": xs, "turn": t}]
    out, cut = [], None
    for idx, g in enumerate(order):
        if a.time_limit and time.time() - t0 > a.time_limit:
            cut = {"at": idx, "of": len(order), "next": g["parts"]}
            print(f"打ち切り: {idx}/{len(order)}", flush=True)
            break
        rows = ruler_rows(rules, g["parts"], range(1, a.seeds + 1), a.budget)
        g.update(names=[rules.cards[x].name for x in g["parts"]], stage1=sum(r["stage1"] for r in rows), stage2=sum(r["stage2"] for r in rows),
                 errors=sum(1 for r in rows if r["error"]), vias=sorted({r["via"] for r in rows if r["via"]}), games=len(rows),
                 best_turn=None, kills=None, bound_games=0)
        if g["stage1"] or g["stage2"] or g["kind"] == "extra":   # 上限ターンの実測は段1以上に届いた組だけ（時間の節約）
            mb = S.measured_bound(rules, deck_of(g["parts"]), range(a.bound_seeds), budget=a.bound_budget, max_turn=4)
            g.update(best_turn=mb["best_turn"], kills=mb["kills"], bound_games=mb["games"])
        out.append(g)
        print(f"{g['kind']:7s} {'+'.join(g['names'])}: 段1 {g['stage1']}/{len(rows)} 段2 {g['stage2']}/{len(rows)} 誤り{g['errors']} "
              f"実測上限 {g['best_turn']}（{g['kills']}/{g['bound_games']}） {time.time()-t0:.0f}s", flush=True)
    Path(a.out).write_text(json.dumps({"groups": out, "cut": cut, "seconds": round(time.time() - t0), "args": vars(a)},
                                      ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
