#!/usr/bin/env python3
"""サイクル＋前提閉集合による候補提案の本実装（第2〜4層）の運転席。

手順:
    python3 tools/combo_hunt3_cycles.py build        # グラフ再構築（正準束）
    python3 tools/combo_hunt3_cycles.py generate     # 核列挙→閉集合→ファネル→候補
    python3 tools/combo_hunt3_cycles.py gate         # 健全性ゲート（対照の診断）
    python3 tools/combo_hunt3_cycles.py judge1 [--wave 400] [--workers 2]
    python3 tools/combo_hunt3_cycles.py judge2 [--workers 2]

成果物は ~/workspace/combo3/cycles_impl/ に逐次保存する（再開可能）。
判定はサブプロセス隔離（判定器の探索がメモリ・時間を食うため）。
段階1 = judge_engine_once（予算1000・シード1、上限900秒）、
段階2 = judge_engine3（上限1800秒）＋ 新規性判定 ＋ 変換判定（上限1200秒/件）。
アカシックの教訓（判定＋最小化の合計が上限を超えて未決着）から、段階2の上限は
最小化の実績（約300〜430秒）に余裕を持たせてある。
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path.home() / "workspace" / ".pylibs"))

OUT = Path.home() / "workspace" / "combo3" / "cycles_impl"
GRAPH_PKL = OUT / "graph.pkl"
CORES_JSONL = OUT / "cores.jsonl"
CANDS_JSONL = OUT / "candidates.jsonl"
GATE_JSON = OUT / "gate.json"
STAGE1_JSONL = OUT / "results_stage1.jsonl"
STAGE2_JSONL = OUT / "results_stage2.jsonl"
FEEDBACK_JSONL = OUT / "feedback.jsonl"
COMBO3 = Path.home() / "workspace" / "combo3"

TIMEOUT1 = 900          # 段階1（judge_engine_once）
TIMEOUT2 = 1800         # 段階2（judge_engine3: 判定＋最小化）
TIMEOUT_CONV = 1200     # 変換判定1件


def _env():
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{ROOT}:{Path.home() / 'workspace' / '.pylibs'}"
    # 判定は全カード（converted 含む）で読む。環境変数が「あれば」変換分を
    # 除く仕様なので、setdefault ではなく明示的に外す
    env.pop("DMSIM_SKIP_CONVERTED", None)
    return env


def _save_graph(g):
    OUT.mkdir(parents=True, exist_ok=True)
    with GRAPH_PKL.open("wb") as f:
        pickle.dump({"meta": g.meta, "nodes": g.nodes, "offsets": g.offsets,
                     "targets": g.targets, "statics": g.statics,
                     "enablers": g.enablers, "stats": g.stats, "rep": g.rep}, f)


def _load_graph():
    from dmsim.discovery.closedsets import CanonGraph
    with GRAPH_PKL.open("rb") as f:
        d = pickle.load(f)
    return CanonGraph(d["meta"], d["nodes"], d["offsets"], d["targets"],
                      d["statics"], d["enablers"], d["stats"], rep=d.get("rep"))


def _rep_map(rules) -> dict:
    """正準 ID → 収録されている代表印刷 ID（判定は実在の印刷 ID で行う）。"""
    from dmsim.cards.identity import canon_id
    from dmsim.engine import bundle_canon as BC
    rep: dict[str, str] = {}
    for b in BC.bundles(rules):
        rep.setdefault(canon_id(b.card), b.card)
    return rep


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def cmd_build(args):
    from dmsim.discovery.closedsets import build_graph
    rules = _rules()
    g = build_graph(rules)
    _save_graph(g)
    print(json.dumps(g.stats, ensure_ascii=False, indent=1))
    return 0


def cmd_generate(args):
    from dmsim.discovery.closedsets import (build_closed_sets, candidate_rank,
                                            funnel_evaluate, enumerate_cores)
    from dmsim.discovery.closedsets import CONTROL_SETS, control_species
    rules = _rules()
    g = _load_graph()
    if args.cores_from and Path(args.cores_from).exists():
        cores = [json.loads(l) for l in
                 Path(args.cores_from).read_text().splitlines() if l.strip()]
        cstats = {"loaded_from": args.cores_from, "distinct_cores": len(cores)}
        print(f"cores loaded from file: {len(cores)}", flush=True)
    else:
        cores, cstats = enumerate_cores(g, deg_cap=args.deg_cap)
    # 対照に関わる核（種が対照の種集合に含まれる核）を先に処理する
    # （生成が時間切れで打ち切られても健全性ゲートが判定できるように）
    ctrl_species = [set(control_species(c)) for c in CONTROL_SETS]
    cores.sort(key=lambda c: 0 if any(set(c["cards"]) <= s for s in ctrl_species)
               else 1)
    OUT.mkdir(parents=True, exist_ok=True)
    with CORES_JSONL.open("w") as f:
        for c in cores:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    from dmsim.discovery.closedsets import CONTROL_SETS as _CS
    must_include = set()
    for _c in _CS:
        must_include |= set(control_species(_c))
    # 逐次保存＋再開可能: 合格集合は核ごとに部分ファイルへ append し、
    # 進捗（処理済み核数・段階集計）は小さな JSON に残す。再起動で
    # プロセスが死んでも、同じコマンドの再実行で続きから再開する。
    partial_path = OUT / "candidates_partial.jsonl"
    progress_path = OUT / "gen_progress.json"
    stage_counts: Counter = Counter()
    n_sets = 0
    n_cores_done = 0
    if progress_path.exists() and not args.fresh:
        prog = json.loads(progress_path.read_text())
        n_cores_done = prog["cores_done"]
        n_sets = prog["n_sets"]
        stage_counts = Counter(prog["stage_counts"])
        print(f"resuming generate at core {n_cores_done} (sets={n_sets})",
              flush=True)
        partial = partial_path.open("a")
    else:
        partial = partial_path.open("w")
    truncated = False
    t0 = time.time()
    for idx, core in enumerate(cores):
        if idx < n_cores_done:
            continue
        if n_sets >= args.max_sets or time.time() - t0 > args.gen_seconds:
            truncated = True
            break
        for cand in build_closed_sets(g, rules, core, must_include=must_include):
            n_sets += 1
            ev = funnel_evaluate(g, rules, cand)
            stage_counts[ev["stage"] + (f":{ev['reason']}" if ev["reason"] else "")] += 1
            if ev["stage"] != "pass":
                continue
            rec = {"cards": cand["cards"], "core_cards": cand["core_cards"],
                   "bundles": cand["bundles"], "enabler": cand["enabler"],
                   "features": ev["features"],
                   "rank": list(candidate_rank(ev["features"]))}
            partial.write(json.dumps(rec, ensure_ascii=False) + "\n")
        partial.flush()
        n_cores_done = idx + 1
        if n_cores_done % 100 == 0:
            progress_path.write_text(json.dumps(
                {"cores_done": n_cores_done, "n_sets": n_sets,
                 "stage_counts": dict(stage_counts)}))
        if n_cores_done % 2000 == 0:
            print(f"  ...cores {n_cores_done}/{len(cores)} sets={n_sets} "
                  f"{round(time.time() - t0)}s", flush=True)
    partial.close()
    progress_path.write_text(json.dumps(
        {"cores_done": n_cores_done, "n_sets": n_sets,
         "stage_counts": dict(stage_counts)}))
    # 最終整形: 部分ファイルから種ごとに最良の見本を残し、層化してプール化
    kept: dict[tuple, dict] = {}
    with partial_path.open() as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            key = tuple(rec["cards"])
            rank = tuple(rec["rank"])
            cur = kept.get(key)
            if cur is None or rank < cur[0]:
                kept[key] = (rank, rec)
    # プールは種数ごとに層化して上限をかける（4種の対照が低種の洪水で
    # 埋もれないように）。生成自体は決定的なので、第2波は再生成で広げられる。
    by_species: dict[int, list] = {}
    for item in kept.values():
        by_species.setdefault(item[1]["features"]["n_species"], []).append(item)
    pool = []
    pool_info = {}
    for n, items in sorted(by_species.items()):
        items.sort(key=lambda kv: kv[0])
        pool_info[str(n)] = {"passing_species": len(items),
                             "kept": min(len(items), args.pool_per_stratum)}
        pool += items[: args.pool_per_stratum]
    # 対照に一致する候補は層の上限で落とさない（健全性ゲートの担保）
    from dmsim.discovery.closedsets import CONTROL_SETS, control_match
    in_pool = {tuple(c["cards"]) for _, c in pool}
    for rank, cand in kept.values():
        sp = tuple(cand["cards"])
        if sp not in in_pool and any(control_match(ctrl, sp)
                                     for ctrl in CONTROL_SETS):
            pool.append((rank, cand))
            in_pool.add(sp)
    pool.sort(key=lambda kv: kv[0])
    with CANDS_JSONL.open("w") as f:
        for _, cand in pool:
            f.write(json.dumps(cand, ensure_ascii=False) + "\n")
    summary = {"cores": cstats, "closed_sets": n_sets,
               "cores_processed": n_cores_done, "generate_truncated": truncated,
               "funnel": dict(stage_counts), "candidates": len(pool),
               "pool": pool_info,
               "species_hist": dict(Counter(c["features"]["n_species"] for _, c in pool)),
               "seconds": round(time.time() - t0, 1)}
    (OUT / "generate_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


def _pool_from_kept(kept: dict, pool_per_stratum: int):
    """種ごとに最良の見本だけが残った kept から、層化したプールを作る。"""
    from dmsim.discovery.closedsets import CONTROL_SETS, control_match
    by_species: dict[int, list] = {}
    for item in kept.values():
        by_species.setdefault(item[1]["features"]["n_species"], []).append(item)
    pool = []
    pool_info = {}
    for n, items in sorted(by_species.items()):
        items.sort(key=lambda kv: kv[0])
        pool_info[str(n)] = {"passing_species": len(items),
                             "kept": min(len(items), pool_per_stratum)}
        pool += items[:pool_per_stratum]
    in_pool = {tuple(c["cards"]) for _, c in pool}
    for rank, cand in kept.values():
        sp = tuple(cand["cards"])
        if sp not in in_pool and any(control_match(ctrl, sp)
                                     for ctrl in CONTROL_SETS):
            pool.append((rank, cand))
            in_pool.add(sp)
    pool.sort(key=lambda kv: kv[0])
    return pool, pool_info


def cmd_finalize(args):
    """逐次保存された部分ファイル（candidates_partial.jsonl）から
    候補プールを最終整形する。生成プロセスが途中で死んだ場合の復旧用。
    2パス方式（1パス目は順位と行番号だけを保持）でメモリを抑える。"""
    from dmsim.discovery.closedsets import CONTROL_SETS, control_match
    partial_path = OUT / "candidates_partial.jsonl"
    progress_path = OUT / "gen_progress.json"
    prog = json.loads(progress_path.read_text()) if progress_path.exists() else {}
    # 退化したドロー核の候補を除く（enumerate_cores 側の修正と同じ。
    # 部分ファイルは修正前の生成物なので、ここでも弾く）
    gmeta = None
    if GRAPH_PKL.exists():
        with GRAPH_PKL.open("rb") as f:
            gmeta = pickle.load(f)["meta"]
    n_draw_filtered = 0
    best: dict[tuple, tuple] = {}       # 種 -> (rank, 行番号)
    with partial_path.open() as f:
        for ln, line in enumerate(f):
            if not line.strip():
                continue
            rec = json.loads(line)
            if gmeta is not None and all(
                    (gmeta[b["i"]]["prem"] or {}).get("kind") == "draw"
                    for b in rec["bundles"] if b["role"] == "core"):
                n_draw_filtered += 1
                continue
            key = tuple(rec["cards"])
            rank = tuple(rec["rank"])
            cur = best.get(key)
            if cur is None or rank < cur[0]:
                best[key] = (rank, ln)
    # プールの上限は (種数, 核の長さ) の層ごとにかける。種数だけだと
    # 核1束の候補の洪水で、核2束（回転対のような形）が押し出される。
    # 層の判定には勝者行の features が要るので、行番号→層を先に引く
    # (best には層が無いため、部分ファイルの該当行から拾う)
    winner_lines = {ln: sp for sp, (_, ln) in best.items()}
    stratum_of: dict[int, tuple] = {}
    with partial_path.open() as f:
        for ln, line in enumerate(f):
            if ln in winner_lines:
                rec = json.loads(line)
                stratum_of[ln] = (rec["features"]["n_species"],
                                  rec["features"]["core_len"])
    winners = sorted(best.items(), key=lambda kv: kv[1][0])
    pool_info: dict[str, dict] = {}
    stratum_seen: Counter = Counter()
    stratum_total: Counter = Counter()
    for sp, (_, ln) in winners:
        stratum_total[stratum_of[ln]] += 1
    chosen: dict[int, tuple] = {}       # 行番号 -> (rank, 種)
    for sp, (rank, ln) in winners:
        st = stratum_of[ln]
        if stratum_seen[st] < args.pool_per_stratum:
            stratum_seen[st] += 1
            chosen[ln] = (rank, sp)
    for sp, (rank, ln) in winners:
        if ln not in chosen and any(control_match(c, sp) for c in CONTROL_SETS):
            chosen[ln] = (rank, sp)
    for st, total in sorted(stratum_total.items()):
        pool_info[str(st)] = {"passing_species": total,
                              "kept": stratum_seen[st]}
    recs: dict[int, dict] = {}
    with partial_path.open() as f:
        for ln, line in enumerate(f):
            if ln in chosen:
                recs[ln] = json.loads(line)
    ordered = sorted(chosen.items(), key=lambda kv: kv[1][0])
    with CANDS_JSONL.open("w") as f:
        for ln, _ in ordered:
            f.write(json.dumps(recs[ln], ensure_ascii=False) + "\n")
    summary = {"cores": {"distinct_cores": 201731},
               "closed_sets": prog.get("n_sets"),
               "cores_processed": prog.get("cores_done"),
               "generate_truncated": True,
               "funnel": prog.get("stage_counts", {}),
               "candidates": len(ordered), "pool": pool_info,
               "draw_core_filtered": n_draw_filtered,
               "species_hist": dict(Counter(len(sp) for _, (_, sp) in ordered)),
               "finalized_from_partial": True,
               "pool_strata": "(n_species, core_len)"}
    (OUT / "generate_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


def _gate_report(g, rules, candidates: list[dict] | None):
    from dmsim.discovery.closedsets import (CONTROL_SETS, control_match,
                                            control_species, trace_control)
    cand_species = ([tuple(c["cards"]) for c in candidates]
                    if candidates is not None else None)
    report = []
    for ctrl in CONTROL_SETS:
        species = control_species(ctrl)
        hit = (next((list(s) for s in cand_species if control_match(ctrl, s)), None)
               if cand_species is not None else None)
        entry = {"label": ctrl["label"], "species": list(species),
                 "in_candidates": hit is not None, "matched_species": hit}
        if not entry["in_candidates"]:
            entry["trace"] = trace_control(g, rules, ctrl)
        report.append(entry)
    return report


def cmd_gate(args):
    rules = _rules()
    g = _load_graph()
    cands = None
    if CANDS_JSONL.exists():
        cands = [json.loads(l) for l in CANDS_JSONL.read_text().splitlines() if l.strip()]
    report = _gate_report(g, rules, cands)
    GATE_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=1))
    ok = sum(1 for r in report if r["in_candidates"])
    print(f"gate: {ok}/{len(report)} controls in candidates")
    for r in report:
        if r["in_candidates"] is not True:
            print("  MISS", r["label"], "trace stage:",
                  (r.get("trace") or {}).get("stage"))
    return 0


# ---------------------------------------------------------------- サブプロセス判定

def _run_sub(mode: str, job: dict, timeout: int) -> dict:
    p = subprocess.run([sys.executable, str(Path(__file__).resolve()), mode],
                       input=json.dumps(job), capture_output=True, text=True,
                       timeout=timeout, env=_env(), cwd=str(ROOT))
    if p.returncode != 0:
        raise RuntimeError(f"subprocess failed: {p.stderr[-1500:]}")
    return json.loads(p.stdout.strip().splitlines()[-1])


def mode_one():
    job = json.loads(sys.stdin.read())
    from dmsim.discovery import hunt3
    from dmsim.discovery.hunt3 import bundles_by_card  # hunt2 由来の再輸出
    rules = _rules()
    rep = _rep_map(rules)
    cards = {rep[cid]: 2 for cid in job["cards"]}
    r = hunt3.judge_engine_once(rules, cards, bundles_by_card(rules),
                                budget=job.get("budget", 1000),
                                seeds=(job.get("seed", 1),))
    print(json.dumps({"pass": r["pass"], "kinds": r["kinds"], "delta": r["delta"],
                      "win_by": r["win_by"], "grown": r["grown"],
                      "evidence": r["evidence"], "own_turns": r["own_turns"],
                      "rows": r["rows"]}, ensure_ascii=False))
    return 0


def mode_one3():
    job = json.loads(sys.stdin.read())
    from dmsim.discovery import hunt3
    from dmsim.discovery.hunt3 import bundles_by_card  # hunt2 由来の再輸出
    rules = _rules()
    rep = _rep_map(rules)
    cards = {rep[cid]: 2 for cid in job["cards"]}
    r = hunt3.judge_engine3(rules, cards, bundles_by_card(rules),
                            budget=job.get("budget", 1000),
                            seeds=(job.get("seed", 1),))
    print(json.dumps({"pass": r["pass"], "core": r["core"], "delta": r["delta"],
                      "kinds": r["kinds"], "evidence": r["evidence"],
                      "necessity": r["necessity"], "ablations": r["ablations"],
                      "rows": r["rows"]}, ensure_ascii=False))
    return 0


def mode_one_conv():
    job = json.loads(sys.stdin.read())
    from dmsim.discovery import hunt3
    from dmsim.discovery.hunt3 import bundles_by_card  # hunt2 由来の再輸出
    rules = _rules()
    core = {k: v for k, v in job["core"].items()}
    r = hunt3.judge_conversion3(rules, core, [job["card"]], bundles_by_card(rules),
                                engine_budget=1000, conv_budget=1000,
                                delta=job["delta"], seeds=(1, 2))
    print(json.dumps({"card": job["card"], "pass": r["pass"], "rows": r["rows"]},
                     ensure_ascii=False))
    return 0


# ---------------------------------------------------------------- 段階判定

def _done_keys(path: Path) -> set:
    if not path.exists():
        return set()
    return {json.loads(l)["key"] for l in path.read_text().splitlines() if l.strip()}


def _prior_judged_species() -> set[tuple]:
    """構造署名の提案で判定済みの種集合（再判定しない）。"""
    from dmsim.cards.identity import canon_id
    out = set()
    for name in ("proposals_struct.jsonl", "proposals_struct_xenarch.jsonl",
                 "proposals_struct_akashic.jsonl"):
        p = COMBO3 / name
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            if line.strip():
                cards = json.loads(line)["cards"]
                out.add(tuple(sorted(canon_id(c) for c in cards)))
    return out


def _fail_reason(r1: dict) -> str:
    if r1.get("error"):
        return "error"
    if r1.get("timeout"):
        return "timeout"
    if r1["pass"]:
        return "pass"
    loops = [lp for row in r1.get("rows", []) for lp in row.get("loops", [])]
    if not loops:
        return "no_regression_detected"       # グラフと判定の不一致の主信号
    return "regression_without_gain"


def cmd_judge1(args):
    from dmsim.discovery.closedsets import CONTROL_SETS, control_match
    cands = [json.loads(l) for l in CANDS_JSONL.read_text().splitlines() if l.strip()]
    prior = _prior_judged_species()
    done = _done_keys(STAGE1_JSONL)
    n_skip = Counter()
    todo = []
    for i, c in enumerate(cands):
        key = ",".join(c["cards"])
        if key in done:
            continue
        species = tuple(c["cards"])
        if any(control_match(ctrl, species) for ctrl in CONTROL_SETS):
            n_skip["control"] += 1             # 対照は判定対象外（ゲートで確認済み）
            continue
        if species in prior:
            n_skip["prior_judged"] += 1        # 構造署名の提案で判定済み
            continue
        todo.append((i, key, c))
    print(f"skipped: {dict(n_skip)}", flush=True)
    todo = todo[: args.wave]
    print(f"stage1: {len(todo)} to judge (wave={args.wave}, done={len(done)})",
          flush=True)
    s1f = STAGE1_JSONL.open("a")
    fbf = FEEDBACK_JSONL.open("a")

    def run(item):
        i, key, c = item
        t0 = time.time()
        try:
            r = _run_sub("--one", {"cards": c["cards"]}, TIMEOUT1)
            rec = {"key": key, "cards": c["cards"], "pass": r["pass"],
                   "delta": r["delta"], "kinds": r["kinds"],
                   "features": c["features"], "seconds": round(time.time() - t0, 1),
                   "rows": r["rows"]}
        except subprocess.TimeoutExpired:
            rec = {"key": key, "cards": c["cards"], "pass": False, "timeout": True,
                   "features": c["features"], "seconds": TIMEOUT1}
        except Exception as e:  # noqa: BLE001 - 判定の失敗は記録して続行する
            rec = {"key": key, "cards": c["cards"], "pass": False,
                   "error": str(e)[:300], "features": c["features"],
                   "seconds": round(time.time() - t0, 1)}
        rec["fail_reason"] = _fail_reason(rec)
        return rec

    npass = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run, item): item for item in todo}
        for fut in as_completed(futs):
            rec = fut.result()
            npass += 1 if rec["pass"] else 0
            s1f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            s1f.flush()
            fbf.write(json.dumps({"key": rec["key"], "cards": rec["cards"],
                                  "stage1_pass": rec["pass"],
                                  "fail_reason": rec["fail_reason"],
                                  "delta": rec.get("delta"),
                                  "features": rec["features"]},
                                 ensure_ascii=False) + "\n")
            fbf.flush()
            print(f"[{rec['key']}] pass={rec['pass']} reason={rec['fail_reason']}",
                  flush=True)
    print(f"stage1 done: pass {npass}/{len(todo)}")
    return 0


#: 既知エンジン（最小コア, 増分）。新規性の判定に使う（正準 ID に直して比較）。
KNOWN_ENGINES = [
    ({"dm22ex2-021": 2}, {"deck:0": -1, "graveyard:0": 1}),
    ({"dm22ex2-021": 2, "dm22rp2x-004": 2}, {"deck:0": -1, "hand:0": 1}),
    ({"dm23ex2-009": 1, "dm23bd7-035": 2, "dm24ex1-038": 1, "dmrp12-s01": 1},
     {"deck:1": -1, "graveyard:1": 1}),
    ({"dm23ex2-009": 1, "dm23bd7-035": 2, "dmrp12-s01": 1, "dm26ex3-047": 1},
     {"deck:0": -1, "hand:0": 1}),
    ({"dm23ex2-009": 1, "dm23bd7-035": 2, "dmrp12-s01": 1, "dm26ex3-081": 1},
     {"deck:0": -1, "mana:0": 1}),
    ({"dm23ex2-009": 1, "dm23bd7-035": 2, "dmrp12-s01": 1, "dmrp13-016": 1},
     {"deck:0": -1, "hand:0": 1}),
    ({"dm23ex2-009": 1, "dm23bd7-035": 2, "dmrp08-s01": 1},
     {"deck:0": -1, "shield:0": 1}),
] + [({"dm22ex2-021": 2, cid: 2}, {"deck:0": -1, "hand:0": 1}) for cid in (
    "dmd05-009", "dmr11-029", "dmr13-091", "dmrp04s-077",
    "dmrp19-046", "dmrp19-066", "dmrp20-068")]


def _is_known(core: dict, delta: dict) -> bool:
    from dmsim.cards.identity import canon_id
    core_c = {canon_id(k): v for k, v in core.items()}
    for kc, kd in KNOWN_ENGINES:
        if {canon_id(k): v for k, v in kc.items()} == core_c and kd == delta:
            return True
    return False


def cmd_judge2(args):
    from dmsim.discovery import hunt3
    passed = [json.loads(l) for l in STAGE1_JSONL.read_text().splitlines()
              if l.strip() and json.loads(l)["pass"]]
    done = _done_keys(STAGE2_JSONL)
    todo = [r for r in passed if r["key"] not in done]
    print(f"stage2: {len(todo)} to minimize (done={len(done)})", flush=True)
    s2f = STAGE2_JSONL.open("a")
    rules = _rules()
    catalog = hunt3.conversion_catalog3(rules, hunt3.bundles_by_card(rules))

    def run(rec):
        t0 = time.time()
        out = {"key": rec["key"], "cards": rec["cards"]}
        try:
            r3 = _run_sub("--one3", {"cards": rec["cards"]}, TIMEOUT2)
        except subprocess.TimeoutExpired:
            return {**out, "stage2": "timeout", "seconds": TIMEOUT2}
        except Exception as e:  # noqa: BLE001
            return {**out, "stage2": "error", "error": str(e)[:300],
                    "seconds": round(time.time() - t0, 1)}
        out.update({"stage2": "ok", "pass": r3["pass"], "core": r3["core"],
                    "delta": r3["delta"], "kinds": r3["kinds"],
                    "necessity": r3["necessity"],
                    "seconds": round(time.time() - t0, 1)})
        if not r3["pass"] or not r3["core"]:
            out["novel"] = False
            return out
        out["novel"] = not _is_known(r3["core"], r3["delta"])
        if out["novel"]:
            convs = []
            for card in hunt3.pair_conversions3(r3["delta"], r3["kinds"],
                                                catalog, limit=4):
                try:
                    rc = _run_sub("--one-conv",
                                  {"core": r3["core"], "card": card["card"],
                                   "delta": r3["delta"]}, TIMEOUT_CONV)
                    convs.append({"card": card, "pass": rc["pass"]})
                except subprocess.TimeoutExpired:
                    convs.append({"card": card, "pass": False, "timeout": True})
                except Exception as e:  # noqa: BLE001
                    convs.append({"card": card, "pass": False,
                                  "error": str(e)[:200]})
            out["conversions"] = convs
        return out

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run, r): r for r in todo}
        for fut in as_completed(futs):
            rec = fut.result()
            s2f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            s2f.flush()
            print(f"[{rec['key']}] stage2={rec['stage2']} novel={rec.get('novel')}",
                  flush=True)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("build")
    fin = sub.add_parser("finalize")
    fin.add_argument("--pool-per-stratum", type=int, default=8_000,
                     help="(種数, 核の長さ) の層ごとの上限")
    # 同名オプションが generate 側にもあるため、既定値は set_defaults で固定する
    fin.set_defaults(pool_per_stratum=8_000)
    g = sub.add_parser("generate")
    g.add_argument("--deg-cap", type=int, default=400)
    g.add_argument("--cores-from", default=None,
                   help="列挙済みの核 JSONL から再開する（列挙を省く）")
    g.add_argument("--fresh", action="store_true",
                   help="逐次保存した生成進捗を捨てて最初から")
    g.add_argument("--max-sets", type=int, default=12_000_000)
    g.add_argument("--gen-seconds", type=int, default=3600)
    g.add_argument("--pool-per-stratum", type=int, default=25_000)
    sub.add_parser("gate")
    j1 = sub.add_parser("judge1")
    j1.add_argument("--wave", type=int, default=400)
    j1.add_argument("--workers", type=int, default=2)
    j2 = sub.add_parser("judge2")
    j2.add_argument("--workers", type=int, default=2)
    args = ap.parse_args(argv)
    if args.cmd == "build":
        return cmd_build(args)
    if args.cmd == "finalize":
        return cmd_finalize(args)
    if args.cmd == "generate":
        return cmd_generate(args)
    if args.cmd == "gate":
        return cmd_gate(args)
    if args.cmd == "judge1":
        return cmd_judge1(args)
    if args.cmd == "judge2":
        return cmd_judge2(args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--one":
        sys.exit(mode_one())
    if len(sys.argv) > 1 and sys.argv[1] == "--one3":
        sys.exit(mode_one3())
    if len(sys.argv) > 1 and sys.argv[1] == "--one-conv":
        sys.exit(mode_one_conv())
    sys.exit(main())
