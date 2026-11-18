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
import os  # noqa: E402
import pickle  # noqa: E402
from dmsim.engine import state as _state_mod  # noqa: E402

# copy-on-write（実験B）を既定で有効にする: 保持探索では局面の大量保持で
# メモリが律速になるため（docs/cow-experiment.md）。DMSIM_COW=0 で無効化できる。
if os.environ.get("DMSIM_COW") != "0":
    _state_mod.COW = True
from dmsim.engine import rustcore  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
from dmsim.engine.loop import abstract, verify  # noqa: E402
from dmsim.search import turn  # noqa: E402
from dmsim.search.turn import Detectors, TurnSearch, _is_burn, _is_engine  # noqa: E402
from dmsim.plan.macro import MacroPlanner, load_stage_file, stage_fraction  # noqa: E402
from dmsim.search.leaf_eval import WIN, Weights, evaluate  # noqa: E402
from exhaustive_proto import STAGES, _make_stage_search, cfg_suffix, stage_candidates  # noqa: E402
from order_fn import ruler_key  # noqa: E402

_W = Weights()
_PLANNERS: list[MacroPlanner] = []


def _trim_score(mode: str, eng) -> tuple:
    """ターン境界で保持する局面の順序スコア（次ターン開始局面で測る）。
    plan: 大局観の Plan の充足率（stage_fraction）を主軸にし、同点は順序関数 v2 で解く。
    鎖が複数ある場合は鎖の選択（大局観の責務）として、各鎖での充足率の
    最大値を採る（局面に最も合うルートで評価する楽観選択。保持は
    優先付けであって除外ではないので、楽観側に倒す）。最大値は鎖の
    並び順に依存しないため、保持選択の順序非依存も保たれる。"""
    if mode == "plan":
        frac = max(stage_fraction(eng, 0, p.plan(eng, 0))
                   for p in _PLANNERS)
        return (frac,) + ruler_key(eng, 0)
    return ruler_key(eng, 0) if mode == "ruler" else (evaluate(eng, 0, _W),)


def _as_python(eng):
    """RustEngine なら、その時点の状態を写した Python の Engine に変換する。
    葉を保持・保存・記録に回す前に使い、下流は従来どおり Python の
    Engine だけを見る（展開の入口で maybe_rust に包み、出口で戻す）。"""
    v = getattr(eng, "_view", None)
    return v() if v is not None else eng

FRONTIER_CAP = 64        # frontier モードで保持する局面数の上限（超えたら capped）
LEAF_CAP = 4000          # 1局面・1ターンあたりに集める葉の上限
_TOTAL_BUDGET = 0        # ケース全体のノード総予算（0 = 無制限。main が設定する）
_MEM_LIMIT_MB = 0        # 最大RSS の上限MB（0 = 無制限。main が設定する）


class _CapReached(Exception):
    pass


class _RunAborted(Exception):
    """総予算またはメモリ上限で打ち切った（判定は unknown になる）。"""
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class LeafCollector:
    """TurnSearch._search と同じ規則で、ターン終了の葉を全て集める。

    on_leaf が渡された場合は葉を溜めず、見つけ次第その場で渡す（ストリーミング）。
    葉を全部保持するとメモリが葉の数に比例して膨らみ、葉の多い局面では
    保持局面の数より先にこちらが律速になる（2026-11-17 のパイロットで実証）。
    LEAF_CAP はどちらの方式でも安全弁として効く（当たれば truncated）。
    """

    def __init__(self, ts: TurnSearch, on_leaf=None):
        self.ts = ts
        self.on_leaf = on_leaf
        self.leaves: list[tuple[float, object, tuple]] = []
        self.leaf_count = 0
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
        self.leaf_count = 0
        self.truncated = False
        det = Detectors.new(eng, ts.me, ts.draw_discard)
        try:
            self._rec(eng.clone(), det)
        except _CapReached:
            self.truncated = True
        return self.leaves, self.truncated, ts.stats.nodes

    def _add_leaf(self, value, eng, loops):
        self.leaf_count += 1
        if self.on_leaf is not None:
            self.on_leaf(value, eng, loops)
        else:
            self.leaves.append((value, eng, loops))
        if self.leaf_count >= LEAF_CAP:
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
             stage: int, order: str, node_budget: int, trim_order: str = "value",
             start_engine=None, progress=None):
    st = next(s for s in STAGES if s["stage"] == stage)
    fn, _label = stage_candidates(order, stage)
    orig = turn.candidates
    turn.candidates = fn
    try:
        search_cls = _make_stage_search(st["stock_offsets"])
        start = start_engine if start_engine is not None else sc.build(rules, setup)
        frontier = [start]
        total_nodes = 0
        capped = False
        truncated_any = False
        frontier_sizes = []
        for t in range(1, max_turn + 1):
            nxt: dict[str, tuple[float, object]] = {}
            for _si, st_eng in enumerate(frontier):
                ts = search_cls(0, budget=node_budget)
                kill_leaf: list = []

                def handle_leaf(_v, leaf, _loops):
                    # 葉は溜めずその場で処理する（ストリーミング）。
                    # キルが見つかっても展開は最後まで回す: ノード数を
                    # 従来（全葉収集）方式と一致させ、途中打ち切りと区別するため。
                    if kill_leaf:
                        return
                    r = leaf.s.result
                    if r is not None and r.get("winner") == 0:
                        kill_leaf.append(_as_python(leaf))
                        return
                    nxt_eng = advance_to_my_turn(leaf)
                    if nxt_eng is not None:
                        nxt_eng = _as_python(nxt_eng)
                        key = nxt_eng.s.fast_key()  # 探索内部の重複統合は高速キー（記録照合は digest のまま）
                        s = _trim_score(trim_order, nxt_eng)
                        if key not in nxt or s > nxt[key][0]:
                            nxt[key] = (s, nxt_eng)

                _leaves, trunc, nodes = LeafCollector(
                    ts, on_leaf=handle_leaf).collect(
                        rustcore.maybe_rust(st_eng), node_budget)
                total_nodes += nodes
                truncated_any = truncated_any or trunc
                if _TOTAL_BUDGET and total_nodes > _TOTAL_BUDGET:
                    raise _RunAborted("total_budget")
                if _MEM_LIMIT_MB:
                    import resource
                    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 > _MEM_LIMIT_MB:
                        raise _RunAborted("memory")
                if progress is not None:
                    import resource
                    progress({"turn": t, "states_done": _si + 1,
                              "states_total": len(frontier), "nodes": total_nodes,
                              "rss_mb": round(resource.getrusage(
                                  resource.RUSAGE_SELF).ru_maxrss / 1024)})
                if kill_leaf:
                    leaf = kill_leaf[0]
                    r = leaf.s.result
                    return {"verdict": "kill", "kill_turn": t, "kill_by": r.get("reason"),
                            "nodes": total_nodes, "frontier_sizes": frontier_sizes,
                            "capped": capped, "truncated": truncated_any, "final": leaf}
            frontier_sizes.append(len(nxt))
            if not nxt:
                verdict = "no-kill" if not (capped or truncated_any) else "unknown"
                return {"verdict": verdict, "kill_turn": None, "kill_by": None,
                        "nodes": total_nodes, "frontier_sizes": frontier_sizes,
                        "capped": capped, "truncated": truncated_any, "final": None}
            # 保持選択は順序非依存に（計画書 §3.7）: キー昇順に整列して
            # からスコア降順の安定ソートを重ね、同点はキーで決める。
            ranked = sorted(nxt.items(), key=lambda kv: kv[0])
            ranked.sort(key=lambda kv: kv[1][0], reverse=True)
            states = [se for _k, se in ranked]
            keep = beam if mode == "beam" else FRONTIER_CAP
            if len(states) > keep:
                if mode == "frontier":
                    capped = True
                states = states[:keep]
            frontier = [e for _v, e in states]
            if progress is not None:
                progress({"turn_done": t, "frontier_next": len(frontier),
                          "nodes": total_nodes, "capped": capped,
                          "truncated": truncated_any})
        verdict = "no-kill" if not (capped or truncated_any) else "unknown"
        return {"verdict": verdict, "kill_turn": None, "kill_by": None,
                "nodes": total_nodes, "frontier_sizes": frontier_sizes,
                "capped": capped, "truncated": truncated_any, "final": None}
    finally:
        turn.candidates = orig


def _store_put(store: Path, eng) -> str:
    """局面を状態ストアへ書く（書き込み一度きり）。キーは fast_key。
    fast_key が同じ局面は探索の重複統合でも同一視されるため、先勝ちでよい。"""
    key = eng.s.fast_key()
    p = store / f"{key}.pkl"
    if not p.exists():
        tmp = store / f".tmp-{key}"
        with tmp.open("wb") as fh:
            pickle.dump((eng.s, list(eng.log), eng.s.digest()), fh, protocol=4)
        os.replace(tmp, p)
    return key


def _store_get(store: Path, rules, key: str):
    """状態ストアから局面を復元する。digest が保存時と一致しなければ例外。"""
    with (store / f"{key}.pkl").open("rb") as fh:
        s, log, dg = pickle.load(fh)
    from dmsim.engine import Engine
    eng = Engine(rules, s)
    eng.log = log
    if eng.s.digest() != dg:
        raise ValueError(f"状態ストアの digest 不一致: {key}")
    return eng


def run_case_disk(rules, setup: dict, *, max_turn: int, mode: str, beam: int,
                  stage: int, order: str, node_budget: int, trim_order: str = "value",
                  start_engine=None, progress=None, store: Path,
                  manifest: dict | None, chunk_nodes: int = 0,
                  settings_hash: str = "", engine_ver: str = ""):
    """ディスク常駐版の run_case（docs/frontier-disk-design.md）。

    保持局面の実体は状態ストアに置き、メモリにはキーとスコアだけを残す。
    manifest が None なら新規、渡されればその続きから再開する。
    チャンク（chunk_nodes）を使い切ると verdict="suspended" で戻る
    （判定ではなく、目録を残しての中断）。"""
    st = next(s for s in STAGES if s["stage"] == stage)
    fn, _label = stage_candidates(order, stage)
    orig = turn.candidates
    turn.candidates = fn
    try:
        search_cls = _make_stage_search(st["stock_offsets"])
        store.mkdir(parents=True, exist_ok=True)
        if manifest is None:
            start = start_engine if start_engine is not None else sc.build(rules, setup)
            mf = {"version": 1, "settings_hash": settings_hash,
                  "engine_version": engine_ver, "status": "running",
                  "turn": 1, "next_index": 0,
                  "frontier_keys": [_store_put(store, start)],
                  "nxt": {}, "total_nodes": 0, "capped": False,
                  "truncated": False, "frontier_sizes": []}
        else:
            mf = manifest
        total_nodes = mf["total_nodes"]
        capped = mf["capped"]
        truncated_any = mf["truncated"]
        frontier_sizes = mf["frontier_sizes"]
        inv_nodes = 0

        def save_mf():
            mf["total_nodes"] = total_nodes
            mf["capped"] = capped
            mf["truncated"] = truncated_any
            mf["frontier_sizes"] = frontier_sizes
            tmp = store / ".manifest.tmp"
            tmp.write_text(json.dumps(mf, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, store / "manifest.json")

        save_mf()
        for t in range(mf["turn"], max_turn + 1):
            frontier_keys = mf["frontier_keys"]
            # 目録のスコアは JSON 経由でリストになるため、タプルに戻して比較を揃える
            nxt: dict[str, tuple] = ({k: tuple(v) for k, v in mf["nxt"].items()}
                                     if t == mf["turn"] else {})
            start_i = mf["next_index"] if t == mf["turn"] else 0
            for idx in range(start_i, len(frontier_keys)):
                st_eng = _store_get(store, rules, frontier_keys[idx])
                ts = search_cls(0, budget=node_budget)
                kill_leaf: list = []

                def handle_leaf(_v, leaf, _loops):
                    if kill_leaf:
                        return
                    r = leaf.s.result
                    if r is not None and r.get("winner") == 0:
                        kill_leaf.append(_as_python(leaf))
                        return
                    nxt_eng = advance_to_my_turn(leaf)
                    if nxt_eng is not None:
                        nxt_eng = _as_python(nxt_eng)
                        key = _store_put(store, nxt_eng)
                        s = _trim_score(trim_order, nxt_eng)
                        if key not in nxt or s > nxt[key]:
                            nxt[key] = s

                _l, trunc, nodes = LeafCollector(
                    ts, on_leaf=handle_leaf).collect(
                        rustcore.maybe_rust(st_eng), node_budget)
                total_nodes += nodes
                inv_nodes += nodes
                truncated_any = truncated_any or trunc
                if _TOTAL_BUDGET and total_nodes > _TOTAL_BUDGET:
                    mf["status"] = "aborted"
                    save_mf()
                    raise _RunAborted("total_budget")
                if _MEM_LIMIT_MB:
                    import resource
                    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 > _MEM_LIMIT_MB:
                        mf["status"] = "aborted"
                        save_mf()
                        raise _RunAborted("memory")
                if progress is not None:
                    import resource
                    progress({"turn": t, "states_done": idx + 1,
                              "states_total": len(frontier_keys), "nodes": total_nodes,
                              "rss_mb": round(resource.getrusage(
                                  resource.RUSAGE_SELF).ru_maxrss / 1024)})
                if kill_leaf:
                    mf["status"] = "completed"
                    save_mf()
                    leaf = kill_leaf[0]
                    r = leaf.s.result
                    return {"verdict": "kill", "kill_turn": t, "kill_by": r.get("reason"),
                            "nodes": total_nodes, "frontier_sizes": frontier_sizes,
                            "capped": capped, "truncated": truncated_any, "final": leaf}
                mf["turn"] = t
                mf["next_index"] = idx + 1
                mf["nxt"] = nxt
                save_mf()
                if chunk_nodes and inv_nodes >= chunk_nodes:
                    return {"verdict": "suspended", "kill_turn": None, "kill_by": None,
                            "nodes": total_nodes, "frontier_sizes": frontier_sizes,
                            "capped": capped, "truncated": truncated_any, "final": None}
            frontier_sizes.append(len(nxt))
            if not nxt:
                mf["status"] = "completed"
                save_mf()
                verdict = "no-kill" if not (capped or truncated_any) else "unknown"
                return {"verdict": verdict, "kill_turn": None, "kill_by": None,
                        "nodes": total_nodes, "frontier_sizes": frontier_sizes,
                        "capped": capped, "truncated": truncated_any, "final": None}
            # 保持選択は順序非依存に（計画書 §3.7）: キー昇順→スコア
            # 降順の安定ソートで、同点はキーで決める。
            ordered = sorted(nxt.items(), key=lambda kv: kv[0])
            ordered.sort(key=lambda kv: kv[1], reverse=True)
            keep = beam if mode == "beam" else FRONTIER_CAP
            if len(ordered) > keep:
                if mode == "frontier":
                    capped = True
                ordered = ordered[:keep]
            new_keys = [k for k, _s in ordered]
            keep_set = set(new_keys)
            for p in store.glob("*.pkl"):
                if p.stem not in keep_set:
                    p.unlink()
            mf["turn"] = t + 1
            mf["next_index"] = 0
            mf["frontier_keys"] = new_keys
            mf["nxt"] = {}
            save_mf()
            if progress is not None:
                progress({"turn_done": t, "frontier_next": len(new_keys),
                          "nodes": total_nodes, "capped": capped,
                          "truncated": truncated_any})
        mf["status"] = "completed"
        save_mf()
        verdict = "no-kill" if not (capped or truncated_any) else "unknown"
        return {"verdict": verdict, "kill_turn": None, "kill_by": None,
                "nodes": total_nodes, "frontier_sizes": frontier_sizes,
                "capped": capped, "truncated": truncated_any, "final": None}
    finally:
        turn.candidates = orig


def main():
    global FRONTIER_CAP, LEAF_CAP, _TOTAL_BUDGET, _MEM_LIMIT_MB
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", default="tests/saga_prep_setup.yaml")
    ap.add_argument("--deck", default=None,
                    help="指定するとシナリオではなくデッキ＋シードの対局開始（0ターン目）から始める")
    ap.add_argument("--seeds", default="1")
    ap.add_argument("--max-turn", type=int, default=3)
    ap.add_argument("--mode", choices=["frontier", "beam"], default="frontier")
    ap.add_argument("--beam", type=int, default=8)
    ap.add_argument("--stage", type=int, default=1)
    ap.add_argument("--order", default="rank", choices=["rank", "canonical", "value"])
    ap.add_argument("--trim-order", default="value", choices=["value", "ruler", "plan"],
                    help="ターン境界で保持する局面の順序（value=V、ruler=順序関数、plan=大局観の段の充足率）")
    ap.add_argument("--stages-file", default="data/eval/stages/saga.generated.yaml",
                    help="trim-order=plan で使う段階目標の鎖（load_stage_file 形式）。"
                         "カンマ区切りで複数渡すと鎖の選択（充足率の最大値）が有効になる")
    ap.add_argument("--budget", type=int, default=200_000)
    ap.add_argument("--frontier-cap", type=int, default=FRONTIER_CAP)
    ap.add_argument("--leaf-cap", type=int, default=LEAF_CAP)
    ap.add_argument("--total-budget", type=int, default=0,
                    help="ケース全体のノード総予算（0 = 無制限。超えたら unknown で打ち切り）")
    ap.add_argument("--mem-limit-mb", type=int, default=0,
                    help="最大RSS の上限MB（0 = 無制限。超えたら unknown で打ち切り）")
    ap.add_argument("--store-dir", default=None,
                    help="指定するとディスク常駐モード（状態ストア＋目録で分割・再開可能）")
    ap.add_argument("--resume", action="store_true",
                    help="--store-dir の目録から再開する（設定ハッシュが違えば拒否。再開時は --out も同じファイルを指定すること）")
    ap.add_argument("--chunk-nodes", type=int, default=0,
                    help="この起動で処理するノード量の目安（0 = 最後まで。超えたら目録を残して中断）")
    ap.add_argument("--out", default="logs/exhaustive_crossturn.jsonl")
    a = ap.parse_args()

    FRONTIER_CAP = a.frontier_cap
    LEAF_CAP = a.leaf_cap
    _TOTAL_BUDGET = a.total_budget
    _MEM_LIMIT_MB = a.mem_limit_mb

    rules = load_rules()
    print("rules loaded", flush=True)
    if a.trim_order == "plan":
        global _PLANNERS
        _PLANNERS = []
        for f in a.stages_file.split(","):
            f = f.strip()
            if not f:
                continue
            stages, _goal = load_stage_file(f)
            _PLANNERS.append(MacroPlanner(stages=stages))
            print(f"planner: {len(stages)} stages from {f}", flush=True)
    deck_mode = a.deck is not None
    deck = None
    if deck_mode:
        from dmsim.eval.measure import load_deck
        deck = load_deck(a.deck)
        setup0 = {}
        name = Path(a.deck).stem
    else:
        setup0 = yaml.safe_load(Path(a.setup).read_text(encoding="utf-8"))
        name = Path(a.setup).stem
    seeds = [int(s) for s in a.seeds.split(",") if s.strip()]

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    f = out.open("a" if a.resume else "w", encoding="utf-8")

    def w(obj):
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        f.flush()

    from dmsim.eval.explog import engine_version
    ever = engine_version(".")
    settings = {"mode": a.mode, "beam": a.beam, "stage": a.stage, "order": a.order,
                "trim_order": a.trim_order,
                "stages_file": a.stages_file if a.trim_order == "plan" else None,
                "budget_per_state": a.budget, "max_turn": a.max_turn,
                "frontier_cap": FRONTIER_CAP, "leaf_cap": LEAF_CAP,
                "total_budget": _TOTAL_BUDGET, "mem_limit_mb": _MEM_LIMIT_MB,
                "deck": a.deck,
                "opp": "passive (charge only)", "lock_judge": "off"}
    if not a.resume:
        w({"kind": "header", "tool": "exhaustive_crossturn", "schema": "exhaustive-proto-1",
           "engine_version": ever, "settings": settings})
    # 記録ファイル名の設定サフィックス（設定が違う走行同士の上書き事故を防ぐ）
    cfg_hash = cfg_suffix(settings)
    rec_dir = Path("logs/exhaustive_records")
    rec_dir.mkdir(parents=True, exist_ok=True)

    for seed in seeds:
        setup = dict(setup0)
        setup["seed"] = seed
        case = f"{name} seed{seed} T{a.max_turn} {a.mode}{a.beam if a.mode == 'beam' else ''}"
        store = None
        manifest = None
        if a.store_dir:
            store = Path(a.store_dir) / f"{name}_seed{seed}-{cfg_hash}"
            mf_path = store / "manifest.json"
            if mf_path.exists():
                if not a.resume:
                    w({"kind": "case_start", "case": case, "mode": f"crossturn-{a.mode}",
                       "scope": {"setup": None if deck_mode else a.setup, "deck": a.deck,
                                 "seed": seed, "max_turn": a.max_turn,
                                 "stage": a.stage, "order": a.order}})
                    w({"kind": "case_result", "case": case, "verdict": "error",
                       "error": f"store already exists (use --resume): {store}",
                       "wall_seconds": 0})
                    print(f"[{case}] ERROR store already exists: {store}", flush=True)
                    continue
                manifest = json.loads(mf_path.read_text(encoding="utf-8"))
                if (manifest.get("settings_hash") != cfg_hash
                        or manifest.get("engine_version") != ever):
                    w({"kind": "case_result", "case": case, "verdict": "error",
                       "error": "resume refused: settings/engine mismatch",
                       "wall_seconds": 0})
                    print(f"[{case}] ERROR resume refused (settings mismatch)", flush=True)
                    continue
                if manifest.get("status") in ("completed", "aborted"):
                    print(f"[{case}] already {manifest['status']} in store; skipped",
                          flush=True)
                    continue
        if manifest is None:
            w({"kind": "case_start", "case": case, "mode": f"crossturn-{a.mode}",
               "scope": {"setup": None if deck_mode else a.setup, "deck": a.deck,
                         "seed": seed, "max_turn": a.max_turn,
                         "stage": a.stage, "order": a.order}})
        else:
            w({"kind": "resumed", "case": case, "turn": manifest["turn"],
               "next_index": manifest["next_index"], "nodes": manifest["total_nodes"]})
            print(f"[{case}] resumed at turn {manifest['turn']} "
                  f"index {manifest['next_index']} nodes {manifest['total_nodes']}",
                  flush=True)
        t0 = time.perf_counter()

        def prog(info):
            w({"kind": "progress", "case": case, **info})
            print(f"[{case}] progress {info}", flush=True)

        try:
            start_engine = None
            if deck_mode and manifest is None:
                from dmsim.engine import Engine
                start_engine = Engine.new_game(rules, [deck, ["dm01-080"] * 40], seed, 0)
            if store is not None:
                r = run_case_disk(rules, setup, max_turn=a.max_turn, mode=a.mode,
                                  beam=a.beam, stage=a.stage, order=a.order,
                                  node_budget=a.budget, trim_order=a.trim_order,
                                  start_engine=start_engine, progress=prog,
                                  store=store, manifest=manifest,
                                  chunk_nodes=a.chunk_nodes,
                                  settings_hash=cfg_hash, engine_ver=ever)
            else:
                r = run_case(rules, setup, max_turn=a.max_turn, mode=a.mode, beam=a.beam,
                             stage=a.stage, order=a.order, node_budget=a.budget,
                             trim_order=a.trim_order, start_engine=start_engine,
                             progress=prog)
        except _RunAborted as ab:
            w({"kind": "case_result", "case": case, "verdict": "unknown",
               "aborted": ab.reason,
               "wall_seconds": round(time.perf_counter() - t0, 3)})
            print(f"[{case}] UNKNOWN (aborted: {ab.reason})", flush=True)
            continue
        except Exception as e:
            w({"kind": "case_result", "case": case, "verdict": "error",
               "error": f"{type(e).__name__}: {e}", "wall_seconds": round(time.perf_counter() - t0, 3)})
            print(f"[{case}] ERROR {e}", flush=True)
            continue
        if r["verdict"] == "suspended":
            w({"kind": "suspended", "case": case, "nodes": r["nodes"],
               "frontier_sizes": r["frontier_sizes"],
               "wall_seconds": round(time.perf_counter() - t0, 3)})
            print(f"[{case}] SUSPENDED nodes={r['nodes']} "
                  f"(resume with --resume)", flush=True)
            continue
        rec_name = None
        if r["verdict"] == "kill" and r["final"] is not None:
            from dmsim.engine.play import deck_lists, make_record
            rec = make_record(r["final"], deck_lists(r["final"]), seed,
                              note=f"crossturn {a.mode} kill from {a.deck if deck_mode else a.setup}",
                              **({} if deck_mode else {"scenario": dict(setup0, seed=seed)}))
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
