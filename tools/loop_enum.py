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
from dmsim.defs import load_rules  # noqa: E402
from dmsim.discovery.cyclesetup import setup_from_cycle  # noqa: E402
from dmsim.scenario import build  # noqa: E402
from dmsim.solitaire import play_game  # noqa: E402
from dmsim.zone_graph import Cycle, bundles_of, feeds  # noqa: E402


def lap_ok(c: Cycle) -> bool:
    """式の判定: 1周で自分の資源が減らず（山札だけは削れてよい。自分の山札切れは別に見る）、偶然のドロー頼みでない。"""
    return c.sure and all(v >= 0 for k, v in c.delta().items() if k != "deck")


def cycles_among(rules, cards: list[str], max_len: int = 3) -> list[Cycle]:
    """指定カードだけの網で、長さ max_len までの閉路（束の列）を数える。"""
    bs = [b for b in bundles_of(rules) if b.card in cards]
    succ = {i: {j: v for j, b2 in enumerate(bs) if (v := feeds(a, b2, rules))} for i, a in enumerate(bs)}
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


# ---- 使用回数 x つきの列挙（閉路でなく「束の多重集合」: 全員の前提を誰かが満たし、1周の収支が負でない）----
def bundle_delta(b) -> dict:
    return Cycle([b]).delta()


def solve_x(rules, cards: list[str], max_x: int = 2, max_used: int = 5) -> list[dict]:
    """cards の束から、使用回数 x（各 0..max_x、使う束は max_used 個まで）を選び、
    (1) 前提を持つ束は、使う束のどれかから受け渡しがある（feeds>0）か、自分から起動できる束がある
    (2) Σ x·delta の自分の資源が負にならない（山札だけは可）かつ、相手の資源が動くか自分のどれかが増える
    を満たす組を返す。"""
    bs = [b for b in bundles_of(rules) if b.card in cards]
    n = len(bs)
    fed = [[feeds(a, c, rules) > 0 for c in bs] for a in bs]
    dl = [bundle_delta(b) for b in bs]
    od = [Cycle([b]).opp_delta() for b in bs]
    out = []
    for used in itertools.chain.from_iterable(itertools.combinations(range(n), k) for k in range(1, max_used + 1)):
        # 前提の閉包: 前提を持つ束は、使う束の誰かから受け渡しがある
        if any(bs[i].prem is not None and not any(fed[j][i] for j in used) for i in used):
            continue
        for xs in itertools.product(range(1, max_x + 1), repeat=len(used)):
            tot, opp = {}, {}
            for i, x in zip(used, xs):
                for k, v in dl[i].items():
                    tot[k] = tot.get(k, 0) + x * v
                for k, v in od[i].items():
                    opp[k] = opp.get(k, 0) + x * v
            if any(v < 0 for k, v in tot.items() if k != "deck"):
                continue
            if any(v > 0 for v in tot.values()) or any(opp.values()):
                out.append({"bundles": [bs[i].name for i in used], "x": list(xs), "delta": {k: v for k, v in tot.items() if v},
                            "opp": {k: v for k, v in opp.items() if v}})
                break
    return out
