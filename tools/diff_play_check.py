#!/usr/bin/env python3
"""差分検証ハーネス。

同一シード・同一方策のプレイアウトを2回実行し、全決定点の digest 列と
最終結果が一致するか比べる。エンジン内部の表現を変える実験（copy-on-write
など）で「振る舞いが変わっていない」ことを確認するための安全網。

使い方:
  python3 tools/diff_play_check.py [--seeds 12] [--max-decisions 150]
  python3 tools/diff_play_check.py --self-test
      片方の回答を1箇所だけ変え、乖離を検出できることを確認する。
      ハーネス自体が無力でないことの証明用。

方策はシード固定の決定的乱数。digest は記録照合と同じ GameState.digest()
を使う（fast_key ではない）。
"""
import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dmsim import load_rules
from dmsim.engine import Engine
from dmsim.eval.measure import load_deck


def policy_answer(d, rng):
    n = len(d["options"])
    lo, hi = d["min"], d["max"]
    if lo == n and n > 1:
        idx = list(range(n))
        rng.shuffle(idx)
        return idx
    k = rng.randrange(lo, hi + 1)
    return rng.sample(range(n), k) if k else []


def playout(rules, deck, seed, policy_seed, max_decisions, diverge_at=None):
    """決定点ごとの digest 列と最終結果を返す。diverge_at は自己検証用:
    その決定点で方策と違う回答をして乖離を作る。"""
    e = Engine.new_game(rules, [deck, deck], seed, 0)
    rng = random.Random(policy_seed)
    digests = []
    step = 0
    while step < max_decisions:
        d = e.advance()
        if d is None or e.s.result:
            break
        digests.append(e.s.digest())
        ans = policy_answer(d, rng)
        if diverge_at is not None and step == diverge_at:
            n = len(d["options"])
            alt = [(i + 1) % n for i in ans] if ans else [0]
            if alt != ans:
                ans = alt
        e.answer(ans)
        step += 1
    r = e.s.result
    tail = f"result={r['winner']}/{r['reason']}/turn{r['turn']}" if r else "unfinished"
    return digests, tail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--max-decisions", type=int, default=150)
    ap.add_argument("--deck", default="data/decks/saga.yaml")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    rules = load_rules()
    deck = load_deck(args.deck)
    bad = 0
    for seed in range(1, args.seeds + 1):
        a, ra = playout(rules, deck, seed, 1000 + seed, args.max_decisions)
        if args.self_test:
            b, rb = playout(rules, deck, seed, 1000 + seed, args.max_decisions,
                            diverge_at=5)
            div = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
            detected = div is not None or ra != rb or len(a) != len(b)
            print(f"seed {seed}: decisions={len(a)} "
                  f"divergence={'detected@' + str(div) if detected else 'MISSED'}")
            bad += 0 if detected else 1
        else:
            b, rb = playout(rules, deck, seed, 1000 + seed, args.max_decisions)
            same = a == b and ra == rb
            print(f"seed {seed}: decisions={len(a)} identical={same} {ra}")
            bad += 0 if same else 1
    print(f"== {'self-test' if args.self_test else 'identity'}: "
          f"{args.seeds - bad}/{args.seeds} OK")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
