"""全保持探索のラベル付け: frontier を止めずに全展開し、各局面に
「あと何ターンで殺せるか（dist）」を付ける（docs/chain-from-frontier-plan.md §2）。

通常の探索は最初のキルで止まるが、ここでは止めない。局面ごとに
「その展開でキル葉が出たか」と「次ターンの子局面のキー」を edges に記録し、
全展開の後に最終ターンから逆向きに dist を伝播させる。出力は
状態ストア＋edges＋labels で、抽出器 v2（chain_extract2）の材料になる。

ラベルの正直さ: 打ち切り（葉上限・局面毎予算・保持上限）に触れた局面と
その祖先は exact=False とし、抽出の材料から外せるようにする。
dist が確定するのは exact な局面だけ。保持上限で落とした子は目録に
キー単位で記録し、exact は局面単位で伝播させる（自分の子が全て残った
局面は、同じターンで他の局面の子が落ちていても exact のまま）。

実行はディスク常駐・分割実行（目録で中断・再開可能）。
exhaustive_crossturn は変更せず、内部部品を import して使う。

使い方:
  python3 tools/chain_label.py --setup tests/saga_prep_setup.yaml \
      --seeds 1 --max-turn 2 --store-dir logs/label_prep
  python3 tools/chain_label.py --deck data/decks/saga_doom_e.yaml \
      --seeds 24 --max-turn 4 --stage 2 --store-dir logs/label_doom_e \
      --chunk-nodes 100000 [--resume]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from dmsim import load_rules  # noqa: E402
from dmsim.engine import Engine  # noqa: E402
from dmsim.engine import rustcore  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
from dmsim.eval.explog import engine_version  # noqa: E402
from dmsim.eval.measure import load_deck  # noqa: E402
from dmsim.search import turn  # noqa: E402

import exhaustive_crossturn as ct  # noqa: E402
from exhaustive_crossturn import (  # noqa: E402
    GuideMismatch, LeafCollector, _store_get, _store_put, advance_to_my_turn)
from exhaustive_proto import STAGES, _make_stage_search, stage_candidates  # noqa: E402


def _rss_mb() -> int:
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) // 1024
    except Exception:
        pass
    return 0


class _Aborted(Exception):
    def __init__(self, reason):
        self.reason = reason


def compute_labels(store: Path, dropped: dict, max_turn: int) -> dict:
    """edges.jsonl から dist と exact を後方伝播で計算する。

    exact は「dist の上限と下限が一致する」こととして定義する:
    - 上限 ub: 実際に見つかった最速のキルまでのターン数（無ければ ∞）。
    - 下限 lb: 打ち切りや保持上限で落とした先に隠れ得る最速キルの下限。
      キルが見つかった局面は lb=ub=1（1 未満にはならない）で、自分の
      展開が打ち切られていても exact。打ち切られたのにキルが無い局面は
      lb=1（キルが隠れているかもしれない）。落とされた子は lb=1 として
      親の下限を引く。
    旧定義（子が全て exact でないと親も inexact）は過剰に保守的で、
    キル発見済みの打ち切り局面の祖先が全て inexact になっていた
    （seed31 パイロットで実測: 全ターンの展開が完走し全子が決着して
    いても開始局面が inexact と表示された）。"""
    edges = {}
    for line in (store / "edges.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        edges[e["key"]] = e
    ub: dict[str, int | None] = {}
    lb: dict[str, int | None] = {}
    INF = None
    for key in sorted(edges, key=lambda k: -edges[k]["turn"]):
        e = edges[key]
        if e["kill"]:
            ub[key] = lb[key] = 1
            continue
        if e["turn"] >= max_turn:
            ub[key] = INF
            lb[key] = 1 if e["trunc"] else INF
            continue
        child_ub = [ub.get(c, INF) for c in e["children"]]
        finite = [x for x in child_ub if x is not None]
        ub[key] = 1 + min(finite) if finite else INF
        if e["trunc"]:
            lb[key] = 1
        else:
            # edges に無い子（保持上限で落とされた）は lb=1 として数える
            child_lb = [lb[c] if c in lb else 1 for c in e["children"]]
            finite_lb = [x for x in child_lb if x is not None]
            lb[key] = 1 + min(finite_lb) if finite_lb else INF
    return {k: {"turn": edges[k]["turn"], "dist": ub[k],
                "exact": ub[k] == lb[k]}
            for k in edges}


def run_labeling(rules, setup, *, deck_mode, deck, seed, max_turn, stage,
                 order, node_budget, frontier_cap, store: Path,
                 manifest, chunk_nodes, total_budget, mem_limit_mb,
                 settings_hash, engine_ver, progress=None,
                 checkpoint_nodes: int = 0):
    st = next(s for s in STAGES if s["stage"] == stage)
    fn, _label = stage_candidates(order, stage)
    orig = turn.candidates
    turn.candidates = fn
    try:
        search_cls = _make_stage_search(st["stock_offsets"])
        store.mkdir(parents=True, exist_ok=True)
        edges_path = store / "edges.jsonl"
        if manifest is None:
            if deck_mode:
                start = Engine.new_game(rules, [deck, ["dm01-080"] * 40],
                                        seed, 0)
            else:
                start = sc.build(rules, setup)
            k0 = _store_put(store, start)
            mf = {"version": 1, "settings_hash": settings_hash,
                  "engine_version": engine_ver, "status": "running",
                  "max_turn": max_turn,
                  "turn": 1, "next_index": 0, "frontier_keys": [k0],
                  "nxt_keys": [], "total_nodes": 0, "capped": False,
                  "truncated": False, "turn_capped": {}}
        else:
            mf = manifest

        def save_mf():
            tmp = store / "manifest.json.tmp"
            tmp.write_text(json.dumps(mf, ensure_ascii=False),
                           encoding="utf-8")
            os.replace(tmp, store / "manifest.json")

        # 局面内チェックポイント: 1局面の展開途中でも、処理済みの葉までの
        # 探索状態（LeafCollector.checkpoint_state）と収集済みの
        # children/kill をファイルに保存し、プロセスが死んでもその局面を
        # 途中から再開できるようにする。manifest の形式は変えない。
        ckpt_path = store / "state_ckpt.pkl"
        ckpt_tmp = store / "state_ckpt.pkl.tmp"

        def save_ckpt(obj):
            with ckpt_tmp.open("wb") as fh:
                pickle.dump(obj, fh, protocol=4)
            os.replace(ckpt_tmp, ckpt_path)

        def drop_ckpt():
            for p in (ckpt_path, ckpt_tmp):
                try:
                    p.unlink()
                except FileNotFoundError:
                    pass

        def load_ckpt(turn_, idx_, key_):
            if not checkpoint_nodes or not ckpt_path.exists():
                return None
            try:
                with ckpt_path.open("rb") as fh:
                    ck = pickle.load(fh)
            except Exception:
                drop_ckpt()
                return None
            if (ck.get("turn"), ck.get("idx"), ck.get("key"),
                    ck.get("settings_hash")) != (turn_, idx_, key_,
                                                  settings_hash):
                drop_ckpt()   # 別の局面の残骸
                return None
            return ck

        save_mf()
        if manifest is None:
            drop_ckpt()
        inv_start = mf["total_nodes"]
        try:
            while mf["turn"] <= max_turn:
                t = mf["turn"]
                frontier_keys = mf["frontier_keys"]
                nxt_keys = list(mf["nxt_keys"])
                nxt_set = set(nxt_keys)
                for idx in range(mf["next_index"], len(frontier_keys)):
                    key = frontier_keys[idx]
                    st_eng = _store_get(store, rules, key)
                    ts = search_cls(0, budget=node_budget)
                    kill: list = []
                    children: list[str] = []
                    children_set: set[str] = set()
                    ck = load_ckpt(t, idx, key)
                    resume = None
                    if ck is not None:
                        resume = ck["collector"]
                        children = list(ck["children"])
                        children_set = set(children)
                        if ck["kill"]:
                            kill.append(True)
                        print(f"[turn {t} idx {idx}] 局面内チェックポイント"
                              f"から再開: leaves={resume['leaf_count']} "
                              f"nodes={resume['nodes']}", flush=True)
                    last_ckpt = [resume["nodes"] if resume else 0]

                    def handle_leaf(_v, leaf, _loops):
                        r = leaf.s.result
                        if r is not None:
                            if r.get("winner") == 0:
                                kill.append(True)
                        else:
                            nxt_eng = advance_to_my_turn(leaf)
                            if nxt_eng is not None:
                                ckey = _store_put(
                                    store, ct._as_python(nxt_eng))
                                if ckey not in children_set:
                                    children_set.add(ckey)
                                    children.append(ckey)
                        if (checkpoint_nodes and collector._guide_done
                                and ts.stats.nodes - last_ckpt[0]
                                >= checkpoint_nodes):
                            save_ckpt({
                                "turn": t, "idx": idx, "key": key,
                                "settings_hash": settings_hash,
                                "children": list(children),
                                "kill": bool(kill),
                                "collector": collector.checkpoint_state()})
                            last_ckpt[0] = ts.stats.nodes

                    collector = LeafCollector(ts, on_leaf=handle_leaf)
                    collector.track_path = checkpoint_nodes > 0
                    try:
                        _l, trunc, nodes = collector.collect(
                            rustcore.maybe_rust(st_eng), node_budget,
                            resume=resume)
                    except GuideMismatch:
                        # ガイドが実際の探索と食い違った（本来は起きない）:
                        # チェックポイントを捨て、この局面だけ最初から
                        # 展開し直す。探索は決定的なので等価性は保たれる。
                        print(f"[turn {t} idx {idx}] チェックポイントの"
                              "ガイド不一致: 最初から展開し直します",
                              flush=True)
                        drop_ckpt()
                        kill.clear()
                        children.clear()
                        children_set.clear()
                        collector = LeafCollector(ts, on_leaf=handle_leaf)
                        collector.track_path = checkpoint_nodes > 0
                        last_ckpt[0] = 0
                        _l, trunc, nodes = collector.collect(
                            rustcore.maybe_rust(st_eng), node_budget)
                    mf["total_nodes"] += nodes
                    mf["truncated"] = mf["truncated"] or trunc
                    with edges_path.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps(
                            {"key": key, "turn": t, "kill": bool(kill),
                             "trunc": trunc, "children": children}) + "\n")
                    for ck in children:
                        if ck not in nxt_set:
                            nxt_set.add(ck)
                            nxt_keys.append(ck)
                    mf["nxt_keys"] = nxt_keys
                    mf["next_index"] = idx + 1
                    save_mf()
                    drop_ckpt()
                    if progress is not None:
                        progress({"turn": t, "states_done": idx + 1,
                                  "states_total": len(frontier_keys),
                                  "nodes": mf["total_nodes"],
                                  "rss_mb": _rss_mb()})
                    if total_budget and mf["total_nodes"] > total_budget:
                        raise _Aborted("total_budget")
                    if mem_limit_mb and _rss_mb() > mem_limit_mb:
                        raise _Aborted("mem_limit")
                    if (chunk_nodes
                            and mf["total_nodes"] - inv_start >= chunk_nodes
                            and not (t == max_turn
                                     and idx == len(frontier_keys) - 1)):
                        return {"status": "suspended",
                                "nodes": mf["total_nodes"]}
                # 保持選択は順序非依存にする（計画書 §3.7）: 候補を
                # キー順に整列してから上限で切り、次ターンの frontier の
                # 並びもキー順に固定する。到着順で切ると、並列化や
                # 展開順の変更で保持集合が変わってしまう。
                nxt_keys = sorted(nxt_keys)
                capped_turn = len(nxt_keys) > frontier_cap
                if capped_turn:
                    mf["capped"] = True
                    mf["turn_capped"][str(t)] = True
                    prev = mf.setdefault("dropped", {}).get(str(t), [])
                    mf["dropped"][str(t)] = sorted(
                        set(prev) | set(nxt_keys[frontier_cap:]))
                    nxt_keys = nxt_keys[:frontier_cap]
                mf["frontier_keys"] = nxt_keys
                mf["nxt_keys"] = []
                mf["next_index"] = 0
                mf["turn"] = t + 1
                save_mf()
                if progress is not None:
                    progress({"turn_done": t, "frontier_next": len(nxt_keys),
                              "nodes": mf["total_nodes"],
                              "capped": mf["capped"],
                              "truncated": mf["truncated"]})
                if not nxt_keys:
                    break
        except _Aborted as ab:
            mf["status"] = "aborted"
            mf["abort_reason"] = ab.reason
            save_mf()
            return {"status": "aborted", "reason": ab.reason,
                    "nodes": mf["total_nodes"]}
        mf["status"] = "completed"
        save_mf()
        labels = compute_labels(store, mf.get("dropped", {}), max_turn)
        (store / "labels.json").write_text(
            json.dumps(labels, ensure_ascii=False), encoding="utf-8")
        hist: dict[str, int] = {}
        for v in labels.values():
            if v["exact"]:
                k = str(v["dist"]) if v["dist"] is not None else "inf"
                hist[k] = hist.get(k, 0) + 1
        return {"status": "completed", "nodes": mf["total_nodes"],
                "states": len(labels),
                "exact_states": sum(1 for v in labels.values() if v["exact"]),
                "dist_hist": hist, "capped": mf["capped"],
                "truncated": mf["truncated"]}
    finally:
        turn.candidates = orig


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup", default=None)
    ap.add_argument("--deck", default=None)
    ap.add_argument("--seeds", default="1")
    ap.add_argument("--max-turn", type=int, default=3)
    ap.add_argument("--stage", type=int, default=1)
    ap.add_argument("--order", default="rank",
                    choices=["rank", "canonical", "value"])
    ap.add_argument("--budget", type=int, default=200_000)
    ap.add_argument("--frontier-cap", type=int, default=10 ** 9)
    ap.add_argument("--leaf-cap", type=int, default=200_000)
    ap.add_argument("--total-budget", type=int, default=0)
    ap.add_argument("--mem-limit-mb", type=int, default=0)
    ap.add_argument("--store-dir", required=True)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--chunk-nodes", type=int, default=0)
    ap.add_argument("--checkpoint-nodes", type=int, default=25_000,
                    help="局面内チェックポイントの間隔（ノード数、0で無効）。"
                         "設定ハッシュには含めない（結果に影響しないため）")
    ap.add_argument("--out", default="logs/chain_label.jsonl")
    a = ap.parse_args(argv)

    ct.LEAF_CAP = a.leaf_cap
    rules = load_rules()
    ever = engine_version(".")
    deck_mode = a.deck is not None
    deck = load_deck(a.deck) if deck_mode else None
    setup0 = ({} if deck_mode else
              yaml.safe_load(Path(a.setup).read_text(encoding="utf-8")))
    name = Path(a.deck).stem if deck_mode else Path(a.setup).stem
    settings = {"deck": a.deck, "setup": None if deck_mode else a.setup,
                "max_turn": a.max_turn, "stage": a.stage, "order": a.order,
                "budget": a.budget, "frontier_cap": a.frontier_cap,
                "leaf_cap": a.leaf_cap}
    cfg_hash = hashlib.sha256(
        json.dumps(settings, sort_keys=True).encode()).hexdigest()[:8]
    out_path = Path(a.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if a.resume else "w"

    with out_path.open(mode, encoding="utf-8") as out:

        def w(obj):
            out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            out.flush()

        for seed in [int(x) for x in a.seeds.split(",") if x.strip()]:
            case = f"{name} seed{seed}"
            case_store = Path(a.store_dir) / f"{name}_seed{seed}-{cfg_hash}"
            manifest = None
            if a.resume and (case_store / "manifest.json").exists():
                manifest = json.loads(
                    (case_store / "manifest.json").read_text(encoding="utf-8"))
                if (manifest.get("settings_hash") != cfg_hash
                        or manifest.get("engine_version") != ever):
                    print(f"[{case}] 再開条件が一致しません", flush=True)
                    continue
                if manifest.get("status") in ("completed", "aborted"):
                    print(f"[{case}] 既に {manifest['status']}", flush=True)
                    continue
                w({"kind": "resumed", "case": case,
                   "turn": manifest["turn"],
                   "next_index": manifest["next_index"],
                   "nodes": manifest["total_nodes"]})
            setup = dict(setup0, seed=seed) if not deck_mode else setup0

            def progress(info, _case=case):
                w({"kind": "progress", "case": _case, **info})

            t0 = time.time()
            res = run_labeling(
                rules, setup, deck_mode=deck_mode, deck=deck, seed=seed,
                max_turn=a.max_turn, stage=a.stage, order=a.order,
                node_budget=a.budget, frontier_cap=a.frontier_cap,
                store=case_store, manifest=manifest,
                chunk_nodes=a.chunk_nodes, total_budget=a.total_budget,
                mem_limit_mb=a.mem_limit_mb, settings_hash=cfg_hash,
                engine_ver=ever, progress=progress,
                checkpoint_nodes=a.checkpoint_nodes)
            if res["status"] == "suspended":
                w({"kind": "suspended", "case": case,
                   "nodes": res["nodes"], "wall_seconds": time.time() - t0})
            else:
                w({"kind": "label_result", "case": case,
                   "wall_seconds": time.time() - t0,
                   "store": str(case_store), **res})
            print(f"[{case}] {res['status']} nodes={res['nodes']}",
                  flush=True)


if __name__ == "__main__":
    main()
