"""実エンジンの短い試行で候補を選別し、既知コンボを陽性対照として探索の効き目を確かめる（静的な拾い上げの置き換え）。

  PYTHONPATH=. python tools/combo_screen.py --control            # 既知コンボの中核が、ランダムな組より上位に出るか
  PYTHONPATH=. python tools/combo_screen.py --singles --top 40   # 全カード1枚ずつ試し、相手のゾーンを動かす札を上位に出す
試行: 手札にカード（最大3枚）、マナ10枚（5文明）、相手は山札30枚・マナ6枚。数ターン回して、相手の山札・マナ・盾の減りと勝ちを見る。
"""
import argparse
import itertools
import json
import random
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.defs import load_rules  # noqa: E402
from dmsim.scenario import build  # noqa: E402
from dmsim.solitaire import play_game  # noqa: E402

MANA5 = ["T001", "T003", "T004", "T005", "T008"]
OPP_DECK, OPP_MANA = 30, 6


def trial(rules, cards, seed=1, turns=2, budget=60) -> dict:
    spec = {"p0": {"hand": list(cards), "mana": MANA5 * 2}, "p1": {"mana": ["T001"] * OPP_MANA},
            "deck_size": OPP_DECK, "shuffle_deck": True, "seed": seed}
    st = build(rules, spec)
    z0 = st.s.zones
    d0, m0, s0 = len(z0["deck"][1]), len(z0["mana"][1]), len(z0["shield"][1])
    res, eng = play_game(rules, [], [], seed, max_turn=turns, budget=budget, start=st)
    z = eng.s.zones
    out = {"opp_deck": d0 - len(z["deck"][1]), "opp_mana": m0 - len(z["mana"][1]), "opp_shield": s0 - len(z["shield"][1]),
           "kill": res.kill_turn is not None}
    out["score"] = out["opp_deck"] + 2 * out["opp_mana"] + 3 * out["opp_shield"] + (20 if out["kill"] else 0)
    out["lock_score"] = out["opp_deck"] + 2 * out["opp_mana"]      # 殴りの勝ちや盾割りを除いた、山札・マナを動かす力
    return out


def score(rules, cards, seeds=(1, 2), turns=2, key="score") -> float:
    s = 0.0
    for sd in seeds:
        try:
            s += trial(rules, cards, sd, turns)[key]
        except Exception:     # 1組の失敗で止めない
            pass
    return s / len(seeds)


def control(rules, n_random=300, seed=1) -> list[dict]:
    y = yaml.safe_load(Path("data/known_combos/combos.yaml").read_text(encoding="utf-8"))["combos"]
    ids = [i for i in rules.cards if not i.startswith(("T", "R", "L"))]
    rng = random.Random(seed)
    out = []
    for c in y:
        cores = [p["id"] for p in c["parts"] if p.get("role") == "core" and p.get("id")]
        if c["id"] == "drill_lock":
            cores = ["dm16-051", "dm36-015", "dm36-078"]
        for k in (2, 3):
            if len(cores) < k:
                continue
            core_sc = max(score(rules, list(cm)) for cm in itertools.islice(itertools.combinations(cores, k), 20))
            base = sorted(score(rules, rng.sample(ids, k)) for _ in range(n_random // 3))
            pct = sum(1 for b in base if b < core_sc) / len(base)
            out.append({"combo": c["id"], "split": c["split"], "k": k, "core_score": round(core_sc, 2), "random_median": round(base[len(base) // 2], 2),
                        "random_p95": round(base[int(len(base) * .95)], 2), "percentile": round(pct, 3)})
            print(out[-1], flush=True)
    return out


def singles(rules, top=40, key="score") -> list[dict]:
    ids = [i for i in rules.cards if not i.startswith(("T", "R", "L"))]
    rows = []
    for i in ids:
        rows.append({"id": i, "name": rules.cards[i].name, "score": score(rules, [i], seeds=(1,), key=key)})
    rows.sort(key=lambda r: -r["score"])
    for r in rows[:top]:
        print(f"{r['score']:6.1f} {r['id']} {r['name']}")
    return rows


def recovery_pool(rules) -> list[str]:
    """自分のゾーンから手札・場へ動かす札（回収・蘇生・踏み倒し）。相手を動かす札の相棒の候補。"""
    from dmsim.zone_graph import bundles_of
    out = set()
    for b in bundles_of(rules):
        for m in b.moves:
            if m.owner != "opp" and str(m.src) in ("graveyard", "mana", "deck", "shield") and str(m.dst) in ("hand", "bz", "mana"):
                out.add(b.card)
    return sorted(c for c in out if not c.startswith(("T", "R", "L")))


def pairs(rules, singles_rows, top_a=12, turns=3, budget_s=1500, per=20) -> list[dict]:
    """相手を動かす上位の札 A × 回復系の札 B を、3ターンの実試行で選別する。相乗（組の点数 − 単体の最大）で順位づけ。"""
    sc = {r["id"]: r["score"] for r in singles_rows}
    A = [r["id"] for r in singles_rows[:top_a]]
    B = recovery_pool(rules)
    t0 = time.time()
    rows = []
    for a in A:
        for b in B:
            if a == b:
                continue
            if time.time() - t0 > budget_s:
                break
            s = score(rules, [a, b], seeds=(1,), turns=turns, key="lock_score")
            rows.append({"cards": [a, b], "names": [rules.cards[a].name, rules.cards[b].name], "score": s,
                         "synergy": s - max(sc.get(a, 0), sc.get(b, 0))})
    rows.sort(key=lambda r: -r["synergy"])
    print(f"{len(rows)} 組を試行 ({len(A)}x{len(B)})")
    for r in rows[:per]:
        print(f"{r['synergy']:6.1f} {r['score']:6.1f} {' + '.join(r['names'])}")
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--singles", action="store_true")
    ap.add_argument("--pairs", action="store_true", help="単体の上位 × 回復系の札を3ターンで試す")
    ap.add_argument("--budget", type=int, default=1500, help="--pairs の時間予算（秒）")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    rules = load_rules()
    t0 = time.time()
    if a.pairs:
        rows = singles(rules, a.top, key="lock_score")
        res = pairs(rules, rows, top_a=a.top, budget_s=a.budget)
    else:
        res = control(rules) if a.control else singles(rules, a.top) if a.singles else None
    if res is not None and a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
