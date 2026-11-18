"""落下監査: 保持上限で落とした局面の標本を事後展開し、「枝切りの損失」
（落とした中に dist 有限＝殺せた局面がどれだけあったか）を推定する
（docs/order-function-generalization-plan.md §3.7 の定量目標 6）。

材料は chain_label の目録に記録された dropped（ターン→落としたキー）。
落とした局面の .pkl はストアに残っているので、標本を決定的に抽出し、
残りホライズン分だけ frontier で展開して dist を測る。予算に触れた
標本は unknown として分けて数え、損失率は Wilson 区間で報告する。

使い方:
  python3 tools/chain_drop_audit.py \
      --store logs/chain_label_x/<case> --stage 2 --per-turn 8 \
      --out logs/drop_audit.json
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dmsim import load_rules  # noqa: E402
from dmsim.engine import Engine  # noqa: E402

import exhaustive_crossturn as ct  # noqa: E402


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True,
                    help="chain_label のケースストア（dropped を含む）")
    ap.add_argument("--stage", type=int, default=1)
    ap.add_argument("--order", default="rank")
    ap.add_argument("--budget", type=int, default=200_000)
    ap.add_argument("--leaf-cap", type=int, default=200_000)
    ap.add_argument("--per-turn", type=int, default=8,
                    help="ターンごとの標本数")
    ap.add_argument("--seed", type=int, default=0, help="標本抽出の種")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    store = Path(a.store)
    mf = json.loads((store / "manifest.json").read_text(encoding="utf-8"))
    dropped = mf.get("dropped", {})
    if not dropped:
        print("dropped の記録がありません（上限に触れていない run）")
        return 1
    labels = {}
    if (store / "labels.json").exists():
        labels = json.loads((store / "labels.json").read_text(encoding="utf-8"))
    max_turn = mf["max_turn"]
    ct.LEAF_CAP = a.leaf_cap
    ct.FRONTIER_CAP = 10 ** 9  # 監査の展開は全保持（上限で unknown にしない）
    rules = load_rules()
    rng = random.Random(a.seed)

    report = {"store": str(store), "seed": a.seed, "turns": {}}
    tot_finite = tot_valid = 0
    for turn_s, keys in sorted(dropped.items()):
        turn = int(turn_s)
        keys = sorted(keys)
        sample = (keys if len(keys) <= a.per_turn
                  else rng.sample(keys, a.per_turn))
        rows = []
        for key in sample:
            with (store / f"{key}.pkl").open("rb") as fh:
                state, _log, _dg = pickle.load(fh)
            eng = Engine(rules, state)
            # 落とした局面はターン turn+1 の開始局面。到達したターンから
            # 数えて残りホライズンは max_turn - turn ターン。
            remain = max_turn - turn
            if remain < 1:
                rows.append({"key": key, "result": "out_of_horizon"})
                continue
            r = ct.run_case(rules, {}, max_turn=remain, mode="frontier",
                            beam=0, stage=a.stage, order=a.order,
                            node_budget=a.budget, trim_order="value",
                            start_engine=eng)
            if r["verdict"] == "kill":
                rows.append({"key": key, "result": "finite",
                             "dist": r["kill_turn"], "nodes": r["nodes"]})
            elif r["verdict"] == "no-kill":
                rows.append({"key": key, "result": "infinite",
                             "nodes": r["nodes"]})
            else:
                rows.append({"key": key, "result": "unknown",
                             "nodes": r["nodes"]})
        finite = sum(1 for r in rows if r["result"] == "finite")
        valid = sum(1 for r in rows
                    if r["result"] in ("finite", "infinite"))
        tot_finite += finite
        tot_valid += valid
        lo, hi = wilson(finite, valid)
        report["turns"][turn_s] = {
            "dropped_total": len(keys), "sampled": len(rows),
            "finite": finite, "valid": valid,
            "loss_rate_ci": [round(lo, 3), round(hi, 3)], "rows": rows}
        print(f"turn {turn}: dropped={len(keys)} sampled={len(rows)} "
              f"finite={finite}/{valid} loss CI [{lo:.2f}, {hi:.2f}]",
              flush=True)
    lo, hi = wilson(tot_finite, tot_valid)
    report["overall"] = {"finite": tot_finite, "valid": tot_valid,
                         "loss_rate_ci": [round(lo, 3), round(hi, 3)]}
    print(f"overall: finite={tot_finite}/{tot_valid} "
          f"loss CI [{lo:.2f}, {hi:.2f}]")
    if a.out:
        Path(a.out).write_text(json.dumps(report, ensure_ascii=False,
                                           indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
