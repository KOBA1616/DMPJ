"""ターン横断探索（試作）: ターン境界で分岐を保持し、貪欲確定方式の見逃しを測る物差し。

従来の複数ターン方式（game.play_game）は、各ターンで TurnSearch が返した最良の
ターン終了局面を1つだけ確定して次ターンへ進む。本ツールはターン終了局面を
複数保持する:

  - mode=frontier: 到達したターン終了局面を digest で重複排除して全て保持
    （上限 FRONTIER_CAP を超えたら打ち切り＝ capped として記録し、判定は unknown）
  - mode=beam: 評価 V の上位 k 件だけ保持（k=1 が従来の貪欲方式に相当）

1ターン内の展開は TurnSearch._search と同じ規則（seen による抽象状態の統合、
ループ証明書の fast_forward、候補生成は exhaustive_proto の段方式）で全ての葉を
集める。相手は無抵抗（チャージのみ）、ロック判定はしない。

判定の主張範囲はケースの scope（シナリオ配置／デッキ・シード／ターン数）の中だけ。
frontier が打ち切られず、ノード予算も使い切らなかった場合だけ no-kill が証明になる。

使い方:
  python tools/exhaustive_crossturn.py --setup tests/saga_prep_setup.yaml --seeds 1,2,3 \
      --mode frontier --max-turn 3 --stage 1
  python tools/exhaustive_crossturn.py --setup tests/saga_prep_setup.yaml --seeds 1 \
      --mode beam --beam 8 --max-turn 3
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

from dmsim import load_rules  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
from dmsim.engine.loop import abstract, verify  # noqa: E402
from dmsim.search import turn  # noqa: E402
from dmsim.search.turn import Detectors, TurnSearch, _is_burn, _is_engine  # noqa: E402
from dmsim.plan.macro import MacroPlanner, load_stage_file, stage_fraction  # noqa: E402
from dmsim.search.leaf_eval import WIN, Weights, evaluate  # noqa: E402
from exhaustive_proto import STAGES, _make_stage_search, cfg_suffix, stage_candidates  # noqa: E402
from order_fn import ruler_key  # noqa: E402

_W = Weights()
_PLANNER: MacroPlanner | None = None


def _trim_score(mode: str, eng) -> tuple:
    """ターン境界で保持する局面の順序スコア（次ターン開始局面で測る）。
    plan: 大局観の Plan の充足率（stage_fraction）を主軸にし、同点は順序関数 v2 で解く。"""
    if mode == "plan":
        plan = _PLANNER.plan(eng, 0)
        return (stage_fraction(eng, 0, plan),) + ruler_key(eng, 0)
    return ruler_key(eng, 0) if mode == "ruler" else (evaluate(eng, 0, _W),)

FRONTIER_CAP = 64        # frontier モードで保持する局面数の上限（超えたら capped）
LEAF_CAP = 4000          # 1局面・1ターンあたりに集める葉の上限


class _CapReached(Exception):
    pass


class LeafCollector:
    """TurnSearch._search と同じ規則で、ターン終了の葉を全て集める。"""

    def __init__(self, ts: TurnSearch):
        self.ts = ts
        self.leaves: list[tuple[float, object, tuple]] = []
        self.truncated = False

    def collect(self, eng, node_budget: int):
        ts = self.ts
        ts.left = node_budget
        ts._la_left = turn.ROLLOUT_TOTAL
        ts._rf = turn.REPEAT_FIRST if ts.repeat_first is None else ts.repeat_first
        ts._deadline = None
        ts._root_log = len(eng.log)
        ts.seen = set()
        ts._macro_nodes = 0
        ts.stats = turn.TurnStats()
        self.leaves = []
        self.truncated = False
        det = Detectors.new(eng, ts.me, ts.draw_discard)
        try:
            self._rec(eng.clone(), det)
        except _CapReached:
            self.truncated = True
        return self.leaves, self.truncated, ts.stats.nodes

    def _add_leaf(self, value, eng, loops):
        self.leaves.append((value, eng, loops))
        if len(self.leaves) >= LEAF_CAP:
            raise _CapReached

    def _rec(self, eng, det):
        ts = self.ts
        d = ts._settle(eng)
        if d is None:
            self._add_leaf(ts._eval(eng), eng, ())
            return
        if ts.left <= 0:
            self.truncated = True
            leaf = ts._rollout(eng)
            self._add_leaf(ts._eval(leaf), leaf, ())
            return
        h, ctr = abstract(eng, "in_turn")
        ex = eng.tkey_extra() if hasattr(eng, "tkey_extra") else None
        if ex is not None:
            mana_left, sizes = ex
        else:
            mana_left = tuple(sorted((c.defn, c.tapped) for c in (eng.s.cards[x] for p in (0, 1) for x in eng.s.zones["mana"][p])))
            sizes = tuple(len(eng.s.zones[z][p]) for p in (0, 1) for z in ("hand", "shield", "graveyard", "bz"))
        tkey = (h, tuple(sorted(ctr.items())), mana_left, sizes)
        cert = det.observe(eng)
        if cert is not None and ts.collect is not None:
            return                      # ループ発見モードは使わない
        if cert is not None and _is_burn(cert, ts.me) and not ts.burn_stock:
            cert = None
        elif cert is not None and verify(eng, cert, times=1).verified < 1:
            cert = None
        elif cert is not None:
            got = False
            for ff, lp in ts._stocks(eng, cert):
                got = True
                self._rec(ff, Detectors.new(ff, ts.me, ts.draw_discard))
            if got:
                return
            if _is_engine(cert, ts.me) and not _is_burn(cert, ts.me):
                self._add_leaf(ts._eval(eng), eng, ())   # 資源ループはストックし切った局面を葉として残す
                return
            cert = None
        if tkey in ts.seen:
            return
        ts.seen.add(tkey)
        for child, lp in ts._macro_children(eng, d):
            ts.left -= 1
            ts.stats.nodes += 1
            self._rec(child, det.fork())
        cands = turn.candidates(eng, d, ts.w, ts.combo_cap)
        if ts.w.lookahead and len(cands) > 1:
            cands = ts._lookahead_order(eng, cands)
        if ts._rf and len(cands) > 1:
            cands = ts._repeat_order(eng, d, cands)
        for choice in cands:
            if ts.left <= 0:
                self.truncated = True
                break
            ts.left -= 1
            ts.stats.nodes += 1
            child = eng.clone()
            child.answer(choice)
            self._rec(child, det.fork())


def advance_to_my_turn(eng, me: int = 0):
    """ターン終了局面から、相手ターン（チャージのみ）を挟んで自分の次の決定点まで進める。
    対局が終わっていたら None。"""
    e = eng.clone()
    for _ in range(10000):
        if e.s.result is not None:
            return None
        d = e.advance()
        if d is None:
            return None
        if e.s.active == me and d["player"] == me:
            return e
        e.answer(turn.charge_only_policy(e, d))
    return None


def run_case(rules, setup: dict, *, max_turn: int, mode: str, beam: int,
             stage: int, order: str, node_budget: int, trim_order: str = "value"):
    st = next(s for s in STAGES if s["stage"] == stage)
    fn, _label = stage_candidates(order, stage)
    orig = turn.candidates
    turn.candidates = fn
    try:
        search_cls = _make_stage_search(st["stock_offsets"])
        start = sc.build(rules, setup)
        frontier = [start]
        total_nodes = 0
        capped = False
        truncated_any = False
        frontier_sizes = []
        for t in range(1, max_turn + 1):
            nxt: dict[str, tuple[float, object]] = {}
            for st_eng in frontier:
                ts = search_cls(0, budget=node_budget)
                leaves, trunc, nodes = LeafCollector(ts).collect(st_eng, node_budget)
                total_nodes += nodes
                truncated_any = truncated_any or trunc
                for v, leaf, _loops in leaves:
                    r = leaf.s.result
                    if r is not None and r.get("winner") == 0:
                        return {"verdict": "kill", "kill_turn": t, "kill_by": r.get("reason"),
                                "nodes": total_nodes, "frontier_sizes": frontier_sizes,
                                "capped": capped, "truncated": truncated_any, "final": leaf}
                    nxt_eng = advance_to_my_turn(leaf)
                    if nxt_eng is not None:
                        key = nxt_eng.s.digest()
                        s = _trim_score(trim_order, nxt_eng)
                        if key not in nxt or s > nxt[key][0]:
                            nxt[key] = (s, nxt_eng)
            frontier_sizes.append(len(nxt))
            if not nxt:
                verdict = "no-kill" if not (capped or truncated_any) else "unknown"
                return {"verdict": verdict, "kill_turn": None, "kill_by": None,
                        "nodes": total_nodes, "frontier_sizes": frontier_sizes,
                        "capped": capped, "truncated": truncated_any, "final": None}
            states = sorted(nxt.values(), key=lambda x: x[0], reverse=True)
            keep = beam if mode == "beam" else FRONTIER_CAP
            if len(states) > keep:
                if mode == "frontier":
                    capped = True
                states = states[:keep]
            frontier = [e for _v, e in states]
        verdict = "no-kill" if not (capped or truncated_any) else "unknown"
        return {"verdict": verdict, "kill_turn": None, "kill_by": None,
                "nodes": total_nodes, "frontier_sizes": frontier_sizes,
                "capped": capped, "truncated": truncated_any, "final": None}
    finally:
        turn.candidates = orig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", default="tests/saga_prep_setup.yaml")
    ap.add_argument("--seeds", default="1")
    ap.add_argument("--max-turn", type=int, default=3)
    ap.add_argument("--mode", choices=["frontier", "beam"], default="frontier")
    ap.add_argument("--beam", type=int, default=8)
    ap.add_argument("--stage", type=int, default=1)
    ap.add_argument("--order", default="rank", choices=["rank", "canonical", "value"])
    ap.add_argument("--trim-order", default="value", choices=["value", "ruler", "plan"],
                    help="ターン境界で保持する局面の順序（value=V、ruler=順序関数、plan=大局観の段の充足率）")
    ap.add_argument("--stages-file", default="data/eval/stages/saga.generated.yaml",
                    help="trim-order=plan で使う段階目標の鎖（load_stage_file 形式）")
    ap.add_argument("--budget", type=int, default=200_000)
    ap.add_argument("--out", default="logs/exhaustive_crossturn.jsonl")
    a = ap.parse_args()

    rules = load_rules()
    print("rules loaded", flush=True)
    if a.trim_order == "plan":
        global _PLANNER
        stages, _goal = load_stage_file(a.stages_file)
        _PLANNER = MacroPlanner(stages=stages)
        print(f"planner: {len(stages)} stages from {a.stages_file}", flush=True)
    setup0 = yaml.safe_load(Path(a.setup).read_text(encoding="utf-8"))
    seeds = [int(s) for s in a.seeds.split(",") if s.strip()]
    name = Path(a.setup).stem

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    f = out.open("w", encoding="utf-8")

    def w(obj):
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        f.flush()

    from dmsim.eval.explog import engine_version
    settings = {"mode": a.mode, "beam": a.beam, "stage": a.stage, "order": a.order,
                "trim_order": a.trim_order,
                "stages_file": a.stages_file if a.trim_order == "plan" else None,
                "budget_per_state": a.budget, "max_turn": a.max_turn,
                "frontier_cap": FRONTIER_CAP, "leaf_cap": LEAF_CAP,
                "opp": "passive (charge only)", "lock_judge": "off"}
    w({"kind": "header", "tool": "exhaustive_crossturn", "schema": "exhaustive-proto-1",
       "engine_version": engine_version("."), "settings": settings})
    # 記録ファイル名の設定サフィックス（設定が違う走行同士の上書き事故を防ぐ）
    cfg_hash = cfg_suffix(settings)
    rec_dir = Path("logs/exhaustive_records")
    rec_dir.mkdir(parents=True, exist_ok=True)

    for seed in seeds:
        setup = dict(setup0)
        setup["seed"] = seed
        case = f"{name} seed{seed} T{a.max_turn} {a.mode}{a.beam if a.mode == 'beam' else ''}"
        w({"kind": "case_start", "case": case, "mode": f"crossturn-{a.mode}",
           "scope": {"setup": a.setup, "seed": seed, "max_turn": a.max_turn,
                     "stage": a.stage, "order": a.order}})
        t0 = time.perf_counter()
        try:
            r = run_case(rules, setup, max_turn=a.max_turn, mode=a.mode, beam=a.beam,
                         stage=a.stage, order=a.order, node_budget=a.budget,
                         trim_order=a.trim_order)
        except Exception as e:
            w({"kind": "case_result", "case": case, "verdict": "error",
               "error": f"{type(e).__name__}: {e}", "wall_seconds": round(time.perf_counter() - t0, 3)})
            print(f"[{case}] ERROR {e}", flush=True)
            continue
        rec_name = None
        if r["verdict"] == "kill" and r["final"] is not None:
            from dmsim.engine.play import deck_lists, make_record
            rec = make_record(r["final"], deck_lists(r["final"]), seed,
                              note=f"crossturn {a.mode} kill from {a.setup}",
                              scenario=dict(setup0, seed=seed))
            rec_name = f"crossturn_{name}_seed{seed}_{a.mode}-{cfg_hash}.json"
            (rec_dir / rec_name).write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        w({"kind": "case_result", "case": case, "verdict": r["verdict"],
           "kill_turn": r["kill_turn"], "kill_by": r["kill_by"], "nodes": r["nodes"],
           "frontier_sizes": r["frontier_sizes"], "capped": r["capped"],
           "truncated": r["truncated"], "record": rec_name,
           "wall_seconds": round(time.perf_counter() - t0, 3)})
        print(f"[{case}] {r['verdict'].upper()} kill_turn={r['kill_turn']} nodes={r['nodes']} "
              f"frontier={r['frontier_sizes']} capped={r['capped']} trunc={r['truncated']} "
              f"wall={time.perf_counter() - t0:.1f}s", flush=True)
    f.close()


if __name__ == "__main__":
    main()
