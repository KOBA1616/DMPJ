"""速い候補の中からループしうる組を探す（絞る順番を逆にする、2026-11-13）。

1. 2枚組の候補（discovery.candidates.candidate_pairs、順序なしにまとめ、つながりの点は両向きの大きいほう）に
   速さの上限（eval.speed_bound.static_bound）を当て、4ターン以内に入口へ届きうる組を母集団にする。点の分布を速い組・遅い組で比べる。
2. 母集団に静的なループ判定（engine.zone_graph の循環。2枚の束だけで閉路を探す）を当てる。
   閉路があり、ターン内で回り（in_turn）、受け渡しが狙って満たせ（sure）、1周のマナが閉じる（払うマナが 0 か、マナゾーンが増える）ものを残す。
   勝ち手段（相手のゾーンを動かす・自分の山札を減らさない蓄積）がない組には、3枚目（その閉路の移動が誘発を満たし、相手のゾーンを動かす札）を足して試す。
   落ちた理由を数える: no_cycle / gated（ターン内で回らない）/ blind（札が狙って戻らない）/ mana（マナが閉じない）/
   drain（1周で手札・マナ・場が減る＝札の収支が負）/ no_win（勝ち手段がない）。
   未承認カード（load_rules(only_approved=True) に無い札）が入る組には印を付ける。
使い方: python dmsim/discovery/loop_screen.py（旧 tools/fast_loop_screen.py） --out out.json [--max-turn 4]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.discovery.candidates import candidate_pairs, card_io  # noqa: E402
from dmsim.engine import zone_graph as Z  # noqa: E402
from dmsim.eval import speed_bound as S  # noqa: E402

from . import loop_cond as C  # noqa: E402


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
            if COND and C.gate(bs[j]):
                continue        # 移動では満たせない限定つきの誘発（via・unpaid・1ターンに1回）は閉路に入れない
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


def _all_ops(d):
    for f in (getattr(d, "faces", None) or [d]):
        for ab in f.abilities or []:
            for key in ("effect", "instead"):
                yield from _walk(ab.get(key) or [])
        yield from _walk(getattr(f, "spell", None) or [])


def _walk(ops):
    for op in ops or []:
        if isinstance(op, dict):
            yield op
            for k in ("body", "then", "else", "effect", "instead"):
                if isinstance(op.get(k), list):
                    yield from _walk(op[k])


def special_win(d) -> bool:
    """自分の特殊勝利（効果の中に op: win がある。置換 instead の中も見る）。"""
    return any(op.get("op") == "win" and op.get("player", "you") == "you" for op in _all_ops(d))


def free_cast(d):
    """手札の呪文・クリーチャーのコストを払わずに使わせる常在能力の対象（filter）の一覧。"""
    out = []
    for f in (getattr(d, "faces", None) or [d]):
        for ab in f.abilities or []:
            if ab.get("kind") != "static":
                continue
            mod = ab.get("mod") or {}
            aff = ab.get("affects")
            if isinstance(aff, dict) and aff.get("zone") == "hand" and aff.get("owner", "you") == "you" and \
                    set(mod.get("allow") or []) & {"cast_free", "play_free", "summon_free"}:
                out.append(aff.get("filter") or {})
    return out


def _admits(flt, d):
    t = flt.get("types")
    return not t or bool(set(t) & set(d.types))


def cycle_mana(c, rules, helpers) -> int:
    """1周で払うマナ。札の組の中の常在能力（手札の呪文を無償で唱える等）が対象にする束は 0 とみなす。"""
    n = 0
    for b in c.bundles:
        if b.origin not in ("spell", "summon"):
            continue
        d = rules.cards[b.card]
        kind = {"spell": "spell", "summon": "creature"}[b.origin]
        if any(_admits(f, d) and (not f.get("types") or kind in f["types"]) for f in helpers):
            continue
        n += b.cost
    return n


def _zone(z):
    return z if isinstance(z, str) else "/".join(map(str, z))


def side_bundles(c: Z.Cycle, bs, rules, helpers=()) -> list:
    """閉路の束が狙って誘発させる、閉路の外の誘発（マナを払わずに毎周起きる付け足しの効果。例: 無償で出したクリーチャーの出た時）。
    helpers（組の中の無償で唱えさせる常在能力）があれば、閉路が手札に戻す呪文・クリーチャーを無償で使うことも付け足しに数える
    （訪れる魔の時刻が回収した H.D.2. をアカシック3で唱える）。"""
    inside = {id(b) for b in c.bundles}
    out = []
    for b in bs:
        if id(b) in inside or not b.prem or b.prem.kind in Z.TICKS or (COND and C.gate(b)):
            continue
        if b.origin == "trigger" or (COND and helpers and b.origin in ("spell", "summon")
                                     and cycle_mana(Z.Cycle([b]), rules, helpers) == 0):
            if any(Z.feeds(a, b, rules) == 2 for a in c.bundles):
                out.append(b)
    return out


def net(bundles, owner="you", skip=frozenset()) -> dict:
    """束の移動の収支。名前を付けた札を後で動かす移動（select.ref）は、その札を置いたゾーンから動かす。
    複数枚を動かしうる移動（many）は、移動元に余りがあり移動先が足りないぶんを埋める。"""
    d, many = {}, []
    for b in bundles:
        placed = {}
        for m in b.moves:
            if id(m) in skip:
                continue
            src, dst = _zone(m.src), _zone(m.dst)
            if m.ref and m.ref in placed:
                src = placed[m.ref]
            if m.alias:
                placed[m.alias] = dst
            if (m.owner == "opp") != (owner == "opp"):
                continue
            d[src] = d.get(src, 0) - 1
            d[dst] = d.get(dst, 0) + 1
            if m.many:
                many.append((src, dst))
    for src, dst in many:
        k = min(max(0, d.get(src, 0)), max(0, -d.get(dst, 0)))
        d[src] = d.get(src, 0) - k
        d[dst] = d.get(dst, 0) + k
    return {k: v for k, v in d.items() if v}


def classify(c: Z.Cycle, rules=None, helpers=(), side=(), skip=frozenset()) -> str | None:
    """閉路が残れば None、落ちれば理由。"""
    if c.period != "in_turn":
        return "gated"
    if not c.sure:
        return "blind"
    d = net(list(c.bundles) + list(side), skip=skip)
    m = c.mana() if rules is None else cycle_mana(c, rules, helpers)
    if m > 0 and d.get("mana", 0) <= 0:
        return "mana"
    if any(d.get(z, 0) < 0 for z in ("hand", "mana", "bz", "?")):
        return "drain"          # 1周で手札・マナ・場（または読めない移動元）が減る＝札が戻らず回るたびに細る
    return None


def wins(c: Z.Cycle, strict: bool = False, self_win: bool = False, side=(), skip=frozenset()) -> bool:
    """勝ち手段。strict=False: 相手のゾーンを動かす。strict=True: 相手の山札か盾を減らす、または自分の特殊勝利の札が組にあり
    1周で自分の山札が減る（引き切って勝つ）。"""
    allb = list(c.bundles) + list(side)
    od = net(allb, "opp", skip)
    if not strict:
        return bool(od) or self_win
    if od.get("deck", 0) < 0 or od.get("shield", 0) < 0:
        return True
    return self_win and net(allb, skip=skip).get("deck", 0) < 0


COND = True     # 条件を読む（2026-11-14）。False で 2026-11-13 夜の判定（条件つきの移動は起きる前提、特殊勝利は条件を読まない）


def make_ctx(allb, bs, skip=frozenset()):
    """条件の評価に使う、ループ1周の収支と組の中の札の情報。"""
    inflow, inflow_opp, named = set(), set(), set()
    for b in bs:
        for m in b.moves:
            if id(m) in skip:
                continue
            (inflow_opp if m.owner == "opp" else inflow).add(_zone(m.dst))
    for b in allb:
        for m in b.moves:
            if id(m) not in skip and m.ref_self:
                named.add((_zone(m.dst), b.name))
    draws = any(m.draw for b in allb for m in b.moves if id(m) not in skip)
    return {"net": net(allb, skip=skip), "opp_net": net(allb, "opp", skip), "inflow": inflow, "inflow_opp": inflow_opp,
            "named_in": named, "draws": draws}


def cond_filter(c, side, bs, rules):
    """条件を満たせない移動（skip）と読めない条件の数。閉路の受け渡しが満たせない移動にしか頼っていなければ None（落とす）。"""
    allb = list(c.bundles) + list(side)
    ctx = make_ctx(allb, bs)
    skip, unk = set(), 0
    for b in bs:
        for m in b.moves:
            st = C.conds_state(getattr(m, "conds", ()), ctx)
            if st == "no":
                skip.add(id(m))
            elif st == "unknown" and any(b is x for x in allb):
                unk += 1
    bl = list(c.bundles)
    d = net(allb, skip=skip)
    for a, b in zip(bl, bl[1:] + bl[:1]):
        ok = False
        for m in a.moves:
            if id(m) in skip:
                continue
            one = Z.Bundle(a.card, a.name, a.prem, [m], a.origin, a.cost, a.rearm)
            if Z.feeds(one, b, rules):
                if not m.ref_self and not m.blind and _zone(m.src) in ("deck", "shield") and d.get(_zone(m.src), 0) < 0:
                    continue    # 山札・盾から別のコピーを狙って出し続ける受け渡し: 札が戻らないので枚数ぶんで止まる（有限）
                ok = True
                break
        if not ok:
            return None, unk
    return frozenset(skip), unk


def judge_set(cards, by_card, rules, strict=False, max_len=6):
    """札の組（2〜3枚）の静的なループ判定。(落ちた理由 or None, 残った閉路)。
    閉路は組の一部の札でもよい（同じ札の別のコピー同士の蘇生など）。ただし組のどの札も、閉路に入るか、閉路が誘発させる付け足しの効果か、
    閉路のマナを下げる常在能力か、勝ち手段（特殊勝利・相手の山札か盾を動かす）として役に立つこと。"""
    ids = [rules.cards[x].id for x in cards]
    bs = [b for x in ids for b in by_card.get(x, [])]
    helpers = {x: free_cast(rules.cards[x]) for x in ids}
    winners = {x for x in ids if special_win(rules.cards[x])}
    wpaths = {x: C.win_paths(rules.cards[x]) for x in winners}
    hl = [f for fs in helpers.values() for f in fs]
    cyc = cycles_of(bs, rules, max_len=max_len)
    if not cyc:
        return "no_cycle", None
    reasons, ok = Counter(), []
    for c in cyc:
        side = side_bundles(c, bs, rules, hl)
        skip, unk = frozenset(), 0
        sw = set(winners)
        if COND:
            skip, unk = cond_filter(c, side, bs, rules)
            if skip is None:
                reasons["cond"] += 1
                continue
            ctx = make_ctx(list(c.bundles) + list(side), bs, skip)
            sw = set()
            for x in winners:
                st = C.win_state(wpaths[x], ctx)
                if st == "yes":
                    sw.add(x)
                elif st == "unknown":
                    sw.add(x)
                    unk += 1
        r = classify(c, rules, hl, side, skip)
        if r:
            reasons[r] += 1
            continue
        used = set(c.cards) | {b.card for b in side} | \
            {x for x in ids if helpers[x] and cycle_mana(c, rules, []) > cycle_mana(c, rules, helpers[x])}
        if sw and not wins(c, strict, False, side, skip) and wins(c, strict, True, side, skip):
            used |= sw
        if used >= set(ids):
            c.side, c.skip, c.unknown, c.self_win = side, skip, unk, bool(sw)
            ok.append(c)
        else:
            reasons["unused"] += 1
    if not ok:
        order = ["unused", "drain", "mana", "cond", "blind", "gated"]   # 最も「惜しい」理由を代表にする
        return next(r for r in order if reasons[r]), None
    w = [c for c in ok if wins(c, strict, c.self_win, c.side, c.skip)]
    w.sort(key=lambda c: c.unknown)
    if not w:
        return "no_win", ok
    return None, w


def judge_pair(cards, by_card, rules, strict=False):
    return judge_set(cards, by_card, rules, strict=strict, max_len=4)


def describe(c: Z.Cycle, rules):
    side = getattr(c, "side", [])
    return {"cards": c.cards, "names": [rules.cards[x].name for x in c.cards], "delta": net(list(c.bundles) + side),
            "opp": net(list(c.bundles) + side, "opp"), "side": [f"{b.name}:{b.premise}" for b in side], "mana": c.mana(), "conditional": c.conditional(), "unknown": getattr(c, "unknown", 0), "steps": [f"{b.name}:{b.origin}:{b.premise}" for b in c.bundles]}


def win_card(rules, by_card, x, strict):
    """勝ち手段になりうる札。strict: 相手の山札か盾を動かす束がある、または自分の特殊勝利。"""
    if special_win(rules.cards[x]):
        return True
    for b in by_card.get(rules.cards[x].id, []):
        for m in b.moves:
            if m.owner == "opp" and (not strict or _zone(m.src) in ("deck", "shield")):
                return True
    return False


def third_cards(ok_cycles, by_card, rules, pool, limit=200):
    """2枚の閉路の移動が誘発を満たし、相手のゾーンを動かす札、または自分の特殊勝利の札（3枚目の候補）。"""
    out = []
    for x in pool:
        bs = by_card.get(rules.cards[x].id, [])
        hit = special_win(rules.cards[x]) and any(net(c.bundles).get("deck", 0) < 0 for c in ok_cycles)
        for b in ([] if hit else bs):
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


KNOWN = ("saga", "akashic", "akashic_hd2")    # 登録済みのループ型（holdout のドリルは使わない）


def known_check(rules, by_card, strict):
    """ふるいの見逃しの確認: 速さの条件を外し、既知コンボの中核（loop_entry.core_ids）とその部分組を同じ判定にかける。
    3枚以上の中核は、2枚の部分組から「3枚目を足す」広げ方で中核の残りの札に届くかも見る。"""
    from itertools import combinations
    from dmsim.eval import loop_entry as le
    winners = [x for x in rules.cards if not x.startswith("T") and win_card(rules, by_card, x, strict)]
    out = {}
    for n in KNOWN:
        core = le.core_ids(le.load(n))
        rows = []
        for k in range(2, min(3, len(core)) + 1):
            for sub in combinations(core, k):
                r, cyc = judge_set(list(sub), by_card, rules, strict=strict)
                row = {"cards": list(sub), "names": [rules.cards[x].name for x in sub], "result": r or "pass"}
                if k == 2 and r == "no_win":
                    pool = [x for x in core if x not in sub and x in winners]
                    reach = [x for x in third_cards(cyc, by_card, rules, pool, limit=10)
                             if not judge_set(list(sub) + [x], by_card, rules, strict=strict)[0]]
                    row["third_reaches"] = reach
                rows.append(row)
        out[n] = {"core": core, "any_pass": any(r["result"] == "pass" for r in rows),
                  "reach_by_extension": any(r.get("third_reaches") for r in rows) or any(r["result"] == "pass" and len(r["cards"]) == 2 for r in rows),
                  "rows": rows}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-turn", type=int, default=4)
    ap.add_argument("--out", required=True)
    ap.add_argument("--strict", action="store_true", help="勝ち手段を「相手の山札か盾を減らす、または自分の特殊勝利」に絞る")
    ap.add_argument("--three-pairs", type=int, default=200)
    ap.add_argument("--three-per", type=int, default=20)
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
    for b in (C.bundles(rules) if COND else Z.bundles_of(rules)):
        by_card[b.card].append(b)
    known = known_check(rules, by_card, a.strict)
    for n, k in known.items():
        print(f"既知 {n}: 通る部分組あり={k['any_pass']} 2枚組から届く={k['reach_by_extension']}", flush=True)
    drop = Counter()
    drop_unapproved = Counter()
    passed, nowin = [], []
    for i, p in enumerate(fast):
        r, cyc = judge_pair([p["a"], p["b"]], by_card, rules, strict=a.strict)
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
    # 3枚目: 勝ち手段なしで閉じた組にだけ、勝ち手段の札を1枚足す（上位 --three-pairs 組 × 3枚目の候補 上位 --three-per 枚）。
    # 足した3枚を judge_set でもう一度判定し、通ったものだけ残す。
    winners = [x for x in ids if win_card(rules, by_card, x, a.strict)]
    three, three_drop = [], Counter()
    for p, cyc, un in nowin[:a.three_pairs]:
        for x in third_cards(cyc, by_card, rules, winners, limit=a.three_per):
            if x in (p["a"], p["b"]):
                continue
            t = S.static_bound(rules, [p["a"], p["b"], x])["turn"]
            if t is None or t > a.max_turn:
                three_drop["slow"] += 1
                continue
            r3, c3 = judge_set([p["a"], p["b"], x], by_card, rules, strict=a.strict)
            if r3:
                three_drop[r3] += 1
                continue
            un3 = un + ([x] if x not in approved else [])
            three.append({"a": p["a"], "b": p["b"], "c": x, "score": p["score"], "turn": t, "unapproved": un3,
                          "cycles": [describe(c, rules) for c in c3[:2]]})
    print(f"3枚組（4T以内・判定通過） {len(three)} 落ち {dict(three_drop)} {time.time()-t0:.0f}s", flush=True)
    # 読めない条件がある組は落とさず順位を下げる（読めない条件の数が少ない順、次につながりの点の高い順）
    passed.sort(key=lambda p: (p["cycles"][0].get("unknown", 0), -p["score"]))
    three.sort(key=lambda t: (t["cycles"][0].get("unknown", 0), -t["score"]))
    out = {"pairs": len(pairs), "cards": len(ids), "skipped_cards": broken, "turn_dist": {str(k): v for k, v in sorted(tdist.items(), key=str)},
           "score": {"fast": summ(fast_scores), "slow": summ(slow_scores), "unknown": summ(unk_scores)},
           "fast": len(fast), "drop": dict(drop), "drop_unapproved": dict(drop_unapproved),
           "passed": len(passed), "nowin": len(nowin), "passed_top": passed[:300],
           "nowin_top": [{**p, "unapproved": un, "cycles": [describe(c, rules) for c in cyc[:2]]} for p, cyc, un in nowin[:100]],
           "known": known, "three": three, "three_drop": dict(three_drop), "strict": a.strict, "seconds": round(time.time() - t0)}
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("passed_top", "nowin_top", "three")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
