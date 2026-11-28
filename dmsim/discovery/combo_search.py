"""狙った構成の探索: 部品カードを固定し、残りの枠を候補プールから埋めて、1人回しのキル率で並べる。

  python -m dmsim.combo_search --fix dm22ex2-021:4 --fix dmrp03-s03:2 --slots 2 --copies 3 \\
      --turns 4 --games 20 --workers 4 --top 10

- 固定部品 (--fix ID:枚数) は常にデッキに入る。残りは候補プール（既定: 実カード全部。--pool で絞る）から
  --slots 種類を選び、1種類あたり --copies 枚入れ、足りない分は --filler で埋めて --deck-size 枚にする。
- 組み合わせが --max-decks を超えたら seed 付きで無作為に間引く（再現できる）。
- 1段目は少ない局数で全候補を測り、上位 --finalists だけを --finalist-games 局で測り直す（偶然の高得点を除く）。
- 山札からの引きに頼らず「配置を固定して足りない1〜2枚を探す」なら --setup（dmsim.scenario の spec を書いた YAML）と
  --fill-zone hand を使う。固定した配置に候補を足し、その局面から --turns ターン目までのキル率を測る。
  例: python -m dmsim.combo_search --setup tests/saga_setup.yaml --fill-zone hand --slots 1 --turns 1
- 順位づけはキル率（--turns ターン目まで）、同率ならキルの平均ターンの早い方。
"""
from __future__ import annotations

import itertools
import json
import random
import sys
import time
from dataclasses import dataclass

from ..eval.measure import measure, summarize


@dataclass
class Candidate:
    extra: tuple[str, ...]
    deck: list[str]
    stage: int = 0
    games: int = 0
    rate: float = 0.0
    ci95: tuple[float, float] = (0.0, 1.0)
    mean_turn: float | None = None
    origins: dict | None = None
    errors: int = 0


def build_deck(fixed: dict[str, int], extra: tuple[str, ...], copies: int, filler: str, deck_size: int) -> list[str]:
    deck = [c for c, n in fixed.items() for _ in range(n)]
    for c in extra:
        deck += [c] * copies
    if len(deck) > deck_size:
        raise ValueError(f"deck has {len(deck)} cards > {deck_size}")
    return deck + [filler] * (deck_size - len(deck))


def enumerate_extras(pool: list[str], slots: int, max_decks: int, seed: int) -> list[tuple[str, ...]]:
    combos = itertools.combinations(sorted(pool), slots)
    from math import comb
    total = comb(len(pool), slots)
    if total <= max_decks:
        return list(combos)
    rng = random.Random(seed)
    keep = set(rng.sample(range(total), max_decks))
    return [c for i, c in enumerate(combos) if i in keep]


def evaluate(cand: Candidate, opp_deck: list[str], seeds, turns: int, workers: int, rules, budget: int) -> None:
    results = measure(cand.deck, opp_deck, seeds, workers=workers, rules=rules, max_turn=turns, budget=budget,
                      lock_rounds=2)
    summ = summarize(results, turns)
    k = summ["kill_rate_by_turn"][turns]
    kills = [r.kill_turn for r in results if r.kill_turn is not None and r.kill_turn <= turns]
    cand.games = summ["games"]
    cand.rate, cand.ci95 = k["rate"], tuple(k["ci95"])
    cand.mean_turn = sum(kills) / len(kills) if kills else None
    cand.origins = summ["origins"]
    cand.errors = len(summ["errors"])


def search(rules, fixed: dict[str, int], pool: list[str], *, slots: int = 2, copies: int = 3, filler: str = "T001",
           deck_size: int = 40, turns: int = 4, games: int = 10, finalists: int = 5, finalist_games: int = 60,
           max_decks: int = 200, workers: int = 1, budget: int = 200, seed: int = 1,
           opp_deck: list[str] | None = None, progress=None) -> list[Candidate]:
    opp_deck = opp_deck or [filler] * deck_size
    pool = [c for c in pool if c not in fixed]
    cands = [Candidate(x, build_deck(fixed, x, copies, filler, deck_size))
             for x in enumerate_extras(pool, slots, max_decks, seed)]
    for i, c in enumerate(cands):
        evaluate(c, opp_deck, range(seed, seed + games), turns, workers, rules, budget)
        c.stage = 1
        if progress:
            progress(i + 1, len(cands), c)
    rank = lambda c: (-c.rate, c.mean_turn if c.mean_turn is not None else 99)  # noqa: E731
    cands.sort(key=rank)
    for c in cands[:finalists]:
        evaluate(c, opp_deck, range(seed + 1000, seed + 1000 + finalist_games), turns, workers, rules, budget)
        c.stage = 2
    top = sorted(cands[:finalists], key=rank)
    return top + cands[finalists:]


def _setup_job(args):
    from ..engine import scenario
    from ..eval.measure import W as _W
    from ..eval.lockcheck import lock_probe
    from ..play_api import play_cheat as play_game
    spec, seed, turns, budget = args
    eng = scenario.build(_W["rules"], dict(spec, seed=seed))
    return play_game(_W["rules"], None, None, seed, max_turn=turns, budget=budget, start=eng, lock_rounds=2,
                     lock_judge=lock_probe)[0]


def search_setup(rules, spec: dict, zone: str, pool: list[str], *, slots: int = 1, turns: int = 1, games: int = 4,
                 max_decks: int = 200, workers: int = 1, budget: int = 200, seed: int = 1,
                 progress=None) -> list[Candidate]:
    """配置 spec を固定し、zone（手札など）に pool から slots 枚（種類）足した局面を、それぞれ games 局ずつ測る。"""
    from ..eval.measure import W as _W
    from ..eval.measure import init_worker as _init_worker
    _W["rules"] = rules
    cands = []
    for x in enumerate_extras(pool, slots, max_decks, seed):
        sp = {**spec, "p0": {**spec.get("p0", {}), zone: list(spec.get("p0", {}).get(zone, [])) + list(x)}}
        cands.append((Candidate(x, []), sp))
    jobs = [(sp, sd, turns, budget) for _, sp in cands for sd in range(seed, seed + games)]
    if workers <= 1:
        out = [_setup_job(j) for j in jobs]
    else:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(workers, initializer=_init_worker, initargs=(None,)) as ex:
            out = list(ex.map(_setup_job, jobs, chunksize=max(1, len(jobs) // (workers * 8))))
    for i, (c, _) in enumerate(cands):
        results = out[i * games:(i + 1) * games]
        summ = summarize(results, turns)
        k = summ["kill_rate_by_turn"][turns]
        kills = [r.kill_turn for r in results if r.kill_turn is not None and r.kill_turn <= turns]
        c.stage, c.games, c.rate, c.ci95 = 2, summ["games"], k["rate"], tuple(k["ci95"])
        c.mean_turn = sum(kills) / len(kills) if kills else None
        c.origins, c.errors = summ["origins"], len(summ["errors"])
        if progress:
            progress(i + 1, len(cands), c)
    return sorted((c for c, _ in cands), key=lambda c: (-c.rate, c.mean_turn if c.mean_turn is not None else 99))


def package_search(rules, pool: list[str], *, copies_fixed: int = 4, max_cards: int = 2, max_packages: int = 5,
                   **kw) -> list[tuple[list[str], list[Candidate]]]:
    """ゾーン変換グラフが出したループ候補（部品の組）を固定し、残りの枠を探索する。kw は search に渡す。"""
    from ..engine.zone_graph import find_cycles
    out = []
    for cy in find_cycles(rules, max_cards=max_cards)[:max_packages]:
        fixed = {c: copies_fixed for c in cy.cards}
        out.append((cy.cards, search(rules, fixed, pool, **kw)))
    return out


def main(argv=None):
    import argparse
    from pathlib import Path

    from ..cards.defs import load_rules
    ap = argparse.ArgumentParser(description="部品を固定して残りのカードを探索する")
    ap.add_argument("--fix", action="append", default=[], metavar="ID:枚数", help="固定する部品（複数可）")
    ap.add_argument("--pool", help="候補プール（カードIDをカンマ区切り）。省略時は実カード全部")
    ap.add_argument("--from-cycles", type=int, default=0, metavar="N",
                    help="ゾーン変換グラフのループ候補の上位 N 組を固定部品にして、それぞれ残りを探索する（--fix は使わない）")
    ap.add_argument("--setup", help="配置を固定する spec（YAML。dmsim.scenario の形）。指定すると山札探索ではなく配置探索になる")
    ap.add_argument("--fill-zone", default="hand", help="--setup で候補を足すゾーン")
    ap.add_argument("--slots", type=int, default=2, help="候補から選ぶカードの種類数")
    ap.add_argument("--copies", type=int, default=3, help="選んだ1種類あたりの枚数")
    ap.add_argument("--filler", default="T001")
    ap.add_argument("--deck-size", type=int, default=40)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--games", type=int, default=10, help="1段目の seed 数（先攻・後攻で2倍の局数）")
    ap.add_argument("--finalists", type=int, default=5)
    ap.add_argument("--finalist-games", type=int, default=60)
    ap.add_argument("--max-decks", type=int, default=200)
    ap.add_argument("--budget", type=int, default=200)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--out", help="結果（JSON）の保存先")
    a = ap.parse_args(argv)
    rules = load_rules()
    fixed = {}
    for f in a.fix:
        cid, n = f.rsplit(":", 1)
        if cid not in rules.cards:
            raise SystemExit(f"unknown card {cid}")
        fixed[cid] = int(n)
    pool = a.pool.split(",") if a.pool else [c.id for c in rules.cards.values() if c.source]
    t0 = time.perf_counter()
    prog = (lambda i, n, c: print(f"\r{i}/{n}", end="", flush=True, file=sys.stderr)) if sys.stderr.isatty() else None
    if a.setup:
        import yaml
        spec = yaml.safe_load(Path(a.setup).read_text(encoding="utf-8"))
        res = search_setup(rules, spec, a.fill_zone, pool, slots=a.slots, turns=a.turns, games=a.games,
                           max_decks=a.max_decks, workers=a.workers, budget=a.budget, seed=a.seed, progress=prog)
        print(file=sys.stderr)
        for c in res[:a.top]:
            names = ", ".join(rules.cards[x].name for x in c.extra)
            t = f"{c.mean_turn:.2f}" if c.mean_turn is not None else "-"
            print(f"{c.rate:5.1%} ({c.games}局, 平均T{t}) {c.origins}  +{names}")
        print(f"{len(res)}通り, {time.perf_counter() - t0:.1f}s")
        if a.out:
            Path(a.out).write_text(json.dumps([c.__dict__ | {"extra": list(c.extra)} for c in res],
                                              ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        return
    if a.from_cycles:
        for cards, res in package_search(rules, pool, max_packages=a.from_cycles, slots=a.slots, copies=a.copies,
                                         filler=a.filler, deck_size=a.deck_size, turns=a.turns, games=a.games,
                                         finalists=a.finalists, finalist_games=a.finalist_games,
                                         max_decks=a.max_decks, workers=a.workers, budget=a.budget, seed=a.seed):
            print("部品:", " + ".join(rules.cards[c].name for c in cards))
            for c in res[:a.top]:
                print(f"  {c.rate:5.1%} ({c.games}局) {', '.join(rules.cards[x].name for x in c.extra)}")
        return
    res = search(rules, fixed, pool, slots=a.slots, copies=a.copies, filler=a.filler, deck_size=a.deck_size,
                 turns=a.turns, games=a.games, finalists=a.finalists, finalist_games=a.finalist_games,
                 max_decks=a.max_decks, workers=a.workers, budget=a.budget, seed=a.seed,
                 progress=prog)
    print(file=sys.stderr)
    for c in res[:a.top]:
        names = ", ".join(f"{rules.cards[x].name}×{a.copies}" for x in c.extra)
        t = f"{c.mean_turn:.2f}" if c.mean_turn is not None else "-"
        print(f"[{'確定' if c.stage == 2 else '予備'}] {c.rate:5.1%} (95%CI {c.ci95[0]:.0%}-{c.ci95[1]:.0%}, {c.games}局) "
              f"平均T{t} {c.origins}  {names}")
    print(f"{len(res)}構成, {time.perf_counter() - t0:.1f}s")
    if a.out:
        Path(a.out).write_text(json.dumps([c.__dict__ | {"extra": list(c.extra)} for c in res],
                                          ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
