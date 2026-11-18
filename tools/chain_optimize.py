"""最適化ループ: 鎖の生成→ゲート→自動調整を回す
（docs/chain-from-frontier-plan.md §4）。

抽出器 v2 のパラメータ（閾値の分位・特徴の集合・負例フィルタの強さ）を
変えて候補の鎖を作り、鎖ゲート（chain_gate: 診断＋保持テスト）で測る。
全試行を results.jsonl に残し（勝った候補だけを残さない）、最後に
「PASS の中で最も単純（条件数が少ない）な鎖」を best として出す。

過適合への歯止め:
- ゲートのケース（hidden / prep）は材料の探索と別シナリオであることが
  前提（ホールドアウト）。材料のストアが hidden / prep の場合は警告する。
- 単純さ優先: 同じ PASS なら条件の少ない鎖を採る。細かい条件の
  積み増しでゲートだけを通す鎖を作らない。
- 試行回数に上限を置く（--max-tries）。

使い方:
  python3 tools/chain_optimize.py --store logs/label_doom_e/<case> \
      --workdir /tmp/chain_opt1 --max-tries 6
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent

GRID = [
    {"quantile": q, "features": f, "neg_ratio": n}
    for q, f, n in itertools.product(
        (0.0, 0.1, 0.25), ("all", "star"), (0.9, 0.7))
]


def run_gate(stages_file: Path, timeout: int) -> dict:
    p = subprocess.run(
        [sys.executable, "tools/chain_gate.py",
         "--stages-file", str(stages_file)],
        cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    out = p.stdout + p.stderr
    m = re.search(r"\[gate\] RESULT: (PASS|FAIL)", out)
    diag = re.search(r"\[gate\] diag: .*frac-ranks=\[([^\]]*)\]", out)
    nodes = [int(x) for x in re.findall(r"nodes=(\d+)", out)]
    return {"gate_pass": bool(m and m.group(1) == "PASS"),
            "diag_ranks": diag.group(1) if diag else None,
            "beam_nodes_total": sum(nodes) if nodes else None,
            "raw_tail": out[-500:]}


def run_gate_deck(stages_file: Path, timeout: int, a) -> dict:
    """デッキ用ゲート（chain_gate_deck）: ホールドアウトシードの
    ラベルを基準に beam4 + plan のキルターンを照らす。"""
    p = subprocess.run(
        [sys.executable, "tools/chain_gate_deck.py",
         "--stages-file", str(stages_file),
         "--deck", a.deck, "--ref-store-dir", a.ref_store_dir,
         "--seeds", a.holdout_seeds,
         "--max-turn", str(a.max_turn), "--stage", str(a.stage),
         "--timeout", str(timeout)],
        cwd=ROOT, capture_output=True, text=True, timeout=timeout + 300)
    out = p.stdout + p.stderr
    m = re.search(r"\[gate-deck\] RESULT: (PASS|FAIL)", out)
    nodes = [int(x) for x in re.findall(
        r"\[gate-deck\] seed\d+: (?:KILL|NO-KILL|UNKNOWN|ERROR) "
        r"kill_turn=\S+ nodes=(\d+)", out)]
    return {"gate_pass": bool(m and m.group(1) == "PASS"),
            "diag_ranks": None,
            "beam_nodes_total": sum(nodes) if nodes else None,
            "raw_tail": out[-500:]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True,
                    help="材料ストア。カンマ区切りで複数指定すると合算")
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--max-tries", type=int, default=6)
    ap.add_argument("--gate-timeout", type=int, default=3600)
    ap.add_argument("--gate", choices=["scenario", "deck"],
                    default="scenario",
                    help="deck: ホールドアウトシードのラベルで判定する")
    ap.add_argument("--deck", default="data/decks/saga_doom_e.yaml")
    ap.add_argument("--ref-store-dir", default=None,
                    help="deck ゲート用: chain_label の --store-dir")
    ap.add_argument("--holdout-seeds", default=None,
                    help="deck ゲート用: 検証用シード（カンマ区切り）")
    ap.add_argument("--max-turn", type=int, default=3)
    ap.add_argument("--stage", type=int, default=2)
    a = ap.parse_args(argv)
    if a.gate == "deck" and not (a.ref_store_dir and a.holdout_seeds):
        ap.error("--gate deck には --ref-store-dir と --holdout-seeds "
                 "が必要です")

    store = Path(a.store)
    if any(s in store.name for s in ("hidden", "prep")):
        print("警告: 材料のストアがゲートと同じシナリオの可能性があります"
              "（ホールドアウトが崩れます）", flush=True)
    wd = Path(a.workdir)
    wd.mkdir(parents=True, exist_ok=True)
    results_path = wd / "results.jsonl"
    tried = 0
    if results_path.exists():
        tried = len(results_path.read_text(encoding="utf-8").splitlines())
    best = None
    with results_path.open("a", encoding="utf-8") as rf:
        for i, params in enumerate(GRID):
            if i < tried:
                continue
            if i >= a.max_tries:
                break
            tag = (f"cand{i}_q{params['quantile']}_{params['features']}"
                   f"_n{params['neg_ratio']}")
            stages_file = wd / f"{tag}.yaml"
            report_file = wd / f"{tag}.report.json"
            p = subprocess.run(
                [sys.executable, "tools/chain_extract2.py",
                 "--store", str(store), "--out", str(stages_file),
                 "--report", str(report_file),
                 "--quantile", str(params["quantile"]),
                 "--features", params["features"],
                 "--neg-ratio", str(params["neg_ratio"])],
                cwd=ROOT, capture_output=True, text=True, timeout=1200)
            if p.returncode != 0:
                rec = {"tag": tag, "params": params, "error": "extract_failed",
                       "raw_tail": (p.stdout + p.stderr)[-500:]}
                rf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                rf.flush()
                print(f"[{tag}] extract failed", flush=True)
                continue
            rep = json.loads(report_file.read_text(encoding="utf-8"))
            conditions = sum(s["conditions"] for s in rep["stages"])
            gate = (run_gate_deck(stages_file, a.gate_timeout, a)
                    if a.gate == "deck"
                    else run_gate(stages_file, a.gate_timeout))
            rec = {"tag": tag, "params": params,
                   "stages": len(rep["stages"]), "conditions": conditions,
                   **gate}
            rf.write(json.dumps(rec, ensure_ascii=False) + "\n")
            rf.flush()
            print(f"[{tag}] stages={rec['stages']} cond={conditions} "
                  f"gate={'PASS' if gate['gate_pass'] else 'FAIL'} "
                  f"diag={gate['diag_ranks']} nodes={gate['beam_nodes_total']}",
                  flush=True)
            if gate["gate_pass"]:
                key = (conditions, gate["beam_nodes_total"] or 10 ** 18)
                if best is None or key < best[0]:
                    best = (key, tag, stages_file)
    if best is not None:
        shutil.copy(best[2], wd / "best_stages.yaml")
        print(f"best: {best[1]} -> {wd / 'best_stages.yaml'}", flush=True)
    else:
        print("best: なし（PASS した候補なし）。全試行は results.jsonl を参照",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
