#!/usr/bin/env python3
"""Phase 26-3: 特権価値＋トラッカー特徴＋到達ガードのリーグ学習。

26-2（tools/league_train.py）のレシピ（相手プール混合・集約 ON・
2,000局）をそのまま使い、変更点は次の3つだけにする:

1. 特権価値: 学習者の軌跡を encode_state(privileged=True) で取り、
   価値ヘッドにだけ相手の手札の構成を入力する（方策は不変）。
2. トラッカー特徴: encode_state が常に付ける公開情報の集計特徴
   （自分の未見プールの構成、相手の公開カードの構成）。
3. 到達ガード: 200局ごとにチェックポイントを保存し、固定シード
   （50000+i、20局）の軽量診断で到達・手順・出口を測って曲線を
   記録する。最終モデルは下記の事前基準で選ぶ。

最終モデルの選択基準（学習前にここへ明記する。docs/ai-phases.md の
Phase 26-3 節にも同じ文面を置く）:
  - 候補は 200局ごとのチェックポイント（200〜2,000局の10点）。
  - 条件1（到達ガード）: ガード診断の到達率 >= 0.59
    （土台の全条件診断 0.64 から 0.05 以内）。
  - 条件2: 条件1を満たす中で （手順＋出口）/2 が最大のもの。
    同点なら後のチェックポイント。手順・出口が測れなかった
    （到達サンプル無し等）場合は 0 として扱う。
  - フォールバック: 条件1を満たすものが無ければ、到達率が最大の
    チェックポイント（同点なら （手順＋出口）/2 が大きい方、
    それも同点なら後のもの）。
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from dmsim.ai.encode import Vocab, encode_options, encode_state  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.search.turn import TurnSearch, charge_only_policy, greedy_policy  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402
from tools.league_train import BASE, KINDS, make_model, parse_mix  # noqa: E402
from tools.loop_stages import diagnose  # noqa: E402

OUT = Path("/home/hatch/workspace/phase26priv")
REACH_FLOOR = 0.59  # 土台の到達 0.64 − 0.05


def play_priv_game(rules, vocab, model, deck, opp_kind: str,
                   opp_model: Model | None, seed: int, first: int,
                   learner_seat: int, search_budget: int = 300,
                   learner_greedy: bool = False, collect: bool = True):
    """league_train.play_league_game と同一の対局。ただし学習者の局面は
    privileged=True でエンコードする（特権情報は価値の学習専用）。"""
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
            choice, _, _ = model.act(st, op, rng, greedy=learner_greedy,
                                     aggregate=True)
            if collect:
                traj.append((st, op, sorted(choice)))
            eng.answer(sorted(choice))
        elif opp_kind in ("mirror", "snapshot"):
            om = model if opp_kind == "mirror" else opp_model
            st = encode_state(eng, p, vocab)
            op = encode_options(eng, d, vocab)
            choice, _, _ = om.act(st, op, rng, aggregate=True)
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
    """固定シードの軽量診断（到達ガード用）。到達・手順・出口を返す。"""
    stats = diagnose(rules, vocab, deck, model, games=guard_games,
                     seed0=50000, label=f"guard {games_done}局")
    return {
        "games": games_done,
        "reach": stats["reach_rate"],
        "proc": stats["loop_given_reach"],
        "exit": stats["win_given_loop"],
    }


def select_checkpoint(curve: list[dict]) -> dict:
    """事前基準（モジュール冒頭の文面）で最終チェックポイントを選ぶ。"""
    def score(pt: dict) -> float:
        proc = pt["proc"] if pt["proc"] is not None else 0.0
        exit_ = pt["exit"] if pt["exit"] is not None else 0.0
        return (proc + exit_) / 2.0

    cands = [pt for pt in curve if pt["games"] > 0]
    eligible = [pt for pt in cands if pt["reach"] >= REACH_FLOOR]
    if eligible:
        best = max(eligible, key=lambda pt: (score(pt), pt["games"]))
        reason = (f"到達ガード（>={REACH_FLOOR}）を満たす "
                  f"{len(eligible)} 点の中で （手順＋出口）/2 が最大")
    else:
        best = max(cands, key=lambda pt: (pt["reach"], score(pt),
                                          pt["games"]))
        reason = ("到達ガードを満たすチェックポイントが無かったため、"
                  "到達率が最大のものを選択（フォールバック）")
    return {"selected_games": best["games"], "reason": reason,
            "point": best}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=100)
    ap.add_argument("--games-per-iter", type=int, default=20)
    ap.add_argument("--mix",
                    default="mirror=0.45,snapshot=0.20,greedy=0.15,"
                            "search=0.10,charge=0.10")
    ap.add_argument("--snapshot-every", type=int, default=10)
    ap.add_argument("--pool-max", type=int, default=5)
    ap.add_argument("--search-budget", type=int, default=300)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--seed", type=int, default=26)
    ap.add_argument("--init", default=BASE)
    ap.add_argument("--out", default=str(OUT / "model_priv.npz"))
    ap.add_argument("--guard-every", type=int, default=10,
                    help="何 iter ごとにチェックポイント＋ガード診断を行うか")
    ap.add_argument("--guard-games", type=int, default=20)
    a = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    snap_dir = OUT / "snapshots"
    snap_dir.mkdir(exist_ok=True)
    ckpt_dir = OUT / "checkpoints"
    ckpt_dir.mkdir(exist_ok=True)
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")
    model = Model.load(a.init)
    mix = parse_mix(a.mix)
    probs = np.array([mix[k] for k in KINDS])
    rng = np.random.default_rng(a.seed)

    pool: list[tuple[str, dict]] = [
        ("base", {k: v.copy() for k, v in model.p.items()})]
    pool_models: dict[str, Model] = {}
    total = {k: 0 for k in KINDS}
    total_wins = {k: 0 for k in KINDS}
    print(f"init={a.init} mix={mix} iters={a.iters} "
          f"games/iter={a.games_per_iter}", flush=True)

    curve: list[dict] = []
    t0 = time.time()
    base_pt = guard_point(rules, vocab, deck, model, 0, a.guard_games)
    curve.append(base_pt)
    (OUT / "guard_curve.json").write_text(
        json.dumps(curve, ensure_ascii=False, indent=1))
    print(f"guard 0局: 到達 {base_pt['reach']:.2f} "
          f"({time.time() - t0:.0f}s)", flush=True)

    gc = 0
    for it in range(a.iters):
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
                    pool_models[name] = make_model(vocab, params)
                opp_model = pool_models[name]
            b, w = play_priv_game(
                rules, vocab, model, deck, kind, opp_model,
                seed=1000003 * a.seed + gc, first=first,
                learner_seat=learner_seat,
                search_budget=a.search_budget)
            batch.extend(b)
            total[kind] += 1
            if w == learner_seat:
                iter_wins[kind] += 1
                total_wins[kind] += 1
            gc += 1
        loss, grads = model.loss_and_grads(batch, aggregate=True)
        model.step(grads, lr=a.lr)
        cnt_s = " ".join(f"{k}:{counts[i]}" for i, k in enumerate(KINDS)
                         if counts[i])
        win_s = " ".join(
            f"{k} {iter_wins[k]}/{counts[i]}"
            for i, k in enumerate(KINDS) if counts[i])
        print(f"iter {it}: loss={loss:.3f} dec={len(batch)} [{cnt_s}] "
              f"勝ち [{win_s}] ({time.time() - t0:.0f}s)", flush=True)
        if (it + 1) % a.snapshot_every == 0 or it == a.iters - 1:
            name = f"iter{it + 1}"
            snap_path = snap_dir / f"priv_{name}.npz"
            model.save(str(snap_path))
            pool.append((name, {k: v.copy() for k, v in model.p.items()}))
            while len(pool) > a.pool_max:
                old, _ = pool.pop(0)
                pool_models.pop(old, None)
            print(f"  snapshot {snap_path} pool={[n for n, _ in pool]}",
                  flush=True)
        if (it + 1) % a.guard_every == 0 or it == a.iters - 1:
            ckpt_path = ckpt_dir / f"ckpt_{gc}.npz"
            model.save(str(ckpt_path))
            pt = guard_point(rules, vocab, deck, model, gc, a.guard_games)
            curve.append(pt)
            (OUT / "guard_curve.json").write_text(
                json.dumps(curve, ensure_ascii=False, indent=1))
            print(f"  guard {gc}局: 到達 {pt['reach']:.2f} "
                  f"手順 {pt['proc']} 出口 {pt['exit']} "
                  f"({time.time() - t0:.0f}s)", flush=True)
    print(f"学習完了: {gc} 局（{time.time() - t0:.0f}s）", flush=True)
    for k in KINDS:
        if total[k]:
            print(f"  相手 {k}: {total[k]} 局、学習者の勝率 "
                  f"{total_wins[k] / total[k]:.2f}", flush=True)

    sel = select_checkpoint(curve)
    src = ckpt_dir / f"ckpt_{sel['selected_games']}.npz"
    shutil.copyfile(src, a.out)
    (OUT / "selection.json").write_text(json.dumps(
        {"selection": sel, "curve": curve}, ensure_ascii=False, indent=1))
    print(f"最終モデル: {src} -> {a.out}（理由: {sel['reason']}）",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
