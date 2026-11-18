"""ランキング学習用のデータセット構築: ラベル付きストア（chain_label の
出力）から、局面ごとの特徴と dist を JSONL に出す。

統計版 ruler（順序関数の汎化 §3.3）と、代理指標と dist の相関測定
（枝狩り方針の根拠）の共通入力。教師は exact なラベルだけが信用できる
（inexact は exact フラグで区別して残す）。保持判断は同じターン内の
比較なので、group（ケース:ターン）を記録する。

特徴 v1: order_fn.features のゾーン枚数＋派生量、V（evaluate）、
各鎖の充足率（--stages-file、複数可）。カード ID そのものは入れない
（デッキ汎化のため。属性集計は v2 で検討）。

使い方:
  python3 tools/build_rank_dataset.py \
      --store logs/chain_label_hidden_s1/saga_hidden_setup_seed1-f0d5f69e \
      --stages-file tools/saga_loop_stages.yaml \
      --out logs/rank_dataset.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import exhaustive_crossturn as ct  # noqa: E402
from dmsim import load_rules  # noqa: E402
from dmsim.plan.macro import MacroPlanner, load_stage_file, stage_fraction  # noqa: E402
from dmsim.search.leaf_eval import Weights, evaluate  # noqa: E402
from order_fn import features  # noqa: E402

_W = Weights()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", action="append", required=True,
                    help="labels.json を含むケースディレクトリ（複数可）")
    ap.add_argument("--stages-file", action="append", default=[],
                    help="充足率を特徴に入れる鎖（複数可）")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    planners = []
    for f in a.stages_file:
        stages, _ = load_stage_file(f)
        planners.append((f, MacroPlanner(stages=stages)))
    rules = load_rules()
    rows = []
    for store_s in a.store:
        store = Path(store_s)
        labels = json.loads((store / "labels.json").read_text())
        case = store.name
        for key, lab in sorted(labels.items()):
            eng = ct._store_get(store, rules, key)
            f = features(eng, 0)
            feat = dict(f)
            feat["gy_minus_deck"] = f["own_gy"] - f["own_deck"]
            feat["bz_plus_mana"] = f["own_bz"] + f["own_mana"]
            feat["deck_survives"] = 1 if f["own_deck"] >= 2 else 0
            feat["v"] = evaluate(eng, 0, _W)
            for i, (_name, pl) in enumerate(planners):
                feat[f"plan_frac_{i}"] = stage_fraction(eng, 0, pl.plan(eng, 0))
            rows.append({
                "case": case, "key": key, "turn": lab["turn"],
                "dist": lab["dist"], "exact": lab["exact"],
                "group": f"{case}:t{lab['turn']}",
                "features": feat,
            })
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    exact = [r for r in rows if r["exact"]]
    from collections import Counter
    hist = Counter(r["dist"] for r in exact)
    print(f"rows={len(rows)} exact={len(exact)} "
          f"dist histogram (exact)={dict(hist)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
