"""速い候補の中からループしうる組を探す（絞る順番を逆にする、2026-11-13）。

1. 2枚組の候補（discovery.candidates.candidate_pairs、順序なしにまとめ、つながりの点は両向きの大きいほう）に
   速さの上限（eval.speed_bound.static_bound）を当て、4ターン以内に入口へ届きうる組を母集団にする。点の分布を速い組・遅い組で比べる。
2. 母集団に静的なループ判定（engine.zone_graph の循環。2枚の束だけで閉路を探す）を当てる。
   閉路があり、ターン内で回り（in_turn）、受け渡しが狙って満たせ（sure）、1周のマナが閉じる（払うマナが 0 か、マナゾーンが増える）ものを残す。
   勝ち手段（相手のゾーンを動かす・自分の山札を減らさない蓄積）がない組には、3枚目（その閉路の移動が誘発を満たし、相手のゾーンを動かす札）を足して試す。
   落ちた理由を数える: no_cycle / gated（ターン内で回らない）/ blind（札が狙って戻らない）/ mana（マナが閉じない）/
   drain（1周で手札・マナ・場が減る＝札の収支が負）/ no_win（勝ち手段がない）。
   未承認カード（load_rules(only_approved=True) に無い札）が入る組には印を付ける。
使い方: python tools/fast_loop_screen.py --out out.json [--max-turn 4]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.discovery.candidates import candidate_pairs, card_io  # noqa: E402
from dmsim.engine import zone_graph as Z  # noqa: E402
from dmsim.eval import speed_bound as S  # noqa: E402


def usable_ids(rules):
    ids, broken = [], 0
    for cid in sorted(rules.cards):
        if cid.startswith("T") or rules.cards[cid].cost is None:
            continue
        try:
            card_io(rules, cid)
            ids.append(cid)
        except Exception:
            broken += 1
    return ids, broken


def unordered(pairs):
    best = {}
    for p in pairs:
        k = tuple(sorted((p["a"], p["b"])))
        if k not in best or p["score"] > best[k]["score"]:
            best[k] = {"a": k[0], "b": k[1], "score": p["score"], "links": p["links"]}
    return list(best.values())


def cycles_of(bs, rules, max_len=4):
    """bs（2〜3枚の札の束）の中の閉路。全部の札を使うものだけ。"""
    n = len(bs)
    st = {}
    succ = {i: [] for i in range(n)}
    for i in range(n):
        for j in range(n):
            v = Z.feeds(bs[i], bs[j], rules)
            if v:
                st[i, j] = v
                succ[i].append(j)
    seen, out = set(), []

    def dfs(start, path):
        for j in succ[path[-1]]:
            if j == start:
                key = tuple(sorted(path))
                if key not in seen:
                    seen.add(key)
                    out.append(Z.Cycle([bs[k] for k in path], all(st[x, y] == 2 for x, y in zip(path, path[1:] + path[:1]))))
            elif j > start and j not in path and len(path) < max_len:
                dfs(start, path + [j])

    for s in range(n):
        dfs(s, [s])
    return out


def classify(c: Z.Cycle) -> str | None:
    """閉路が残れば None、落ちれば理由。"""
    if c.period != "in_turn":
        return "gated"
    if not c.sure:
        return "blind"
    d = c.delta()
    if c.mana() > 0 and d.get("mana", 0) <= 0:
        return "mana"
    if any(d.get(z, 0) < 0 for z in ("hand", "mana", "bz", "?")):
        return "drain"          # 1周で手札・マナ・場（または読めない移動元）が減る＝札が戻らず回るたびに細る
    return None


def wins(c: Z.Cycle) -> bool:
    """勝ち手段: 相手のゾーンを動かす（山札削り・盾割り・除去）。自分の山札を減らすだけのものは勝ちにならない。"""
    return bool(c.opp_delta())


def judge_pair(cards, by_card, rules):
    bs = [b for x in cards for b in by_card.get(x, [])]
    cyc = [c for c in cycles_of(bs, rules) if set(c.cards) == set(cards)]
    if not cyc:
        return "no_cycle", None
    reasons = Counter()
    ok = []
    for c in cyc:
        r = classify(c)
        if r:
            reasons[r] += 1
        else:
            ok.append(c)
    if not ok:
        order = ["drain", "mana", "blind", "gated"]   # 最も「惜しい」理由を代表にする
        return next(r for r in order if reasons[r]), None
    w = [c for c in ok if wins(c)]
    if not w:
        return "no_win", ok
    return None, w


def describe(c: Z.Cycle, rules):
    return {"cards": c.cards, "names": [rules.cards[x].name for x in c.cards], "delta": c.delta(), "opp": c.opp_delta(),
            "mana": c.mana(), "conditional": c.conditional(), "steps": [f"{b.name}:{b.origin}:{b.premise}" for b in c.bundles]}


def third_cards(ok_cycles, by_card, rules, pool, limit=200):
    """2枚の閉路の移動が誘発を満たし、相手のゾーンを動かす札（3枚目の候補）。"""
    out = []
    for x in pool:
        bs = by_card.get(x, [])
        hit = False
        for b in bs:
            if not any(m.owner == "opp" for m in b.moves):
                continue
            for c in ok_cycles:
                if any(Z.feeds(a, b, rules) == 2 for a in c.bundles):
                    hit = True
                    break
            if hit:
                break
        if hit:
            out.append(x)
            if len(out) >= limit:
                break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-turn", type=int, default=4)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    t0 = time.time()
    rules = load_rules()
    approved = set(load_rules(only_approved=True).cards)
    ids, broken = usable_ids(rules)
    pairs = unordered(candidate_pairs(rules, ids))
    print(f"組 {len(pairs)}（札 {len(ids)}、除外 {broken}） {time.time()-t0:.0f}s", flush=True)
    sb_cache = {}

    def bound(x, y):
        k = (x, y)
        if k not in sb_cache:
            sb_cache[k] = S.static_bound(rules, [x, y])["turn"]
        return sb_cache[k]

    fast, slow_scores, fast_scores, unk_scores, tdist = [], [], [], [], Counter()
    for p in pairs:
        t = bound(p["a"], p["b"])
        tdist["unknown" if t is None else (t if t <= 6 else ">6")] += 1
        if t is None:
            unk_scores.append(p["score"])
        elif t <= a.max_turn:
            fast_scores.append(p["score"])
            fast.append({**p, "turn": t})
        else:
            slow_scores.append(p["score"])
    print(f"速い組 {len(fast)} {time.time()-t0:.0f}s", flush=True)

    def summ(xs):
        if not xs:
            return {}
        q = statistics.quantiles(xs, n=20)
        return {"n": len(xs), "mean": round(statistics.mean(xs), 2), "p50": round(statistics.median(xs), 2),
                "p90": round(q[17], 2), "p99": round(statistics.quantiles(xs, n=100)[98], 2), "max": max(xs)}

    fast.sort(key=lambda p: (-p["score"], p["a"], p["b"]))
    by_card = defaultdict(list)
    for b in Z.bundles_of(rules):
        by_card[b.card].append(b)
    drop = Counter()
    drop_unapproved = Counter()
    passed, nowin = [], []
    for i, p in enumerate(fast):
        r, cyc = judge_pair([p["a"], p["b"]], by_card, rules)
        un = [x for x in (p["a"], p["b"]) if x not in approved]
        if r == "no_win":
            nowin.append((p, cyc, un))
        if r:
            drop[r] += 1
            if un:
                drop_unapproved[r] += 1
            continue
        passed.append({**p, "rank": i + 1, "unapproved": un, "cycles": [describe(c, rules) for c in cyc[:3]], "three": None})
        if i % 50000 == 0:
            print(f"  {i} {time.time()-t0:.0f}s", flush=True)
    print(f"2枚で閉じて勝ち手段あり {len(passed)}、勝ち手段なし {len(nowin)} {time.time()-t0:.0f}s", flush=True)
    # 3枚目: 勝ち手段なしで閉じた組にだけ、相手のゾーンを動かす札を1枚足す（上位 200 組 × 3枚目の候補 上位 20 まで）
    winners = [x for x in ids if any(any(m.owner == "opp" for m in b.moves) for b in by_card.get(x, []))]
    three = []
    for p, cyc, un in nowin[:200]:
        for x in third_cards(cyc, by_card, rules, winners, limit=20):
            if x in (p["a"], p["b"]):
                continue
            t = S.static_bound(rules, [p["a"], p["b"], x])["turn"]
            if t is None or t > a.max_turn:
                continue
            un3 = un + ([x] if x not in approved else [])
            three.append({"a": p["a"], "b": p["b"], "c": x, "score": p["score"], "turn": t, "unapproved": un3,
                          "base_cycles": [describe(c, rules) for c in cyc[:2]]})
    print(f"3枚組（4T以内） {len(three)} {time.time()-t0:.0f}s", flush=True)
    out = {"pairs": len(pairs), "cards": len(ids), "skipped_cards": broken, "turn_dist": {str(k): v for k, v in sorted(tdist.items(), key=str)},
           "score": {"fast": summ(fast_scores), "slow": summ(slow_scores), "unknown": summ(unk_scores)},
           "fast": len(fast), "drop": dict(drop), "drop_unapproved": dict(drop_unapproved),
           "passed": len(passed), "nowin": len(nowin), "passed_top": passed[:300],
           "nowin_top": [{**p, "unapproved": un, "cycles": [describe(c, rules) for c in cyc[:2]]} for p, cyc, un in nowin[:100]],
           "three": three, "seconds": round(time.time() - t0)}
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("passed_top", "nowin_top", "three")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
