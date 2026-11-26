"""発見の還元（Phase 11）: 探索が見つけたコンボを学習の教材にする。

探索（loop_first.two_stage）が検証済みのループ証明書と勝ち筋を持っている。
それを再生しながら自分の決定を (st, op, choice, ret=+1) のバッチ項目として
記録すると、通常の自己対戦バッチとそのまま混ぜて学習できる（loss は
REINFORCE なので、正解の手の log 確率を押し上げる教材になる）。
ランダムな試行ではほぼ踏めない長い正確な手順を方策に教えるための仕組み。

教材の構成:
- ループ区間: 証明書の actions（意味キー）を fast_forward で再生し、
  answer を横取りして自分の決定だけを記録する。
- 仕上げのターン: 証明書の周回後に探索（TurnSearch）で勝ちが確認された
  状態から、各決定で「候補手を指した後に TurnSearch で読み切る」教師で指す。
"""
from __future__ import annotations

import numpy as np

from ..engine.play import run
from ..search.leaf_eval import Weights, evaluate
from ..search.turn import TurnSearch, charge_only_policy, greedy_policy
from .encode import OPT_NUM, encode_options, encode_state

_W = Weights()
_DUMMY_OP = {"opt_defn": np.zeros(1, np.int32),
             "opt_num": np.zeros((1, OPT_NUM), np.float32),
             "min": 0, "max": 1, "kind": "pass"}


def state_value(model, st: dict) -> float:
    """局面だけから価値ヘッドの値を読む（価値は選択肢に依存しない）。"""
    v = model.forward(st, _DUMMY_OP)[1]
    return float(v.item()) if hasattr(v, "item") else float(v)


def policy_order_fn(model, vocab, cap: int | None = None):
    """TurnSearch の order_fn: 候補手を学習方策の log 確率が高い順に並べる。
    cap を与えると上位 cap 個に絞る（枝刈り）。絞らない形が既定で、
    並べ替えだけなら探索の完全性は保たれる。"""
    pl_logp = model._pl_logp

    def order(eng, d, cands):
        st = encode_state(eng, d["player"], vocab)
        op = encode_options(eng, d, vocab)
        scores = model.forward(st, op)[0]
        scored = sorted(cands, key=lambda c: -pl_logp(scores, list(c)))
        return scored[:cap] if cap else scored

    return order


def model_policy(model, vocab, rng, greedy: bool = False):
    """モデルを (eng, decision) -> choice の方策関数にする。"""
    def pol(eng, d):
        st = encode_state(eng, d["player"], vocab)
        op = encode_options(eng, d, vocab)
        choice, _, _ = model.act(st, op, rng, greedy=greedy)
        return sorted(choice)
    return pol


def execution_rate(rules, vocab, model, start_eng, me: int = 0,
                   trials: int = 16, greedy: bool = False, seed: int = 0) -> float:
    """start_eng（コンボが打てる局面）からモデルが指して勝てる割合。"""
    wins = 0
    for t in range(trials):
        eng = start_eng.clone()
        pols = [charge_only_policy, charge_only_policy]
        pols[me] = model_policy(model, vocab, np.random.default_rng(seed + t),
                                greedy)
        res = run(eng, pols)
        if res and res.get("winner") == me:
            wins += 1
    return wins / trials


def _teacher_choice(eng, d, me: int, budget: int) -> list[int]:
    """候補手を1つ指した後に TurnSearch でターン終了まで読み、最良の手を返す。
    勝ちに届く手があればそれを最優先する（教材生成専用の重い教師）。"""
    from ..engine.core import IllegalAnswer
    n = len(d["options"])
    lo, hi = d["min"], d["max"]
    cands = [greedy_policy()(eng, d)]           # 常に合法な基準候補
    if lo == hi == 1:
        cands += [[i] for i in range(n)]
    elif lo == hi:
        cands += [list(range(lo)), list(range(n - lo, n))]
    else:
        cands += [list(range(lo)), list(range(hi))]
    best, best_score = None, float("-inf")
    seen = set()
    for c in cands:
        key = tuple(sorted(c))
        if key in seen or not lo <= len(key) <= hi:
            continue
        seen.add(key)
        e2 = eng.clone()
        try:
            e2.answer(sorted(c))
        except IllegalAnswer:
            continue
        leaf, _ = TurnSearch(me, budget).run(e2)
        r = leaf.s.result
        score = 1e18 if (r and r.get("winner") == me) else evaluate(leaf, me, _W)
        if score > best_score:
            best, best_score = sorted(c), score
    if best is None:  # 全候補が不合法・範囲外のときは常に合法な基準候補へ
        best = sorted(cands[0])
    return best


def record_demo(rules, vocab, finding, cycles: int, me: int = 0,
                budget: int = 800) -> list[dict]:
    """検証済み Finding（ループ＋勝ち）から教材バッチを作る。勝てなければ例外。"""
    from ..engine.loop import fast_forward
    eng = finding.start.clone()
    items: list[dict] = []
    orig_answer = eng.answer

    def recording_answer(choice):
        d = eng.s.waiting
        if d is not None and d["player"] == me:
            items.append({"st": encode_state(eng, me, vocab),
                          "op": encode_options(eng, d, vocab),
                          "choice": sorted(choice), "ret": 1.0})
        return orig_answer(choice)

    eng.answer = recording_answer
    try:
        fast_forward(eng, finding.cert, cycles)
    finally:
        eng.answer = orig_answer
    # 仕上げのターン: 教師で指し切りながら記録する
    while True:
        d = eng.advance()
        if d is None:
            break
        if d["player"] != me:
            eng.answer(charge_only_policy(eng, d))
            continue
        choice = _teacher_choice(eng, d, me, budget)
        items.append({"st": encode_state(eng, me, vocab),
                      "op": encode_options(eng, d, vocab),
                      "choice": choice, "ret": 1.0})
        eng.answer(choice)
    res = eng.s.result
    if not res or res.get("winner") != me:
        raise RuntimeError(f"demo recording did not win: {res}")
    return items
