"""大量試行と集計（S4、P0-3 で solitaire.py から分割）。seeds × 先攻/後攻 の1人回しを回してキル率を集計する。

  python -m dmsim.eval.measure --deck deck.yaml --games 1000 --turns 4 --workers 4
  （従来の python -m dmsim.solitaire ... も同じ）
"""
from __future__ import annotations

import math
import time
from collections import Counter
from dataclasses import asdict

from ..search.game import GameResult, play_game
from . import lockcheck  # noqa: F401  （import 時に play_game の既定のロック判定役 lock_probe を登録する）


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def summarize(results: list[GameResult], max_turn: int) -> dict:
    n = len(results)
    by_turn = {}
    for t in range(1, max_turn + 1):
        k = sum(1 for r in results if r.kill_turn is not None and r.kill_turn <= t)
        lo, hi = wilson(k, n)
        by_turn[t] = {"kills": k, "rate": k / n if n else 0.0, "ci95": [lo, hi]}
    counted = [r for r in results if r.kill_turn is not None and r.kill_turn <= max_turn]
    return {
        "games": n,
        "kill_rate_by_turn": by_turn,
        "kinds": dict(Counter(r.kind for r in counted)),
        "origins": dict(Counter(r.origin for r in counted)),
        "loop_kill_rate_by_turn": {t: sum(1 for r in results if r.origin in ("loop", "lock") and r.kill_turn is not None
                                          and r.kill_turn <= t) / n if n else 0.0 for t in range(1, max_turn + 1)},
        "lost": dict(Counter(r.lost for r in results if r.lost)),
        "errors": [{"seed": r.seed, "first_player": r.first_player, "error": r.error} for r in results if r.error],
        "loop_games": sum(1 for r in results if r.loops),
        "mean_seconds": sum(r.seconds for r in results) / n if n else 0.0,
        "mean_nodes": sum(r.nodes for r in results) / n if n else 0.0,
        "kill_seeds": [[r.seed, r.first_player, r.kill_turn, r.kind] for r in counted][:50],
    }


W: dict = {}      # ワーカープロセスごとの共有物（rules）


def init_worker(cards_paths):
    from ..cards.defs import load_rules
    W["rules"] = load_rules(cards_paths)


_W = W                       # 旧名（互換。同じ dict）
_init_worker = init_worker   # 旧名（互換）


def _one(args):
    deck, opp_deck, seed, fp, kw = args
    res, _ = play_game(W["rules"], deck, opp_deck, seed, first_player=fp, **kw)
    return res


def measure(deck: list[str], opp_deck: list[str], seeds, *, first: str = "both", workers: int = 1,
            rules=None, **kw) -> list[GameResult]:
    """seeds × 先攻/後攻 の全局を回す。workers>1 ならプロセスを分けて並列に回す（結果は seed 順）。"""
    fps = {"first": [0], "second": [1], "both": [0, 1]}[first]
    jobs = [(deck, opp_deck, s, fp, kw) for s in seeds for fp in fps]
    if workers <= 1:
        W["rules"] = rules if rules is not None else W.get("rules")
        if W["rules"] is None:
            init_worker(None)
        return [_one(j) for j in jobs]
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(workers, initializer=init_worker, initargs=(None,)) as ex:
        return list(ex.map(_one, jobs, chunksize=max(1, len(jobs) // (workers * 8))))


def load_deck(path: str) -> list[str]:
    """YAML: {deck: [id, ...]} か {cards: {id: 枚数}}。"""
    from pathlib import Path

    import yaml
    y = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if "deck" in y:
        return list(y["deck"])
    return [cid for cid, n in y["cards"].items() for _ in range(n)]


def main(argv=None):
    import argparse
    import json
    from pathlib import Path

    from ..cards.defs import load_rules
    from ..engine.play import default_decks, make_record
    ap = argparse.ArgumentParser(description="1人回しで N ターン目までのキル率を測る")
    ap.add_argument("--deck", help="自分のデッキ（YAML）。省略時は実カードを繰り返した40枚")
    ap.add_argument("--opp-deck", help="相手のデッキ（YAML）。省略時は T001×40")
    ap.add_argument("--games", type=int, default=100, help="seed の数（--first both なら局数はその2倍）")
    ap.add_argument("--seed", type=int, default=1, help="最初の seed")
    ap.add_argument("--first", choices=["first", "second", "both"], default="both")
    ap.add_argument("--turns", type=int, default=4, help="何ターン目までのキルを数えるか")
    ap.add_argument("--budget", type=int, default=200, help="1ターンの探索で展開する局面数（0 で貪欲方策のみ）")
    ap.add_argument("--opp", default="none", help="相手の妨害モデル: none / shields3 / blockers / strigger / full（dmsim.opponent.PRESETS）")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", help="集計と各局の結果（JSON）の保存先")
    ap.add_argument("--record", help="最初の1局の対戦記録（JSON）。python -m dmsim.play --replay で再生できる")
    a = ap.parse_args(argv)
    rules = load_rules()
    deck = load_deck(a.deck) if a.deck else default_decks(rules, "dm")[0]
    opp_deck = load_deck(a.opp_deck) if a.opp_deck else ["T001"] * 40
    from ..search.opponent import PRESETS
    kw = {"max_turn": a.turns, "budget": a.budget, "opp": PRESETS[a.opp]}
    if a.record:
        fp = 1 if a.first == "second" else 0
        res, eng = play_game(rules, deck, opp_deck, a.seed, first_player=fp, **kw)
        Path(a.record).write_text(json.dumps(make_record(eng, [deck, opp_deck], a.seed, fp,
                                                         note=json.dumps(asdict(res), ensure_ascii=False)),
                                             ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(asdict(res), ensure_ascii=False))
        return
    t0 = time.perf_counter()
    results = measure(deck, opp_deck, range(a.seed, a.seed + a.games), first=a.first, workers=a.workers,
                      rules=rules, **kw)
    summ = summarize(results, a.turns)
    summ["wall_seconds"] = time.perf_counter() - t0
    for t, v in summ["kill_rate_by_turn"].items():
        print(f"turn {t}: {v['rate']:.1%}  ({v['kills']}/{summ['games']}, 95%CI {v['ci95'][0]:.1%}-{v['ci95'][1]:.1%})")
    print(f"origins={summ['origins']} loop/lock kill rate by turn={ {t: f'{v:.1%}' for t, v in summ['loop_kill_rate_by_turn'].items()} }")
    print(f"kinds={summ['kinds']} lost={summ['lost']} errors={len(summ['errors'])} "
          f"loop_games={summ['loop_games']} wall={summ['wall_seconds']:.1f}s")
    if a.out:
        Path(a.out).write_text(json.dumps({"summary": summ, "games": [asdict(r) for r in results]},
                                          ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
