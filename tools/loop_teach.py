#!/usr/bin/env python3
"""ループフィニッシュ重点検証（Phase 20）。

2つの検証済みループ（サガ／アカシック）を教材として学習モデルに与え、
準備→ループ初期盤面→ループキルまで通せるか、大局観レベルで
手順の選択・欠損時の補正ができるかを段階別に測る。

サブコマンド:
  demos  : 各開始局面から教師（探索）の勝ち手順を記録
  train  : 本番モデル＋教材（taught）と 本番モデル＋自己対戦のみ（control）
  eval   : 局面ごとに base/control/taught の到達率と教師一致率を測定
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
import time
from pathlib import Path

os.environ.setdefault("DMSIM_RUST", "0")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np  # noqa: E402
import yaml  # noqa: E402

from dmsim.ai.demo import _teacher_choice, model_policy, record_game_demo  # noqa: E402
from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.selfplay import train_iters  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
from dmsim.engine.loop import LoopDetector  # noqa: E402
from dmsim.search.turn import charge_only_policy  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402

OUT = Path("/home/hatch/workspace/phase20")
# 土台は新レシピで 3,200 局学習した Colab モデル（Phase 21）
PROD = "/home/hatch/workspace/phase21/model_colab_newdeck.npz"

# 局面名 -> (spec パス, 教材を作る seed, 評価 seed)
POSITIONS = {
    "saga_prep": ("tests/saga_prep_setup.yaml", [0, 1], [2, 3, 4]),
    "saga_hidden": ("tests/saga_hidden_setup.yaml", [0, 1], [2, 3]),
    "saga_first": ("tests/saga_loop_first_setup.yaml", [0], [0]),
    "akashic_t5": ("tools/eval_specs/akashic_t5_assembled.yaml", [0, 1], [0, 1]),
    "akashic_min": ("tools/eval_specs/akashic_loop_min.yaml", [0, 1], [0, 1]),
    "akashic_no_orzekia": ("tools/eval_specs/akashic_no_orzekia.yaml", [], [0]),
}


def build_start(rules, name: str, seed: int):
    path, _d, _e = POSITIONS[name]
    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if name == "saga_prep":
        # Phase 15 の水増し対策: 相手に通常デッキ、自分の山札は 9 枚に制限
        spec["p1"] = {"deck": load_deck("data/decks/saga.yaml")}
        spec["deck_left"] = [9, None]
    elif name == "saga_hidden":
        spec["p1"] = {"deck": load_deck("data/decks/saga.yaml")}
    spec["seed"] = seed
    return sc.build(rules, spec)


def cmd_demos(args) -> int:
    t0 = time.time()
    rules = load_rules()
    vocab = Vocab(rules)
    all_demo: dict[str, list] = {}
    merged = OUT / "loop_demos.pkl"
    if merged.exists():
        with open(merged, "rb") as f:
            all_demo = pickle.load(f)
    for name, (_p, seeds, _e) in POSITIONS.items():
        if not seeds:
            continue
        if args.positions and name not in args.positions:
            continue
        items: list = []
        for sd in seeds:
            try:
                got = record_game_demo(rules, vocab,
                                       build_start(rules, name, sd),
                                       budget=args.budget)
                items += got
                print(f"{name} seed {sd}: {len(got)} 決定"
                      f"（{time.time() - t0:.0f}s）", flush=True)
            except Exception as ex:  # 教師が勝てなかった局面は教材にしない
                print(f"{name} seed {sd}: 教師が勝てず除外（{ex}）", flush=True)
        if items:
            all_demo[name] = items
            # 局面ごとに即保存する（長時間の記録が途中で落ちても残る）
            with open(merged, "wb") as f:
                pickle.dump(all_demo, f)
            print(f"{name}: 保存済み（累計 "
                  f"{sum(len(v) for v in all_demo.values())} 決定）", flush=True)
    total = sum(len(v) for v in all_demo.values())
    print(f"教材合計 {total} 決定: "
          + ", ".join(f"{k}={len(v)}" for k, v in all_demo.items()))
    return 0


def cmd_train(args) -> int:
    t0 = time.time()
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")
    with open(OUT / "loop_demos.pkl", "rb") as f:
        all_demo = pickle.load(f)
    demo = [it for v in all_demo.values() for it in v]
    print(f"教材 {len(demo)} 決定", flush=True)
    for name, dm, rep in [("control", None, 1), ("taught", demo, 3)]:
        m = Model.load(PROD)
        train_iters(rules, vocab, m, deck, deck, args.iters,
                    args.games_per_iter, seed=7, demo=dm, demo_repeat=rep,
                    log=lambda h: None)
        m.save(str(OUT / f"model_{name}.npz"))
        print(f"{name} 保存（{time.time() - t0:.0f}s）", flush=True)
    return 0


def play_from(start_eng, model, vocab, seed: int):
    """局面からモデルが指し、(勝ち, ループ検出, 理由, 終了ターン) を返す。"""
    eng = start_eng.clone()
    det = LoopDetector(me=0, report_all=True)
    pol = model_policy(model, vocab, np.random.default_rng(seed))
    looped = False
    for _ in range(2000):
        d = eng.advance()
        if d is None:
            break
        if d["player"] == 0:
            eng.answer(pol(eng, d))
            if det.observe(eng) is not None:
                looped = True
        else:
            eng.answer(charge_only_policy(eng, d))
    res = eng.s.result
    if not res:
        return False, looped, "no_result", eng.s.turn
    return res.get("winner") == 0, looped, res.get("reason"), res.get("turn")


def play_vs_search(start_eng, model, vocab, seed: int, budget: int = 400):
    """相手（P1）が探索プレイヤーの条件で局面から指す。

    P0 の自分のターンはモデルが1手ずつ指す。P1 のターンは TurnSearch が
    通しで指し、その間の P0 の反応は TurnSearch 内の相手方策（貪欲）が
    担う（Phase 19 の直接対決と同じ方式）。"""
    from dmsim.ai.demo import greedy_policy
    from dmsim.search.turn import TurnSearch
    eng = start_eng.clone()
    det = LoopDetector(me=0, report_all=True)
    pol = model_policy(model, vocab, np.random.default_rng(seed))
    greedy = greedy_policy()
    looped = False
    for _ in range(200):
        if eng.s.result is not None:
            break
        if eng.s.active == 1:
            ts = TurnSearch(1, budget, opp_policy=greedy)
            eng, _st = ts.run(eng)
        else:
            d = eng.advance()
            if d is None:
                break
            if d["player"] == 0:
                eng.answer(pol(eng, d))
                if det.observe(eng) is not None:
                    looped = True
            else:
                eng.answer(greedy(eng, d))
    res = eng.s.result
    if not res:
        return False, looped, "no_result"
    return res.get("winner") == 0, looped, res.get("reason")


def first_decision_agreement(rules, vocab, model, name: str, seed: int):
    """局面の最初の決定で、モデルの貪欲な選択が教師と一致するか。"""
    eng = build_start(rules, name, seed)
    for _ in range(50):
        d = eng.advance()
        if d is None:
            return None
        if d["player"] == 0:
            teacher = _teacher_choice(eng, d, 0, 600)
            pol = model_policy(model, vocab, np.random.default_rng(0),
                               greedy=True)
            mine = pol(eng, d)
            return sorted(mine) == sorted(teacher)
        eng.answer(charge_only_policy(eng, d))
    return None


def cmd_eval(args) -> int:
    t0 = time.time()
    rules = load_rules()
    vocab = Vocab(rules)
    models = {
        "base": Model.load(PROD),
        "control": Model.load(str(OUT / "model_control.npz")),
        "taught": Model.load(str(OUT / "model_taught.npz")),
    }
    for name, (_p, _d, eval_seeds) in POSITIONS.items():
        for mname, m in models.items():
            wins = kills = stalls = turns = n = 0
            for sd in eval_seeds:
                start = build_start(rules, name, sd)
                for t in range(args.trials):
                    w, looped, reason, turn = play_from(
                        start, m, vocab, 9000 + sd * 100 + t)
                    n += 1
                    wins += w
                    kills += w and looped
                    stalls += reason in ("no_result", "step_limit",
                                         "turn_limit")
                    turns += turn or 0
            print(f"{name} / {mname}: 勝率 {wins / n:.2f}、"
                  f"ループキル {kills / n:.2f}、停滞 {stalls / n:.2f}、"
                  f"平均終了ターン {turns / n:.1f}（{n} 試行、"
                  f"{time.time() - t0:.0f}s）", flush=True)
    print("--- 探索プレイヤー相手（準備局面のみ） ---", flush=True)
    for name in ("saga_prep", "saga_hidden"):
        _p, _d, eval_seeds = POSITIONS[name]
        for mname in ("base", "taught"):
            m = models[mname]
            wins = kills = n = 0
            for sd in eval_seeds[:2]:
                start = build_start(rules, name, sd)
                for t in range(3):
                    w, looped, _r = play_vs_search(
                        start, m, vocab, 7000 + sd * 100 + t)
                    n += 1
                    wins += w
                    kills += w and looped
            print(f"{name} / {mname} vs 探索: 勝率 {wins / n:.2f}、"
                  f"ループキル {kills / n:.2f}（{n} 試行、"
                  f"{time.time() - t0:.0f}s）", flush=True)
    print("--- 最初の決定の教師一致率 ---", flush=True)
    for name, (_p, _d, eval_seeds) in POSITIONS.items():
        sd = eval_seeds[0]
        row = {}
        for mname in ("base", "taught"):
            row[mname] = first_decision_agreement(
                rules, vocab, models[mname], name, sd)
        print(f"{name}: base={row['base']} taught={row['taught']}"
              f"（{time.time() - t0:.0f}s）", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    dm = sub.add_parser("demos")
    dm.add_argument("--positions", nargs="*", default=None)
    dm.add_argument("--budget", type=int, default=600)
    tr = sub.add_parser("train")
    tr.add_argument("--iters", type=int, default=20)
    tr.add_argument("--games-per-iter", type=int, default=8)
    ev = sub.add_parser("eval")
    ev.add_argument("--trials", type=int, default=8)
    args = ap.parse_args()
    return {"demos": cmd_demos, "train": cmd_train,
            "eval": cmd_eval}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
