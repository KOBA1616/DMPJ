#!/usr/bin/env python3
"""Phase 27' 確認ラン: 注意モデル（AbAttnModel）を本番レシピで学習。

Phase 27' の A/B（phase27p_train.py、素のレシピ＝26-4 と同一条件）
では注意モデルは 手順 0.53・出口 0.56 と最良だった一方、到達が
0.42（ID 0.57／属性 0.61）に落ちた。本スクリプトは Phase 27 本番用
の train27.py（26-3 レシピの一般化）の構成を AbAttnModel へ適応し、
「本番レシピ（リーグ混合・集約 ON・到達ガード・3t デモ模倣）なら
到達が戻るか」をゼロから 2,000局で確認する。

train27.py との差分はモデル生成まわりだけ:
  - モデルは AbAttnModel（CardFeatures を共有）。
  - スナップショット相手は league_train.make_model（ID版 Model 用）
    の代わりに、同一 CardFeatures を持つ AbAttnModel へパラメータを
    流し込んで作る（phase27p_train.py の from_params と同じ流儀）。
  - チェックポイントの保存・再開は AbAttnModel.save/load を使う。
レシピ要素（混合比・ガード間隔・到達フロア 0.59・BC の頻度と回数・
lr・seed 27）は train27.py の既定値と同一に揃える。

到達ガードの選択基準（26-3 / train27 と同一の事前規約）:
  - 候補は guard-every ごとのチェックポイント。
  - 条件1: ガード診断の到達率 >= 0.59（= 26-3 土台の到達 0.64 − 0.05）。
  - 条件2: 条件1を満たす中で （手順＋出口）/2 が最大。同点なら後方。
  - フォールバック: 条件1が空なら到達率最大（同点なら （手順＋出口）/2、
    それも同点なら後方）。
"""
from __future__ import annotations

import argparse
import json
import pickle
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from dmsim.ai.encode import Vocab, encode_options, encode_state  # noqa: E402
from dmsim.ai.model_abattn import AbAttnModel, CardFeatures  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.search.turn import TurnSearch, charge_only_policy, greedy_policy  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402
from tools.league_train import KINDS, parse_mix  # noqa: E402
from tools.loop_stages import diagnose  # noqa: E402


def play_game(rules, vocab, model, deck, opp_kind: str,
              opp_model, seed: int, first: int,
              learner_seat: int, search_budget: int = 300,
              aggregate: bool = True, collect: bool = True):
    """train27.play_game と同一（モデル型だけ一般化）。"""
    eng = Engine.new_game(rules, [deck, deck], seed, first)
    rng = np.random.default_rng(seed * 7919 + learner_seat + 1)
    greedy = greedy_policy()
    opp_seat = 1 - learner_seat
    traj: list[tuple[dict, dict, list[int]]] = []
    for _ in range(1000):
        if eng.s.result is not None:
            break
        if opp_kind == "search" and eng.s.active == opp_seat:
            ts = TurnSearch(opp_seat, search_budget, opp_policy=greedy)
            eng, _st = ts.run(eng)
            continue
        d = eng.advance()
        if d is None:
            break
        p = d["player"]
        if p == learner_seat:
            st = encode_state(eng, p, vocab, privileged=True)
            op = encode_options(eng, d, vocab)
            choice, _, _ = model.act(st, op, rng, greedy=False,
                                     aggregate=aggregate)
            if collect:
                traj.append((st, op, sorted(choice)))
            eng.answer(sorted(choice))
        elif opp_kind in ("mirror", "snapshot"):
            om = model if opp_kind == "mirror" else opp_model
            st = encode_state(eng, p, vocab)
            op = encode_options(eng, d, vocab)
            choice, _, _ = om.act(st, op, rng, aggregate=aggregate)
            eng.answer(sorted(choice))
        elif opp_kind == "greedy":
            eng.answer(greedy(eng, d))
        elif opp_kind == "charge":
            eng.answer(charge_only_policy(eng, d))
        else:  # search: 学習者ターン中の相手決定は貪欲で代行
            eng.answer(greedy(eng, d))
    res = eng.s.result
    w = res.get("winner") if res else None
    ret = 0.0 if w is None else (1.0 if w == learner_seat else -1.0)
    batch = [{"st": st, "op": op, "choice": ch, "ret": ret}
             for st, op, ch in traj]
    return batch, w


def guard_point(rules, vocab, deck, model, games_done: int,
                guard_games: int) -> dict:
    stats = diagnose(rules, vocab, deck, model, games=guard_games,
                     seed0=50000, label=f"guard {games_done}局")
    return {
        "games": games_done,
        "reach": stats["reach_rate"],
        "proc": stats["loop_given_reach"],
        "exit": stats["win_given_loop"],
    }


def select_checkpoint(curve: list[dict], reach_floor: float) -> dict:
    """事前基準（モジュール冒頭の文面）で最終チェックポイントを選ぶ。"""
    def score(pt: dict) -> float:
        proc = pt["proc"] if pt["proc"] is not None else 0.0
        exit_ = pt["exit"] if pt["exit"] is not None else 0.0
        return (proc + exit_) / 2.0

    cands = [pt for pt in curve if pt["games"] > 0]
    eligible = [pt for pt in cands if pt["reach"] >= reach_floor]
    if eligible:
        best = max(eligible, key=lambda pt: (score(pt), pt["games"]))
        reason = (f"到達ガード（>={reach_floor}）を満たす "
                  f"{len(eligible)} 点の中で （手順＋出口）/2 が最大")
    else:
        best = max(cands, key=lambda pt: (pt["reach"], score(pt),
                                          pt["games"]))
        reason = ("到達ガードを満たすチェックポイントが無かったため、"
                  "到達率が最大のものを選択（フォールバック）")
    return {"selected_games": best["games"], "reason": reason,
            "point": best}


def save_pool(pool: list[tuple[str, dict]], path: Path) -> None:
    arrays: dict[str, np.ndarray] = {}
    names: list[str] = []
    for idx, (name, params) in enumerate(pool):
        names.append(name)
        for k, v in params.items():
            arrays[f"{idx}::{k}"] = np.asarray(v)
    np.savez_compressed(path, **arrays)
    path.with_suffix(".json").write_text(
        json.dumps({"names": names}, ensure_ascii=False))


def load_pool(path: Path) -> list[tuple[str, dict]]:
    names = json.loads(path.with_suffix(".json").read_text())["names"]
    z = np.load(path)
    pool: list[tuple[str, dict]] = []
    for idx, name in enumerate(names):
        params = {k.split("::", 1)[1]: z[k] for k in z.files
                  if k.startswith(f"{idx}::")}
        pool.append((name, params))
    return pool


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", default=None,
                    help="土台モデルの npz（省略時は新規作成）")
    ap.add_argument("--total-games", type=int, default=2000)
    ap.add_argument("--games-per-iter", type=int, default=20)
    ap.add_argument("--mix",
                    default="mirror=0.45,snapshot=0.20,greedy=0.15,"
                            "search=0.10,charge=0.10")
    ap.add_argument("--snapshot-every", type=int, default=10)
    ap.add_argument("--pool-max", type=int, default=5)
    ap.add_argument("--search-budget", type=int, default=300)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--seed", type=int, default=27)
    ap.add_argument("--deck", default="data/decks/saga.yaml")
    ap.add_argument("--aggregate", choices=["on", "off"], default="on")
    ap.add_argument("--guard", choices=["on", "off"], default="on")
    ap.add_argument("--guard-every-games", type=int, default=200)
    ap.add_argument("--guard-games", type=int, default=20)
    ap.add_argument("--reach-floor", type=float, default=0.59)
    ap.add_argument("--imitate-3t", choices=["on", "off"], default="on")
    ap.add_argument("--demos",
                    default="/home/hatch/workspace/phase27/demos_3t.pkl")
    ap.add_argument("--bc-every", type=int, default=5)
    ap.add_argument("--bc-passes", type=int, default=2)
    ap.add_argument("--work-dir",
                    default="/home/hatch/workspace/phase27p/prod_run")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--out-name", default="final_model.npz")
    a = ap.parse_args()

    aggregate = a.aggregate == "on"
    guard_on = a.guard == "on"

    work = Path(a.work_dir)
    snap_dir = work / "snapshots"
    ckpt_dir = work / "checkpoints"
    for d in (work, snap_dir, ckpt_dir):
        d.mkdir(parents=True, exist_ok=True)

    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck(a.deck)
    features = CardFeatures(rules, vocab)

    def fresh() -> AbAttnModel:
        return AbAttnModel(features, len(vocab), seed=a.seed)

    def from_params(params: dict) -> AbAttnModel:
        m = fresh()
        for k, v in params.items():
            m.p[k] = np.asarray(v, dtype=np.float32)
        m._card_cache.clear()
        return m

    demos: list[dict] | None = None
    if a.imitate_3t == "on":
        with open(a.demos, "rb") as f:
            demos = pickle.load(f)["items"]
        print(f"3t 教材: {len(demos)} 決定を読み込んだ", flush=True)

    # ---- 初期化 / 再開 ----
    curve: list[dict] = []
    pool: list[tuple[str, dict]] = []
    start_gc = 0
    progress_path = work / "progress.json"
    resumed = False
    model: AbAttnModel
    if a.resume and progress_path.exists():
        prog = json.loads(progress_path.read_text())
        start_gc = int(prog["games_done"])
        curve = prog.get("curve", [])
        ckpt = ckpt_dir / f"ckpt_{start_gc}.npz"
        init_path = str(ckpt) if ckpt.exists() else a.init
        pool_path = work / "pool_state.npz"
        if pool_path.exists():
            pool = load_pool(pool_path)
        resumed = True
        model = (AbAttnModel.load(init_path, vocab, rules=rules)
                 if init_path else fresh())
        print(f"再開: {start_gc} 局時点のチェックポイント {init_path} "
              f"から続ける（プール {[n for n, _ in pool]}）", flush=True)
    elif a.init:
        model = AbAttnModel.load(a.init, vocab, rules=rules)
    else:
        model = fresh()
    if not pool:
        pool = [("base", {k: v.copy() for k, v in model.p.items()})]
    pool_models: dict[str, AbAttnModel] = {}

    nparams = sum(v.size for v in model.p.values())
    mix = parse_mix(a.mix)
    probs = np.array([mix[k] for k in KINDS])
    rng = np.random.default_rng(a.seed)
    total = {k: 0 for k in KINDS}
    total_wins = {k: 0 for k in KINDS}
    print(f"abattn params={nparams:,} init={a.init} aggregate={aggregate} "
          f"guard={a.guard} imitate={a.imitate_3t} mix={mix} "
          f"total-games={a.total_games} start={start_gc} ゼロから学習",
          flush=True)

    guard_every_iters = max(1, a.guard_every_games // a.games_per_iter)
    iters_total = max(0, (a.total_games - start_gc) // a.games_per_iter)
    iter0 = start_gc // a.games_per_iter
    t0 = time.time()

    if guard_on and not resumed:
        base_pt = guard_point(rules, vocab, deck, model, start_gc,
                              a.guard_games)
        curve.append(base_pt)
        (work / "guard_curve.json").write_text(
            json.dumps(curve, ensure_ascii=False, indent=1))
        print(f"guard {start_gc}局: 到達 {base_pt['reach']:.2f} "
              f"({time.time() - t0:.0f}s)", flush=True)

    gc = start_gc
    for it in range(iters_total):
        git = iter0 + it
        counts = rng.multinomial(a.games_per_iter, probs)
        plan = [k for k, c in zip(KINDS, counts) for _ in range(c)]
        rng.shuffle(plan)
        batch: list[dict] = []
        iter_wins = {k: 0 for k in KINDS}
        for kind in plan:
            learner_seat = gc % 2
            first = (gc // 2) % 2
            opp_model = None
            if kind == "snapshot":
                name, params = pool[int(rng.integers(0, len(pool)))]
                if name not in pool_models:
                    pool_models[name] = from_params(params)
                opp_model = pool_models[name]
            b, w = play_game(
                rules, vocab, model, deck, kind, opp_model,
                seed=1000003 * a.seed + gc, first=first,
                learner_seat=learner_seat,
                search_budget=a.search_budget, aggregate=aggregate)
            batch.extend(b)
            total[kind] += 1
            if w == learner_seat:
                iter_wins[kind] += 1
                total_wins[kind] += 1
            gc += 1
        loss, grads = model.loss_and_grads(batch, aggregate=aggregate)
        model.step(grads, lr=a.lr)
        bc_msg = ""
        if demos is not None and (git + 1) % a.bc_every == 0:
            bloss = 0.0
            for _ in range(a.bc_passes):
                bloss, bgrads = model.bc_loss_and_grads(
                    demos, aggregate=aggregate)
                model.step(bgrads, lr=a.lr)
            bc_msg = f" bc={bloss:.3f}x{a.bc_passes}"
        cnt_s = " ".join(f"{k}:{counts[i]}" for i, k in enumerate(KINDS)
                         if counts[i])
        win_s = " ".join(
            f"{k} {iter_wins[k]}/{counts[i]}"
            for i, k in enumerate(KINDS) if counts[i])
        print(f"iter {git}: loss={loss:.3f} dec={len(batch)} [{cnt_s}] "
              f"勝ち [{win_s}]{bc_msg} ({time.time() - t0:.0f}s)",
              flush=True)
        if (git + 1) % a.snapshot_every == 0 or it == iters_total - 1:
            name = f"iter{git + 1}"
            snap_path = snap_dir / f"prod_{name}.npz"
            model.save(str(snap_path))
            pool.append((name, {k: v.copy() for k, v in model.p.items()}))
            while len(pool) > a.pool_max:
                old, _ = pool.pop(0)
                pool_models.pop(old, None)
            print(f"  snapshot {snap_path} pool={[n for n, _ in pool]}",
                  flush=True)
        if guard_on and ((git + 1) % guard_every_iters == 0
                         or it == iters_total - 1):
            ckpt_path = ckpt_dir / f"ckpt_{gc}.npz"
            model.save(str(ckpt_path))
            pt = guard_point(rules, vocab, deck, model, gc, a.guard_games)
            curve.append(pt)
            (work / "guard_curve.json").write_text(
                json.dumps(curve, ensure_ascii=False, indent=1))
            pool_path = work / "pool_state.npz"
            save_pool(pool, pool_path)
            progress_path.write_text(json.dumps(
                {"games_done": gc, "curve": curve},
                ensure_ascii=False, indent=1))
            print(f"  guard {gc}局: 到達 {pt['reach']:.2f} "
                  f"手順 {pt['proc']} 出口 {pt['exit']} "
                  f"({time.time() - t0:.0f}s)", flush=True)
    print(f"学習完了: {gc} 局（{time.time() - t0:.0f}s）", flush=True)
    for k in KINDS:
        if total[k]:
            print(f"  相手 {k}: {total[k]} 局、学習者の勝率 "
                  f"{total_wins[k] / total[k]:.2f}", flush=True)

    # ---- 最終モデルの選択と保存 ----
    out_path = work / a.out_name
    if guard_on and curve:
        sel = select_checkpoint(curve, a.reach_floor)
        src = ckpt_dir / f"ckpt_{sel['selected_games']}.npz"
        shutil.copyfile(src, out_path)
        (work / "selection.json").write_text(json.dumps(
            {"selection": sel, "curve": curve},
            ensure_ascii=False, indent=1))
        print(f"最終モデル: {src} -> {out_path}"
              f"（理由: {sel['reason']}）", flush=True)
    else:
        model.save(str(out_path))
        print(f"最終モデル: {out_path}（ガードなし、最終状態を保存）",
              flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
