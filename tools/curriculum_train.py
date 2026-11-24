#!/usr/bin/env python3
"""Phase 23: 局面カリキュラム学習。

開幕からの自己対戦に、検証済み局面（最小盤面 M を含む）からの開始、
探索プレイヤー相手の対戦、教師手順の模倣（方策側のみ）を混ぜる。
進捗はループキル率で追う。

混合比（1 iter あたり、既定）:
  開幕の自己対戦 10 局 / 局面開始 6 局 / 探索相手 1 局（2 iter に1回）
局面の段階（逆カリキュラム）:
  A 実行: saga_M, saga_first, akashic_min
  B 組立: saga_hidden, akashic_t5
  C 準備: saga_prep
  A の勝率が高くなったら B、C の配分を増やす。
"""
from __future__ import annotations

import argparse
import pickle
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from dmsim.ai.demo import greedy_policy  # noqa: E402
from dmsim.ai.encode import Vocab, encode_options, encode_state  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.selfplay import collect_games, model_policy  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.engine.loop import LoopDetector  # noqa: E402
from dmsim.search.turn import TurnSearch  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402
from tools.game_content import play_content  # noqa: E402
from tools.loop_teach import build_start  # noqa: E402

OUT = Path("/home/hatch/workspace/phase23")
BASE = "/home/hatch/workspace/phase21/model_colab_big.npz"
DEMOS = "/home/hatch/workspace/phase20/loop_demos.pkl"
STAGES = {
    "A": ["saga_M", "saga_first", "akashic_min"],
    "B": ["saga_hidden", "akashic_t5"],
    "C": ["saga_prep"],
}


def play_recorded(start_eng, model, vocab, rng, opp_mode: str, seed: int):
    """局面から1局指し、P0 の軌跡とループ検出を返す。

    opp_mode: "greedy"（相手は貪欲）/ "search"（相手は TurnSearch）。
    戻り: (batch要素のリスト, 勝敗, ループ検出)。
    """
    eng = start_eng.clone()
    det = LoopDetector(me=0, report_all=True)
    pol = model_policy(model, vocab, rng)
    greedy = greedy_policy()
    traj = []
    looped = False

    def record_and_answer(d):
        st = encode_state(eng, d["player"], vocab)
        op = encode_options(eng, d, vocab)
        choice, _, _ = model.act(st, op, rng)
        traj.append((st, op, sorted(choice)))
        eng.answer(sorted(choice))

    for _ in range(240):
        if eng.s.result is not None:
            break
        if eng.s.active == 1 and opp_mode == "search":
            ts = TurnSearch(1, 300, opp_policy=greedy)
            eng, _st = ts.run(eng)
            continue
        d = eng.advance()
        if d is None:
            break
        if d["player"] == 0:
            record_and_answer(d)
            if det.observe(eng) is not None:
                looped = True
        else:
            eng.answer(greedy(eng, d))
    res = eng.s.result
    w = res.get("winner") if res else None
    ret = 0.0 if w is None else (1.0 if w == 0 else -1.0)
    batch = [{"st": st, "op": op, "choice": ch, "ret": ret}
             for st, op, ch in traj]
    return batch, w, looped


def loop_ret(w, looped: bool) -> float:
    """局面ゲーム用の報酬（v2）: ループキルを成功と定義する。

    通常の勝ちは小さなプラスに留め、ループの完走だけを強く強化する。
    開幕ゲームの報酬（勝敗のみ）は変えない。"""
    if w is None:
        return 0.0
    if w != 0:
        return -1.0
    return 1.0 if looped else 0.2


def eval_positions(rules, vocab, model, trials: int = 4):
    """段階別の勝率とループキル率（相手は貪欲）。"""
    out = {}
    for stage, names in STAGES.items():
        wins = kills = n = 0
        for name in names:
            for sd in (0, 1):
                start = build_start(rules, name, sd)
                for t in range(trials // 2):
                    _b, w, looped = play_recorded(
                        start, model, vocab,
                        np.random.default_rng(31000 + sd * 10 + t),
                        "greedy", 0)
                    n += 1
                    wins += w == 0
                    kills += (w == 0 and looped)
        out[stage] = (wins / n, kills / n, n)
    return out


def mirror_loop_rate(rules, vocab, model, deck, games: int = 12):
    """2つのシード帯で測る（単一の連続シード帯は偏ることが Phase 23 で判明）。"""
    kills = n = 0
    for base in (40000, 60000):
        rows = [play_content(rules, vocab, deck, base + i,
                             (("policy", model), ("policy", model)))
                for i in range(games)]
        rows = [r for r in rows if r]
        kills += sum(1 for r in rows if r["loop_own_turn"] is not None)
        n += len(rows)
    return kills, n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=40)
    ap.add_argument("--opening", type=int, default=10)
    ap.add_argument("--positions", type=int, default=6)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--bc-lr", type=float, default=1e-3)
    ap.add_argument("--bc-every", type=int, default=1,
                    help="BC（模倣）の更新を何 iter に1回行うか")
    ap.add_argument("--loop-reward", action="store_true",
                    help="局面ゲームの報酬をループキル基準にする（v2）")
    ap.add_argument("--eval-every", type=int, default=10)
    ap.add_argument("--init", default=BASE)
    ap.add_argument("--out", default=str(OUT / "model_curriculum.npz"))
    a = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")
    model = Model.load(a.init)
    with open(DEMOS, "rb") as f:
        demos_raw = pickle.load(f)
    demo_batch = [{"st": x["st"], "op": x["op"], "choice": x["choice"]}
                  for items in demos_raw.values() for x in items]
    print(f"init={a.init} demos={len(demo_batch)}", flush=True)

    rng_master = np.random.default_rng(777)
    t0 = time.time()
    for it in range(a.iters):
        # 逆カリキュラム: 実行（A）→ 組立（B）→ 準備（C）へ配分を移す
        if it < a.iters // 3:
            stage_weight = {"A": 4, "B": 2, "C": 0}
        elif it < 2 * a.iters // 3:
            stage_weight = {"A": 2, "B": 3, "C": 1}
        else:
            stage_weight = {"A": 1, "B": 2, "C": 3}
        batch, _w = collect_games(rules, vocab, model, deck, deck,
                                  a.opening, seed=100 + it)
        pool = [n for s, wgt in stage_weight.items()
                for n in STAGES[s] * wgt]
        for k in range(a.positions):
            name = pool[(it * a.positions + k) % len(pool)]
            sd = int(rng_master.integers(0, 2))
            start = build_start(rules, name, sd)
            b, w2, l2 = play_recorded(
                start, model, vocab,
                np.random.default_rng(20000 + it * 100 + k), "greedy", 0)
            if a.loop_reward:
                r = loop_ret(w2, l2)
                b = [{**x, "ret": r} for x in b]
            batch.extend(b)
        if it % 2 == 1:   # 探索プレイヤー相手（開幕から）
            eng = Engine.new_game(rules, [deck, deck], 500 + it,
                                  first_player=it % 2)
            b, _w3, _l3 = play_recorded(
                eng, model, vocab, np.random.default_rng(30000 + it),
                "search", 0)
            batch.extend(b)
        loss, grads = model.loss_and_grads(batch)
        model.step(grads, lr=a.lr)
        if it % a.bc_every == 0:
            _bl, bgrads = model.bc_loss_and_grads(demo_batch)
            model.step(bgrads, lr=a.bc_lr)
        print(f"iter {it}: loss={loss:.3f} decisions={len(batch)} "
              f"配分={stage_weight} ({time.time() - t0:.0f}s)", flush=True)
        if (it + 1) % a.eval_every == 0 or it == a.iters - 1:
            ev = eval_positions(rules, vocab, model)
            kills, n = mirror_loop_rate(rules, vocab, model, deck)
            line = " / ".join(
                f"{s}: 勝率 {ev[s][0]:.2f} ループキル {ev[s][1]:.2f}"
                for s in "ABC")
            print(f"[eval iter {it + 1}] {line} / "
                  f"ミラー ループキル {kills}/{n}", flush=True)
            model.save(a.out)
            snap = a.out.replace(".npz", f"_iter{it + 1}.npz")
            model.save(snap)
            print(f"  saved {a.out} / {snap}", flush=True)
    print(f"完了（{time.time() - t0:.0f}s）", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
