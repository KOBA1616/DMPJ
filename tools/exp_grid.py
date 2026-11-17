"""比較実験のグリッドランナー: YAML 定義の走行一覧を順に実行し、比較表を出す。

docs/search-and-foundation-plan.md フェーズ3「比較実験のグリッドランナー」。
これまで順序×段×beam 幅などの比較をシェルの直列実行で組んでいたのを定型化する。

定義ファイルの形式（tools/grid_example.yaml がサンプル）:

  runs:
    - label: hidden_beam4_ruler       # ログ名と表の列名になる一意な名前
      tool: exhaustive_crossturn      # exhaustive_crossturn / exhaustive_multiturn / exhaustive_proto
      args: {setup: tests/saga_hidden_setup.yaml, seeds: "1,2", mode: beam, beam: 4, trim_order: ruler}

args のキーはアンダースコアをハイフンに変えて --key value として渡す
（trim_order → --trim-order）。値が true のキーはフラグだけ渡し、false は渡さない。
リストはカンマ連結にする（seeds や stages の流儀に合わせる）。
--out は定義側では指定せず、ランナーが logs/grid/<label>.jsonl を渡す。

パラメータスイープは専用機能を持たず、「1つのパラメータだけが違う run の並び」
として定義に書く。走行が全て終わると、ケース×run の比較表
（verdict / kill_turn / nodes）を標準出力に出す。

使い方:
  python tools/exp_grid.py tools/grid_example.yaml
  python tools/exp_grid.py tools/grid_example.yaml --dry-run   # コマンドだけ表示
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ("exhaustive_crossturn", "exhaustive_multiturn", "exhaustive_proto")


def build_command(run: dict, out_path: str) -> list[str]:
    """run 定義 → 実行コマンド。args の写像はモジュール docstring の通り。"""
    args = dict(run.get("args") or {})
    args.pop("out", None)  # --out はランナーが決める
    cmd = [sys.executable, f"tools/{run['tool']}.py"]
    for key, value in args.items():
        flag = "--" + str(key).replace("_", "-")
        if value is True:
            cmd.append(flag)
        elif value is False or value is None:
            continue
        elif isinstance(value, (list, tuple)):
            cmd += [flag, ",".join(str(v) for v in value)]
        else:
            cmd += [flag, str(value)]
    cmd += ["--out", out_path]
    return cmd


def case_key(case: str) -> str:
    """run をまたいでケースを対応づけるキー。crossturn はケース名の末尾に
    その run の mode/beam が付く（例: "... T3 beam4"）ので、それを落とす。"""
    return re.sub(r" (frontier|beam\d+)$", "", case)


def summarize_log(path: Path) -> dict[str, tuple[str, int | None, int | None]]:
    """ログ JSONL → {ケースキー: (verdict, kill_turn, nodes)}。
    multiturn は case_result に kill_turn / nodes が無く stage_result 側にあるので補う
    （nodes は段の合計）。case_start だけで終わったケースは unfinished とする。"""
    out: dict[str, tuple[str, int | None, int | None]] = {}
    stage_rows: dict[str, list[dict]] = {}
    started: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        kind = r.get("kind")
        if kind == "case_start":
            started.append(r["case"])
        elif kind == "stage_result":
            stage_rows.setdefault(r["case"], []).append(r)
        elif kind == "case_result":
            kt = r.get("kill_turn")
            nodes = r.get("nodes")
            for s in stage_rows.get(r["case"], []):
                if kt is None and s.get("kill_turn") is not None:
                    kt = s["kill_turn"]
                if nodes is None and s.get("nodes") is not None:
                    nodes = (nodes or 0) + s["nodes"]
            out[case_key(r["case"])] = (r.get("verdict") or "?", kt, nodes)
    for case in started:
        out.setdefault(case_key(case), ("unfinished", None, None))
    return out


def fmt_cell(summary: tuple[str, int | None, int | None] | None) -> str:
    if summary is None:
        return "-"
    verdict, kt, nodes = summary
    cell = verdict
    if kt is not None:
        cell += f"/T{kt}"
    if nodes is not None:
        cell += f"/{nodes}n"
    return cell


def print_table(runs: list[dict], summaries: dict[str, dict]) -> None:
    cases: list[str] = []
    for run in runs:
        for case in summaries[run["label"]]:
            if case not in cases:
                cases.append(case)
    labels = [run["label"] for run in runs]
    widths = [max([len(c) for c in cases] + [4])]
    for label in labels:
        widths.append(max([len(label)] + [len(fmt_cell(summaries[label].get(c))) for c in cases]))
    print("\n=== 比較表（verdict/kill_turn/nodes） ===")
    print("case".ljust(widths[0]) + "  " + "  ".join(l.ljust(w) for l, w in zip(labels, widths[1:])))
    print("-" * (sum(widths) + 2 * len(labels)))
    for case in cases:
        row = [fmt_cell(summaries[label].get(case)) for label in labels]
        print(case.ljust(widths[0]) + "  " + "  ".join(c.ljust(w) for c, w in zip(row, widths[1:])))
    print()
    for label in labels:
        s = summaries[label]
        kills = sum(1 for v, _kt, _n in s.values() if v.startswith("kill"))
        total_nodes = sum(n for _v, _kt, n in s.values() if n is not None)
        print(f"{label}: cases={len(s)} kill={kills} total_nodes={total_nodes} "
              f"(log: logs/grid/{label}.jsonl)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("definition", nargs="?", default="tools/grid_example.yaml",
                    help="走行定義の YAML（runs: の下に label / tool / args）")
    ap.add_argument("--dry-run", action="store_true", help="コマンドを表示するだけ（実行しない）")
    a = ap.parse_args()

    spec = yaml.safe_load(Path(a.definition).read_text(encoding="utf-8"))
    runs = spec["runs"] if isinstance(spec, dict) else spec
    labels = [run["label"] for run in runs]
    if len(set(labels)) != len(labels):
        print("label が重複している", file=sys.stderr)
        return 1
    for run in runs:
        if run["tool"] not in TOOLS:
            print(f"{run['label']}: tool は {TOOLS} のいずれか（{run['tool']}）", file=sys.stderr)
            return 1

    grid_dir = ROOT / "logs" / "grid"
    grid_dir.mkdir(parents=True, exist_ok=True)
    failed = False
    summaries: dict[str, dict] = {}
    for run in runs:
        label = run["label"]
        safe = re.sub(r"[^0-9A-Za-z_.-]+", "_", label)
        out_rel = f"logs/grid/{safe}.jsonl"
        cmd = build_command(run, out_rel)
        print(f"\n### {label}: {' '.join(cmd)}", flush=True)
        if a.dry_run:
            summaries[label] = {}
            continue
        p = subprocess.run(cmd, cwd=ROOT)
        if p.returncode != 0:
            print(f"### {label}: FAILED (exit {p.returncode})", flush=True)
            failed = True
        log_path = ROOT / out_rel
        summaries[label] = summarize_log(log_path) if log_path.exists() else {}
    if not a.dry_run:
        print_table(runs, summaries)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
