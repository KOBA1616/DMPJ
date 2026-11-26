#!/usr/bin/env python3
"""Phase 26-2 の評価: 土台とリーグ学習モデルを Phase 24 と同一条件で比較。

指標: ミラー30局（シード 40000+i）のループキル数と初検出の自ターン、
対貪欲40局（seed=999）の勝率、対探索プレイヤー（予算300）20局の勝率。
4段階診断は tools/loop_stages.py を別途 --games 40 で回す。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.selfplay import evaluate  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402
from tools.game_content import play_content  # noqa: E402
from tools.league_train import play_league_game  # noqa: E402

MODELS = {
    "土台(11,200局)": "/home/hatch/workspace/phase21/model_colab_big.npz",
    "リーグ(26-2)": "/home/hatch/workspace/phase26/model_league.npz",
}


def eval_vs_search(rules, vocab, model, deck, games: int = 20,
                   budget: int = 300, seed0: int = 70000) -> dict:
    """モデル（greedy 選択）対 TurnSearch（予算300）の勝率。

    座席と先攻の割り当ては selfplay.evaluate と同じ流儀
    （モデル座席 = g%2、先攻 = g%2）。
    """
    wins = losses = draws = 0
    for g in range(games):
        seat = g % 2
        _b, w = play_league_game(
            rules, vocab, model, deck, "search", None,
            seed=seed0 + g, first=g % 2, learner_seat=seat,
            search_budget=budget, learner_greedy=True, collect=False)
        if w is None:
            draws += 1
        elif w == seat:
            wins += 1
        else:
            losses += 1
    n = wins + losses
    return {"games": games, "wins": wins, "losses": losses, "draws": draws,
            "win_rate": wins / n if n else 0.0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-search", action="store_true",
                    help="対探索の評価（遅い）を省略する")
    a = ap.parse_args()
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")
    for name, path in MODELS.items():
        m = Model.load(path)
        rows = [play_content(rules, vocab, deck, 40000 + i,
                             (("policy", m), ("policy", m)))
                for i in range(30)]
        rows = [r for r in rows if r]
        kills = sum(1 for r in rows if r["loop_own_turn"] is not None)
        det = [r["loop_own_turn"] for r in rows
               if r["loop_own_turn"] is not None]
        turns = sum(r["turns"] for r in rows) / len(rows)
        det_s = f"{sum(det) / len(det):.1f}" if det else "-"
        print(f"[{name}] ミラー30局: ループキル {kills}/30、"
              f"初検出 {det_s}、総ターン {turns:.1f}", flush=True)
        r = evaluate(rules, vocab, m, deck, deck, 40, seed=999,
                     opponent="greedy")
        print(f"[{name}] 対貪欲40局: {r['win_rate']:.2f}", flush=True)
        if not a.skip_search:
            rs = eval_vs_search(rules, vocab, m, deck)
            print(f"[{name}] 対探索(予算300)20局: {rs['win_rate']:.2f}"
                  f"（{rs['wins']}勝 {rs['losses']}敗 {rs['draws']}分）",
                  flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
