"""デッキ用鎖ゲート: デッキケース（0ターン目開始）の鎖の採否を判定する。

シナリオ用 chain_gate と違い、基準は「固定シナリオの最速キル」ではなく
「ホールドアウトシードのラベル（chain_label の全保持展開）が与える
最速キルターン」である。材料のシードとゲートのシードを分けることで、
同じデッキ内でのホールドアウトにする。

判定（シードごと）:
- 参照の開始局面が exact で dist 有限 → beam4 + plan が同じキルターンで
  キルすること。
- 参照の開始局面が exact で dist = ∞（範囲内にキルなし）→ beam が
  キルしないこと（NO-KILL のみ可。UNKNOWN は判定不能として FAIL）。
- 参照の開始局面が exact でない → そのシードは基準に使えない（SKIP）。
  全シード SKIP は FAIL。
- 効率: beam のノード数が参照ラベル付けの総ノード数を超えないこと。

使い方:
  python3 tools/chain_gate_deck.py --stages-file <鎖> \
      --ref-store-dir logs/chain_label_doom_e_s31 --seeds 33,51 \
      --max-turn 3 --stage 2
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def reference(store_dir: Path, deck_stem: str, seed: int) -> dict | None:
    """シードのケースストアから開始局面（turn=1）の参照ラベルを返す。"""
    cands = sorted(store_dir.glob(f"{deck_stem}_seed{seed}-*"))
    for c in cands:
        labels_p = c / "labels.json"
        if not labels_p.exists():
            continue
        labels = json.loads(labels_p.read_text(encoding="utf-8"))
        starts = [v for v in labels.values() if v["turn"] == 1]
        if len(starts) != 1:
            continue
        mf = json.loads((c / "manifest.json").read_text(encoding="utf-8"))
        return {"store": str(c), "start": starts[0],
                "frontier_nodes": mf.get("total_nodes")}
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages-file", required=True)
    ap.add_argument("--deck", default="data/decks/saga_doom_e.yaml")
    ap.add_argument("--ref-store-dir", required=True,
                    help="chain_label の --store-dir（ケースストアの親）")
    ap.add_argument("--seeds", required=True,
                    help="ホールドアウトシード（カンマ区切り）")
    ap.add_argument("--max-turn", type=int, default=3)
    ap.add_argument("--stage", type=int, default=2)
    ap.add_argument("--beam", type=int, default=4)
    ap.add_argument("--budget", type=int, default=200_000)
    ap.add_argument("--leaf-cap", type=int, default=200_000)
    ap.add_argument("--timeout", type=int, default=3600)
    a = ap.parse_args()
    py = sys.executable
    deck_stem = Path(a.deck).stem
    seeds = [int(x) for x in a.seeds.split(",") if x.strip()]

    refs = {}
    usable = []
    for seed in seeds:
        ref = reference(Path(a.ref_store_dir), deck_stem, seed)
        if ref is None:
            print(f"[gate-deck] seed{seed}: SKIP (参照ストアなし)", flush=True)
            continue
        refs[seed] = ref
        st = ref["start"]
        if not st["exact"]:
            print(f"[gate-deck] seed{seed}: SKIP (開始局面が exact でない)",
                  flush=True)
            continue
        usable.append(seed)
        kt = st["dist"]  # turn=1 なので kill_turn = dist
        print(f"[gate-deck] seed{seed}: ref kill_turn={kt} "
              f"(frontier nodes={ref['frontier_nodes']})", flush=True)
    if not usable:
        print("[gate-deck] RESULT: FAIL (使える参照がありません)", flush=True)
        return 1

    out_path = f"logs/gate_deck_{deck_stem}.jsonl"
    p = subprocess.run(
        [py, "tools/exhaustive_crossturn.py", "--deck", a.deck,
         "--seeds", ",".join(str(s) for s in usable),
         "--mode", "beam", "--beam", str(a.beam),
         "--trim-order", "plan", "--stages-file", a.stages_file,
         "--max-turn", str(a.max_turn), "--stage", str(a.stage),
         "--budget", str(a.budget), "--leaf-cap", str(a.leaf_cap),
         "--out", out_path],
        cwd=ROOT, capture_output=True, text=True, timeout=a.timeout)
    out = p.stdout + p.stderr
    results = {}
    for line in out.splitlines():
        m = re.search(r"seed(\d+) .* (KILL|NO-KILL|UNKNOWN|ERROR) "
                      r"kill_turn=(\d+|None) nodes=(\d+)", line)
        if m:
            results[int(m.group(1))] = (m.group(2),
                                        None if m.group(3) == "None"
                                        else int(m.group(3)),
                                        int(m.group(4)))
    ok = True
    for seed in usable:
        ref_kt = refs[seed]["start"]["dist"]
        fn = refs[seed]["frontier_nodes"]
        got = results.get(seed)
        if got is None:
            print(f"[gate-deck] seed{seed}: FAIL (beam の結果なし)",
                  flush=True)
            ok = False
            continue
        verdict, kt, nodes = got
        if ref_kt is not None:
            passed = verdict == "KILL" and kt == ref_kt
        else:
            passed = verdict == "NO-KILL"
        nodes_ok = fn is None or nodes <= fn
        passed = passed and nodes_ok
        ok = ok and passed
        print(f"[gate-deck] seed{seed}: {verdict} kill_turn={kt} "
              f"nodes={nodes} (frontier {fn}) -> "
              f"{'PASS' if passed else 'FAIL'}", flush=True)
    print(f"[gate-deck] RESULT: {'PASS' if ok else 'FAIL'} "
          f"({a.stages_file})", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
