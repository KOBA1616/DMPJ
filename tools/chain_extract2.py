"""抽出器 v2: ラベルつき局面集合（chain_label の出力）から段階目標の鎖を
生成する（docs/chain-from-frontier-plan.md §3）。

キル記録だけを材料にした v1 と違い、勝ち・負け両方のラベルつき局面を
標本にする。通過点と閾値の決め方は v1 の規則を大きな標本に適用する:

- dist（最速キルまでの残りターン）≤ d の局面が全て満たす条件を、
  水準 d の通過点とする（枚数の閾値は分布の分位、既定は最小値）。
- dist = ∞（範囲内で殺せない）の局面も多数満たす条件は弁別力が
  ないので弱める／外す（負例フィルタ。v1 ではできなかった判定）。
- 段は dist の大きい順（遠い未来）から並べ、累積形にする。

材料は exact な局面（打ち切りに触れていない）だけを使う。
公平性: deck の名前つき述語は使わない（"*" の残り枚数のみ、公開情報）。

使い方:
  python3 tools/chain_extract2.py --store logs/label_prep/<case> \
      --out tools/extracted2_stages.yaml --report /tmp/extract2_report.json

--store はカンマ区切りで複数指定でき、複数シードの材料を合算する。
合算の条件: 全ストアの settings_hash が一致すること（デッキ・段・予算・
上限・最大ターンが同じで、シードだけが違う）。同一キーが複数ストアに
exact で現れたら1件に畳み、dist が食い違えば材料の不整合として止める。
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from dmsim import load_rules  # noqa: E402
from dmsim.engine import Engine  # noqa: E402
from dmsim.search.reachsearch import zone_counts  # noqa: E402

ZONES = ("hand", "bz", "graveyard", "shield", "mana")


def state_features(eng, me: int, use_cards: bool) -> dict:
    """{(zone, card_id or "*"): 枚数}。deck は "*" のみ（公平性）。"""
    feats = {}
    for z in ZONES:
        ids = eng.zlist(z, me)
        feats[(z, "*")] = len(ids)
        if use_cards:
            for cid, n in zone_counts(eng, me, z).items():
                feats[(z, cid)] = n
    feats[("deck", "*")] = len(eng.zlist("deck", me))
    return feats


def quantile_threshold(values: list[int], q: float) -> int:
    vs = sorted(values)
    return vs[min(len(vs) - 1, int(q * len(vs)))]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True,
                    help="chain_label のケースストア（labels.json を含む）。"
                         "カンマ区切りで複数指定すると合算する")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", default=None)
    ap.add_argument("--quantile", type=float, default=0.0,
                    help="閾値の分位（0 = 最小値）")
    ap.add_argument("--features", choices=["star", "all"], default="all")
    ap.add_argument("--neg-ratio", type=float, default=0.9,
                    help="dist=∞ の局面の充足率がこれ以上なら条件を外す")
    ap.add_argument("--me", type=int, default=0)
    a = ap.parse_args(argv)

    stores = [Path(s) for s in a.store.split(",") if s.strip()]
    manifests = []
    for st in stores:
        manifests.append(json.loads(
            (st / "manifest.json").read_text(encoding="utf-8")))
    hashes = {m.get("settings_hash") for m in manifests}
    if len(hashes) > 1:
        print(f"settings_hash が一致しないストアは合算できません: {hashes}")
        return 1
    # exact 局面を全ストアから合算する。同一キーは1件に畳み、
    # dist の食い違いは材料の不整合として止める。
    pooled: dict[str, tuple[Path, dict]] = {}
    per_store_exact: dict[str, int] = {}
    for st, m in zip(stores, manifests):
        labels = json.loads((st / "labels.json").read_text(encoding="utf-8"))
        n_exact = 0
        for k, v in labels.items():
            if not v["exact"]:
                continue
            n_exact += 1
            if k in pooled:
                if pooled[k][1]["dist"] != v["dist"]:
                    print(f"dist の不整合: キー {k} が {pooled[k][0]} では "
                          f"{pooled[k][1]['dist']}、{st} では {v['dist']}")
                    return 1
                continue
            pooled[k] = (st, v)
        per_store_exact[str(st)] = n_exact
    if not pooled:
        print("exact な局面がありません")
        return 1
    manifest = manifests[0]
    rules = load_rules()
    feats: dict[str, dict] = {}
    dists: dict[str, int | None] = {}
    for key, (st, lab) in pooled.items():
        with (st / f"{key}.pkl").open("rb") as fh:
            state, _log, _dg = pickle.load(fh)
        eng = Engine(rules, state)
        feats[key] = state_features(eng, a.me, a.features == "all")
        dists[key] = lab["dist"]
    exact = {k: v for k, (st, v) in pooled.items()}
    finite = sorted({d for d in dists.values() if d is not None},
                    reverse=True)
    inf_keys = [k for k, d in dists.items() if d is None]
    all_features = set()
    for f in feats.values():
        all_features.update(f.keys())

    stages = []
    report_stages = []
    running: dict[tuple, int] = {}
    prev_target: dict | None = None
    for d in finite:
        pop = [k for k, dd in dists.items() if dd is not None and dd <= d]
        level_cond: dict[tuple, int] = {}
        for f in sorted(all_features):
            thr = quantile_threshold([feats[k].get(f, 0) for k in pop],
                                     a.quantile)
            if thr < 1:
                continue
            if inf_keys:
                neg = (sum(1 for k in inf_keys
                           if feats[k].get(f, 0) >= thr) / len(inf_keys))
                if neg >= a.neg_ratio:
                    continue
            level_cond[f] = thr
        for f, thr in level_cond.items():
            running[f] = max(running.get(f, 0), thr)
        target: dict[str, dict[str, int]] = {}
        for (z, cid), thr in sorted(running.items()):
            target.setdefault(z, {})[cid] = thr
        if target == prev_target:
            continue
        prev_target = target
        sat = sum(1 for k in pop
                  if all(feats[k].get((z, cid), 0) >= n
                         for z, want in target.items()
                         for cid, n in want.items()))
        inf_sat = (sum(1 for k in inf_keys
                       if all(feats[k].get((z, cid), 0) >= n
                              for z, want in target.items()
                              for cid, n in want.items()))
                   / len(inf_keys)) if inf_keys else None
        stages.append({"name": f"dist<={d}", "target": target})
        report_stages.append(
            {"level": d, "conditions": sum(len(v) for v in target.values()),
             "support": f"{sat}/{len(pop)}",
             "inf_satisfy_ratio": inf_sat})
    header = (f"# tools/chain_extract2.py による自動生成"
              f"（材料: {', '.join(str(s) for s in stores)}、"
              f"設定 {manifest.get('settings_hash')}、"
              f"exact 局面 {len(exact)} 件、"
              f"quantile={a.quantile} features={a.features} "
              f"neg_ratio={a.neg_ratio}）。手で直さず、材料と引数を直して作り直す。\n")
    Path(a.out).write_text(
        header + yaml.safe_dump({"stages": stages}, allow_unicode=True,
                                sort_keys=False),
        encoding="utf-8")
    report = {"stores": [str(s) for s in stores],
              "per_store_exact": per_store_exact,
              "exact_states": len(exact),
              "inf_states": len(inf_keys), "levels": finite,
              "stages": report_stages}
    if a.report:
        Path(a.report).write_text(json.dumps(report, ensure_ascii=False,
                                             indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    print(f"stages: {len(stages)} -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
