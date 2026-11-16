"""ループ列挙: 資源の流れ網（zone_graph の束と受け渡し）から、1周で資源が減らず、どれかが増える（または中立の）閉路を静的に数え、
エンジンで再生して確かめる（式の差分と、エンジンが認めたループが合うか）。
  PYTHONPATH=. python tools/loop_enum.py --known      # 既知コンボの中核だけの網で数え、再発見できるか
  PYTHONPATH=. python tools/loop_enum.py --control N  # 陰性対照: 全札の閉路からN個を再生し、確認率を見る
候補の判定:
  式      Cycle.delta()（自分の資源）が負を含まず、sure（偶然のドロー頼みでない）
  再生    cyclesetup の局面で数ターン回し、エンジンのループ検出（res.loops）が出るか
"""
import argparse
import itertools
import random
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.discovery.cyclesetup import setup_from_cycle  # noqa: E402
from dmsim.engine.scenario import build  # noqa: E402
from dmsim.search.game import play_game  # noqa: E402
from dmsim.engine.zone_graph import TICKS, Cycle, bundles_of, feeds  # noqa: E402


def lap_ok(c: Cycle) -> bool:
    """式の判定: 1周で自分の資源が減らず（山札だけは削れてよい。自分の山札切れは別に見る）、偶然のドロー頼みでない。"""
    return c.sure and all(v >= 0 for k, v in c.delta().items() if k != "deck")


def cycles_among(rules, cards: list[str], max_len: int = 3) -> list[Cycle]:
    """指定カードだけの網で、長さ max_len までの閉路（束の列）を数える。"""
    bs = [b for b in bundles_of(rules) if b.card in cards]
    # 時計（ターン終了など）が前提の束は、時間が進めば起きる。どの束からも受け渡し可能として扱う（sure は 1 = 時間頼み）
    succ = {i: {j: v for j, b2 in enumerate(bs) if (v := feeds(a, b2, rules) or (1 if b2.prem is not None and b2.prem.kind in TICKS else 0))}
            for i, a in enumerate(bs)}
    out, seen = [], set()
    for L in range(1, max_len + 1):
        for path in itertools.product(range(len(bs)), repeat=L):
            if path[0] != min(path) or any(path[(k + 1) % L] not in succ[path[k]] for k in range(L)):
                continue
            key = tuple(sorted(path)) if L > 1 else path
            if key in seen:
                continue
            seen.add(key)
            out.append(Cycle([bs[i] for i in path], all(succ[path[k]][path[(k + 1) % L]] == 2 for k in range(L))))
    return out


def replay(rules, cyc: Cycle, turns: int = 2, budget: int = 40) -> dict:
    spec = setup_from_cycle(rules, cyc, mana_n=8)
    spec["seed"] = 1
    st = build(rules, spec)
    res, eng = play_game(rules, [], [], 1, max_turn=turns, budget=budget, start=st)
    return {"loops": len(res.loops), "lock": res.lock is not None, "kill": res.kill_turn is not None}


def cores_of(combo: dict) -> list[str]:
    if combo["id"] == "drill_lock":
        return ["dm16-051", "dm36-015", "dm36-078"]
    return [p["id"] for p in combo["parts"] if p.get("role") == "core" and p.get("id")]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--known", action="store_true")
    ap.add_argument("--control", type=int, default=0)
    a = ap.parse_args(argv)
    rules = load_rules()
    if a.known:
        y = yaml.safe_load(Path("data/known_combos/combos.yaml").read_text(encoding="utf-8"))["combos"]
        for c in y:
            cores = [i for i in cores_of(c) if i in rules.cards]
            cs = cycles_among(rules, cores)
            ok = [x for x in cs if lap_ok(x)]
            rep = [replay(rules, x) for x in ok[:20]]
            print(f"{c['id']:11} {c['split']:7} 閉路 {len(cs):4}  式OK {len(ok):4}  再生(先頭20) ループ検出 {sum(r['loops'] > 0 for r in rep)} ロック {sum(r['lock'] for r in rep)}", flush=True)
    if a.control:
        from combo_hunt import fast_cycles
        cs = fast_cycles(rules, max_cycle3=0)
        ok = [x for x in cs if lap_ok(x)]
        print(f"全閉路 {len(cs)}  式OK {len(ok)}")
        sample = random.Random(1).sample(ok, min(a.control, len(ok)))
        rep = [replay(rules, x) for x in sample]
        print(f"陰性対照 式OKから{len(sample)}個を再生: ループ検出 {sum(r['loops'] > 0 for r in rep)}  ロック {sum(r['lock'] for r in rep)}")


if __name__ == "__main__":
    main()


# ---- 有限ループ: 1周で減る資源は「在庫÷消費」周まで回せる。相手の資源への効果 × 周数 を価値とする ----
STOCK = {"mana": 6, "hand": 3, "graveyard": 0, "bz": 0, "shield": 5, "deck": 30}   # 目安の在庫（仕込み局面の想定）


def lap_bound(c: Cycle, stock: dict | None = None):
    """(周数の上限, 相手側の総効果)。減る資源が無ければ周数は None（無限）。"""
    stock = stock or STOCK
    laps = None
    for k, v in c.delta().items():
        if v < 0:
            n = stock.get(k, 0) // -v
            laps = n if laps is None else min(laps, n)
    opp = c.opp_delta()
    total = {k: v * (laps if laps is not None else 1) for k, v in opp.items()}
    return laps, total
