#!/usr/bin/env python3
"""Phase 26-3 の評価: 土台／リーグ（26-2）／特権＋トラッカー（26-3）を
Phase 24・26-2 と同一条件で比較する。

指標: ミラー30局（シード 40000+i）のループキル数と初検出の自ターン、
対貪欲40局（seed=999）の勝率、対探索プレイヤー（予算300）20局の勝率。
4段階診断は tools/loop_stages.py を別途 --games 40 で回す。

--value-check では、共有の保持軌跡（土台の方策で収集、特権エンコード
付き）上で各モデルの価値予測精度（MSE と符号一致率）を、特権入力
あり／なしで測る。特権価値の効果の切り分け用。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.selfplay import collect_games, evaluate  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402
from tools.game_content import play_content  # noqa: E402
from tools.phase26_eval import eval_vs_search  # noqa: E402

MODELS = {
    "土台(11,200局)": "/home/hatch/workspace/phase21/model_colab_big.npz",
    "リーグ(26-2)": "/home/hatch/workspace/phase26/model_league.npz",
    "特権+トラッカー(26-3)": "/home/hatch/workspace/phase26priv/model_priv.npz",
}


def value_check(rules, vocab, deck, models: dict[str, Model],
                games: int = 40, seed: int = 900) -> None:
    """共有軌跡上で価値の予測精度を測る（特権あり／なし）。"""
    base = models["土台(11,200局)"]
    batch, _w = collect_games(rules, vocab, base, deck, deck, games=games,
                              seed=seed, privileged=True)
    print(f"[価値チェック] 保持軌跡 {games} 局・{len(batch)} 決定"
          f"（土台の方策で収集、seed={seed}）", flush=True)
    rets = np.array([it["ret"] for it in batch], dtype=np.float64)
    for name, m in models.items():
        for priv in (False, True):
            vals = []
            for it in batch:
                st = it["st"]
                if not priv:
                    st = {k: v for k, v in st.items()
                          if not k.startswith("priv")}
                _s, v, _c, _cache = m.forward(st, it["op"])
                vals.append(v)
            vals = np.array(vals, dtype=np.float64)
            mse = float(np.mean((vals - rets) ** 2))
            sign = float(np.mean((vals > 0) == (rets > 0)))
            mode = "特権あり" if priv else "特権なし"
            print(f"  [{name}] {mode}: MSE {mse:.3f} 符号一致 {sign:.3f}",
                  flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-search", action="store_true",
                    help="対探索の評価（遅い）を省略する")
    ap.add_argument("--value-check", action="store_true",
                    help="価値の予測精度チェックも行う")
    ap.add_argument("--only", default="",
                    help="評価するモデル名の部分一致（空なら全て）")
    a = ap.parse_args()
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")
    loaded: dict[str, Model] = {}
    for name, path in MODELS.items():
        if a.only and a.only not in name:
            continue
        m = Model.load(path)
        loaded[name] = m
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
    if a.value_check:
        if len(loaded) < len(MODELS):
            loaded = {name: Model.load(path)
                      for name, path in MODELS.items()}
        value_check(rules, vocab, deck, loaded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
