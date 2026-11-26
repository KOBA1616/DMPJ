#!/usr/bin/env python3
"""Phase 26-4 の評価: ID 表現 vs 属性表現（どちらもゼロから2,000局）を
Phase 24〜26-3 と同一条件で比較し、汎化も測る。

主指標: ミラー30局（シード 40000+i）のループキル、対貪欲40局
（seed=999）、対探索プレイヤー（予算300）20局、loop_stages 診断
40局（到達・手順・出口）。土台（11,200局）の数字は 26-3 の記録を
併記する（同一条件で測定済み）。

汎化の確認（属性表現の狙い = 未学習カードへの汎化）:
1. 未見デッキでの対戦: saga_legacy.yaml（現行サガと共通のカードは
   22種中6種だけ。残り16種はどちらのモデルも学習で見ていない）で
   モデル対貪欲40局。ID 表現では未見カードの埋め込みは初期値の
   乱数のまま、属性表現では属性から計算される。
2. 表現空間の近傍一貫性: 各カードの表現ベクトルについて、コサイン
   類似度 top-5 の近傍が「主たる役割（属性の派生動詞の最大値）」を
   共有する割合。未見カード集合と既見（サガ）カード集合で分けて
   測る。土台（ID・11,200局学習）も同じ物差しで測る。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from dmsim.ai.attributes import build_attribute_matrix  # noqa: E402
from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.model_attr import AttrModel  # noqa: E402
from dmsim.ai.selfplay import evaluate  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402
from tools.game_content import play_content  # noqa: E402
from tools.loop_stages import diagnose  # noqa: E402
from tools.phase26_eval import eval_vs_search  # noqa: E402

BASE = "/home/hatch/workspace/phase21/model_colab_big.npz"
OUT = Path("/home/hatch/workspace/phase26attr")


def rep_vectors(model) -> np.ndarray:
    """カード表現ベクトル [V, D]（モデルが実際に使う表現）。"""
    if isinstance(model, AttrModel):
        return model._embed(np.arange(len(model.attr)))
    return model.p["emb"]


def neighbor_consistency(rules, vocab, deck, models: dict) -> None:
    attr, names = build_attribute_matrix(rules, vocab)
    verb_cols = [i for i, n in enumerate(names) if n.startswith("verb_")]
    verb = attr[:, verb_cols]
    label = np.where(verb.max(axis=1) > 0, verb.argmax(axis=1), -1)
    saga_defns = {vocab.idx(d) for d in set(deck)}
    # 偶然の一致率（ラベルの事前分布からの期待値）
    labs, counts = np.unique(label[label >= 0], return_counts=True)
    prior = counts / counts.sum()
    chance = float((prior ** 2).sum())
    print(f"[近傍一貫性] 役割ラベル {len(labs)} 種、偶然の一致率 "
          f"{chance:.3f}", flush=True)
    for name, m in models.items():
        rep = rep_vectors(m).astype(np.float32)
        rep /= np.maximum(np.linalg.norm(rep, axis=1, keepdims=True), 1e-9)
        sims = rep @ rep.T
        for split, targets in (
                ("既見（サガ）", sorted(i for i in saga_defns
                                        if label[i] >= 0)),
                ("未見", [i for i in range(1, len(vocab))
                          if i not in saga_defns and label[i] >= 0])):
            fracs = []
            for i in targets:
                top = np.argpartition(-sims[i], 6)[:6]
                top = [j for j in top if j != i][:5]
                fracs.append(np.mean([label[j] == label[i] for j in top]))
            print(f"  [{name}] {split} {len(targets)}枚: "
                  f"top-5 近傍の役割一致 {np.mean(fracs):.3f}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-search", action="store_true")
    ap.add_argument("--skip-stages", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    rules = load_rules()
    vocab = Vocab(rules)
    deck = load_deck("data/decks/saga.yaml")
    legacy = load_deck("data/decks/saga_legacy.yaml")
    models: dict[str, Model] = {
        "ID表現(ゼロから2,000局)": Model.load(str(OUT / "model_id.npz")),
        "属性表現(ゼロから2,000局)": AttrModel.load(
            str(OUT / "model_attr.npz")),
        "土台(11,200局)": Model.load(BASE),
    }
    for name, m in models.items():
        if a.only and a.only not in name:
            continue
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
        rl = evaluate(rules, vocab, m, legacy, legacy, 40, seed=999,
                      opponent="greedy")
        print(f"[{name}] 未見デッキ(legacy)対貪欲40局: "
              f"{rl['win_rate']:.2f}", flush=True)
        if not a.skip_search:
            rs = eval_vs_search(rules, vocab, m, deck)
            print(f"[{name}] 対探索(予算300)20局: {rs['win_rate']:.2f}"
                  f"（{rs['wins']}勝 {rs['losses']}敗 {rs['draws']}分）",
                  flush=True)
        if not a.skip_stages:
            diagnose(rules, vocab, deck, m, games=40, label=name)
    neighbor_consistency(rules, vocab, deck, models)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
