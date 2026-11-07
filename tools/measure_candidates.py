"""組の候補の偽陽性率を測る（S-2）。上位候補・候補からの無作為・無関係な組（対照）を、実エンジンで確かめて成立率を比べる。

    python tools/measure_candidates.py --n 30 --seed 1 [--out result.json]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.defs import load_rules  # noqa: E402
from dmsim.discovery import candidates as cd  # noqa: E402
from dmsim.discovery.advantage import scan_pair_report  # noqa: E402

MANA = ["T001", "T003", "T004", "T005", "T008"] * 2        # 5文明 × 2枚（文明とマナの条件を満たす土台）


def confirm(rules, a: str, b: str, seed: int = 1) -> dict:
    t0 = time.time()
    try:
        rep = scan_pair_report(rules, a, b, base={"mana": MANA}, opp={"bz": ["T001"]}, places=("hand", "graveyard"), seeds=(seed,))
        return {"a": a, "b": b, "works": len(rep["works"]), "converts": len(rep["converts"]), "sec": round(time.time() - t0, 1)}
    except Exception as ex:                                # 未対応のカード等
        return {"a": a, "b": b, "error": f"{type(ex).__name__}: {str(ex)[:80]}", "sec": round(time.time() - t0, 1)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--pool", type=int, default=400, help="候補を選ぶカード数（先頭から無作為）")
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    rng = random.Random(a.seed)
    rules = load_rules()
    cards = [c for c in rules.cards if not c.startswith("T")]
    pool = rng.sample(cards, min(a.pool, len(cards)))
    pairs = cd.candidate_pairs(rules, pool)
    groups = {"top": pairs[:a.n], "random_candidates": rng.sample(pairs, min(a.n, len(pairs))) if pairs else []}
    linked = {(p["a"], p["b"]) for p in pairs}
    ctrl = []
    while len(ctrl) < a.n:
        x, y = rng.sample(pool, 2)
        if (x, y) not in linked:
            ctrl.append({"a": x, "b": y})
    groups["control"] = ctrl
    out = {"pool": len(pool), "candidates": len(pairs), "groups": {}}
    for name, ps in groups.items():
        rows = [confirm(rules, p["a"], p["b"], a.seed) for p in ps]
        ok = [r for r in rows if "error" not in r]
        out["groups"][name] = {"n": len(rows), "errors": len(rows) - len(ok), "works": sum(1 for r in ok if r["works"]),
                               "rate": round(sum(1 for r in ok if r["works"]) / max(1, len(ok)), 3), "rows": rows}
        print(name, {k: v for k, v in out["groups"][name].items() if k != "rows"}, flush=True)
    if a.out:
        Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    main()
