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
from dmsim.engine import state as state_mod
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


def branch_playout(rules, deck, seed, policy_seed, max_decisions, branch_steps):
    """COW 用の分岐チェック。各決定点でエンジンを複製し、複製側だけを
    別の方策で branch_steps 決定まで進めてから、親の digest が変わって
    いないことを確認する。共有されたカード／ゾーンへの書き込み漏れは
    親の digest を変えるので、その場で検出できる。
    戻り値: (親の digest 列, 最終結果, 漏れが起きた決定点の列)。"""
    e = Engine.new_game(rules, [deck, deck], seed, 0)
    rng = random.Random(policy_seed)
    brng = random.Random(policy_seed + 999999)
    digests = []
    leaks = []
    step = 0
    while step < max_decisions:
        try:
            d = e.advance()
        except Exception:
            leaks.append(step)
            break
        if d is None or e.s.result:
            break
        before = e.s.digest()
        digests.append(before)
        child = e.clone()
        crashed = False
        try:
            for _ in range(branch_steps):
                cd = child.advance()
                if cd is None or child.s.result:
                    break
                child.answer(policy_answer(cd, brng))
        except Exception:
            crashed = True
        if crashed or e.s.digest() != before:
            leaks.append(step)
        try:
            e.answer(policy_answer(d, rng))
        except Exception:
            leaks.append(step)
            break
        step += 1
    r = e.s.result
    tail = f"result={r['winner']}/{r['reason']}/turn{r['turn']}" if r else "unfinished"
    return digests, tail, leaks


def diff_states(a, b):
    """2つの状態の差分を文字列の列で返す（漏れ箇所の特定用）。"""
    out = []
    for cid, (x, y) in enumerate(zip(a.cards, b.cards)):
        if x is y:
            continue
        for k, v in x.__dict__.items():
            w = y.__dict__[k]
            if v != w:
                out.append(f"card {cid} ({x.defn}) .{k}: {v!r} -> {w!r}")
    for name in a.zones:
        for p in (0, 1):
            if a.zones[name][p] != b.zones[name][p]:
                out.append(f"zone {name}[{p}]: {a.zones[name][p]} -> {b.zones[name][p]}")
    for k in ("hold", "turn", "active", "step", "rng", "seq"):
        if getattr(a, k) != getattr(b, k):
            out.append(f"state .{k}: {getattr(a, k)!r} -> {getattr(b, k)!r}")
    return out


def branch_diag(rules, deck, seed, policy_seed, max_decisions, branch_steps):
    """最初の漏れで止めて、親の状態のどこが変わったかを表示する。"""
    e = Engine.new_game(rules, [deck, deck], seed, 0)
    rng = random.Random(policy_seed)
    brng = random.Random(policy_seed + 999999)
    step = 0
    while step < max_decisions:
        d = e.advance()
        if d is None or e.s.result:
            break
        state_mod.COW = False
        snap = e.s.clone()
        state_mod.COW = True
        child = e.clone()
        crashed = False
        try:
            for _ in range(branch_steps):
                cd = child.advance()
                if cd is None or child.s.result:
                    break
                child.answer(policy_answer(cd, brng))
        except Exception as ex:
            crashed = True
            print(f"  child crashed: {type(ex).__name__}: {ex}")
        diffs = diff_states(snap, e.s)
        if crashed or diffs:
            print(f"seed {seed} step {step}: leak ({'crash' if crashed else 'state changed'})")
            for line in diffs[:20]:
                print(f"  {line}")
            return False
        e.answer(policy_answer(d, rng))
        step += 1
    print(f"seed {seed}: no leak in {step} decisions")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=12)
    ap.add_argument("--max-decisions", type=int, default=150)
    ap.add_argument("--deck", default="data/decks/saga.yaml")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--cow", action="store_true",
                    help="COW 有効時の分岐チェック（親 digest の不変性）")
    ap.add_argument("--branch-steps", type=int, default=6)
    ap.add_argument("--cow-diag", action="store_true",
                    help="COW の最初の漏れで止めて差分を表示する")
    args = ap.parse_args()

    rules = load_rules()
    deck = load_deck(args.deck)
    bad = 0
    if args.cow_diag:
        state_mod.COW = True
        for seed in range(1, args.seeds + 1):
            ok = branch_diag(rules, deck, seed, 1000 + seed,
                             args.max_decisions, args.branch_steps)
            bad += 0 if ok else 1
        state_mod.COW = False
        print(f"== cow diag: {args.seeds - bad}/{args.seeds} leak-free")
        return 1 if bad else 0
    if args.cow:
        for seed in range(1, args.seeds + 1):
            state_mod.COW = False
            a, ra = playout(rules, deck, seed, 1000 + seed, args.max_decisions)
            state_mod.COW = True
            b, rb, leaks = branch_playout(rules, deck, seed, 1000 + seed,
                                          args.max_decisions, args.branch_steps)
            state_mod.COW = False
            same = a == b and ra == rb
            ok = same and not leaks
            print(f"seed {seed}: decisions={len(a)} identical={same} "
                  f"leaks={leaks[:5]}{'...' if len(leaks) > 5 else ''} {rb}")
            bad += 0 if ok else 1
        print(f"== cow branch-check: {args.seeds - bad}/{args.seeds} OK")
        return 1 if bad else 0
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
