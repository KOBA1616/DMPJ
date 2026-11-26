#!/usr/bin/env python3
"""Phase 24: 到達ボーナス（自己模倣）＋探索相手混合の学習。

(a) 開幕の自己対戦で「最小盤面 M に到達したプレイヤー」の到達までの
    決定列（取得・到達の区間）と、「到達して勝ったプレイヤー」の
    到達後の決定列（手順・出口の区間）を、方策側のみの模倣（BC）で
    追加強化する。価値の目標（勝敗）は変えない。
(c) 一部の局では相手を探索プレイヤー（TurnSearch）に置き換える。

進捗は tools/loop_stages.py の4段階診断で追う。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from dmsim.ai.encode import Vocab, encode_options, encode_state  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.engine.loop import LoopDetector  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402
from tools.curriculum_train import play_recorded  # noqa: E402
from tools.loop_stages import diagnose, reached_M  # noqa: E402

OUT = Path("/home/hatch/workspace/phase24")
BASE = "/home/hatch/workspace/phase21/model_colab_big.npz"


def collect_tracked(rules, vocab, model, deck, games: int, seed: int):
    """自己対戦を集め、局ごとに到達・ループの区間情報も返す。

    戻り: (通常バッチ, 到達区間バッチ, 実行区間バッチ, 統計 dict)
    """
    rng = np.random.default_rng(seed)
    batch, assembly, execution = [], [], []
    stats = {"games": games, "reached": 0, "looped": 0, "reach_won": 0}
    for g in range(games):
        first = g % 2
        eng = Engine.new_game(rules, [deck, deck], seed * 100003 + g, first)
        trajs = {0: [], 1: []}
        reach_at = {0: None, 1: None}
        loop_at = {0: None, 1: None}
        dets = {p: LoopDetector(me=p, report_all=True) for p in (0, 1)}

        def pol(e, d, _t=trajs):
            st = encode_state(e, d["player"], vocab)
            op = encode_options(e, d, vocab)
            choice, _, _ = model.act(st, op, rng)
            _t[d["player"]].append((st, op, sorted(choice)))
            return sorted(choice)

        for _ in range(500):
            if eng.s.result is not None:
                break
            d = eng.advance()
            if d is None:
                break
            p = d["player"]
            eng.answer(pol(eng, d))
            for q in (0, 1):
                if reach_at[q] is None and reached_M(eng, rules, q):
                    reach_at[q] = len(trajs[q])
                    stats["reached"] += 1
                if (loop_at[q] is None and dets[q].observe(eng)
                        is not None):
                    loop_at[q] = len(trajs[q])
                    stats["looped"] += 1
        res = eng.s.result
        w = res.get("winner") if res else None
        for q in (0, 1):
            ret = 0.0 if w is None else (1.0 if w == q else -1.0)
            for st, op, ch in trajs[q]:
                batch.append({"st": st, "op": op, "choice": ch, "ret": ret})
            if reach_at[q] is not None:
                seg = trajs[q][:reach_at[q]]
                assembly.extend({"st": st, "op": op, "choice": ch}
                                for st, op, ch in seg)
                if w == q:
                    stats["reach_won"] += 1
                    execution.extend({"st": st, "op": op, "choice": ch}
                                     for st, op, ch in trajs[q][reach_at[q]:])
    return batch, assembly, execution, stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=60)
    ap.add_argument("--games-per-iter", type=int, default=16)
    ap.add_argument("--search-games", type=int, default=0,
                    help="1 iter あたりの探索相手の局数（c）")
    ap.add_argument("--milestone", action="store_true",
                    help="到達ボーナス（自己模倣）を使う（a）")
    ap.add_argument("--ms-lr", type=float, default=1e-3)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--eval-every", type=int, default=20)
    ap.add_argument("--init", default=BASE)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")
    model = Model.load(a.init)
    print(f"init={a.init} milestone={a.milestone} "
          f"search_games={a.search_games}", flush=True)
    t0 = time.time()
    for it in range(a.iters):
        batch, asm, exe, stats = collect_tracked(
            rules, vocab, model, deck, a.games_per_iter, seed=100 + it)
        for k in range(a.search_games):
            eng = Engine.new_game(rules, [deck, deck], 900 + it * 10 + k,
                                  first_player=k % 2)
            b, _w, _l = play_recorded(
                eng, model, vocab,
                np.random.default_rng(40000 + it * 10 + k), "search", 0)
            batch.extend(b)
        loss, grads = model.loss_and_grads(batch)
        model.step(grads, lr=a.lr)
        ms_note = ""
        if a.milestone and (asm or exe):
            ms_batch = asm + exe
            _bl, bgrads = model.bc_loss_and_grads(ms_batch)
            model.step(bgrads, lr=a.ms_lr)
            ms_note = f" milestone={len(ms_batch)}(asm {len(asm)}/exe {len(exe)})"
        print(f"iter {it}: loss={loss:.3f} dec={len(batch)} "
              f"到達 {stats['reached']}/{2 * a.games_per_iter} "
              f"ループ {stats['looped']}{ms_note} "
              f"({time.time() - t0:.0f}s)", flush=True)
        if (it + 1) % a.eval_every == 0 or it == a.iters - 1:
            diagnose(rules, vocab, deck, model, games=24,
                     seed0=40000, label=f"iter {it + 1}")
            snap = a.out.replace(".npz", f"_iter{it + 1}.npz")
            model.save(snap)
            model.save(a.out)
            print(f"  saved {snap}", flush=True)
    print(f"完了（{time.time() - t0:.0f}s）", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
