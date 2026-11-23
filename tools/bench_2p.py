"""2人対戦ベンチマーク: 対戦を最後まで回す局/秒・決定/秒と、Rust 適用率を出す。
  python tools/bench_2p.py [--games 20] [--deck data/decks/saga.yaml] [--engine auto|python]

既定は絶望神サガ（data/decks/saga.yaml）のミラー戦、両者ランダム方策。
エンジンの土台（自己対戦学習など）のスループット計測用で、探索は使わない。
- Rust 適用率: maybe_rust で RustEngine になり、対局終了まで Python へ
  フォールバックしなかった局の割合（動的フォールバックの頻度もここで分かる）。
- Python との比較は --engine python（= DMSIM_RUST=0 相当。Rust に包まない）。
- load_rules の時間は対戦時間に含めず別に表示する（初期化コストの償却が課題のため）。
seed 固定で決定的。高速化の前後で勝敗・決定数が一致するはず。
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import yaml  # noqa: E402

from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine import rustcore  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.engine.play import random_policy, run  # noqa: E402


def load_deck(path: str) -> list[str]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("deck") or data.get("decks")
    if isinstance(data, dict):  # {decks: [[...], [...]]} 形式は先頭を使う
        data = data[0]
    return list(data)


def run_bench(rules, deck_a: list[str], deck_b: list[str], games: int,
              seed: int = 1, engine: str = "auto") -> dict:
    import random as _random

    decisions = 0
    turns = 0
    wins = {0: 0, 1: 0}
    first_wins = 0
    rust_kept = 0
    rust_wrapped = 0
    errors: list[str] = []
    done = 0

    t0 = time.perf_counter()
    for g in range(games):
        first = g % 2
        rng = _random.Random(seed * 100003 + g)
        base_pol = random_policy(rng)

        def pol(eng, d, _p=base_pol):
            nonlocal decisions
            decisions += 1
            return _p(eng, d)

        eng = Engine.new_game(rules, [deck_a, deck_b], seed + g, first)
        if engine == "auto":
            eng = rustcore.maybe_rust(eng)
            if isinstance(eng, rustcore.RustEngine):
                rust_wrapped += 1
        try:
            result = run(eng, [pol, pol])
        except Exception as e:  # step 上限・決定上限などは局として数えず記録する
            errors.append(f"game {g}: {type(e).__name__}: {e}")
            continue
        done += 1
        if isinstance(eng, rustcore.RustEngine) and eng._fb is None:
            rust_kept += 1
        if result is not None:
            w = result.get("winner")
            if w in wins:
                wins[w] += 1
                if w == first:
                    first_wins += 1
            turns += result.get("turn", 0)
    dt = time.perf_counter() - t0

    return {
        "games_done": done,
        "games_requested": games,
        "seconds": dt,
        "games_per_sec": done / dt if dt > 0 else 0.0,
        "decisions": decisions,
        "decisions_per_sec": decisions / dt if dt > 0 else 0.0,
        "decisions_per_game": decisions / done if done else 0.0,
        "avg_turns": turns / done if done else 0.0,
        "wins": wins,
        "first_player_win_rate": first_wins / done if done else 0.0,
        "rust_wrapped": rust_wrapped,
        "rust_kept_rate": rust_kept / rust_wrapped if rust_wrapped else None,
        "errors": errors,
    }


def run_bench_batch(rules, deck_a: list[str], deck_b: list[str], games: int,
                    seed: int = 1) -> dict:
    """Phase 3: Rust 内部の一括実行（dmcore.run_batch、組み込みランダム方策）。
    方策の乱数は Rust 側 RNG のため、勝敗の内訳は駆動方式（auto/python）と一致しない。"""
    from dmsim.engine import rustcore

    states = [rustcore.new_game(rules, [deck_a, deck_b], seed + g, g % 2)
              for g in range(games)]
    t0 = time.perf_counter()
    results = rustcore.run_batch(rules, states, policy="random", seed=seed)
    dt = time.perf_counter() - t0

    wins = {0: 0, 1: 0}
    first_wins = 0
    decisions = 0
    turns = 0
    errors: list[str] = []
    done = 0
    for g, r in enumerate(results):
        if "error" in r:
            errors.append(f"game {g}: {r['error']}")
            continue
        done += 1
        decisions += r["decisions"]
        turns += r["turn"] or 0
        w = r["winner"]
        if w in wins:
            wins[w] += 1
            if w == g % 2:
                first_wins += 1
    return {
        "games_done": done,
        "games_requested": games,
        "seconds": dt,
        "games_per_sec": done / dt if dt > 0 else 0.0,
        "decisions": decisions,
        "decisions_per_sec": decisions / dt if dt > 0 else 0.0,
        "decisions_per_game": decisions / done if done else 0.0,
        "avg_turns": turns / done if done else 0.0,
        "wins": wins,
        "first_player_win_rate": first_wins / done if done else 0.0,
        "rust_wrapped": done,
        "rust_kept_rate": 1.0 if done else None,
        "errors": errors,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="2人対戦ベンチ（既定: サガミラー、両者ランダム）")
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--deck", default="data/decks/saga.yaml", help="両者が使うデッキ（ミラー）")
    ap.add_argument("--deck-b", default=None, help="相手側だけ別デッキにする場合")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--engine", choices=["auto", "python", "batch"], default="auto",
                    help="auto: Rust が扱える局は Rust で進める / python: Rust に包まない / "
                         "batch: Rust 内部で一括実行（組み込みランダム方策）")
    a = ap.parse_args(argv)

    t = time.perf_counter()
    rules = load_rules()
    load_sec = time.perf_counter() - t

    deck_a = load_deck(a.deck)
    deck_b = load_deck(a.deck_b) if a.deck_b else deck_a
    if a.engine == "batch":
        r = run_bench_batch(rules, deck_a, deck_b, a.games, seed=a.seed)
    else:
        r = run_bench(rules, deck_a, deck_b, a.games, seed=a.seed, engine=a.engine)

    print(f"rules loaded in {load_sec:.2f}s (not counted below)")
    print(f"engine={a.engine} decks={len(deck_a)}v{len(deck_b)} "
          f"games={r['games_done']}/{r['games_requested']} in {r['seconds']:.2f}s")
    print(f"  {r['games_per_sec']:.2f} games/s, {r['decisions_per_sec']:.0f} decisions/s, "
          f"{r['decisions_per_game']:.0f} decisions/game, avg {r['avg_turns']:.1f} turns")
    print(f"  wins P0={r['wins'][0]} P1={r['wins'][1]}, "
          f"first player win rate={r['first_player_win_rate']:.2f}")
    if a.engine in ("auto", "batch"):
        print(f"  rust: wrapped {r['rust_wrapped']} games, kept to the end "
              f"{(r['rust_kept_rate'] or 0) * 100:.0f}%")
    for e in r["errors"]:
        print(f"  ERROR {e}")
    return r


if __name__ == "__main__":
    main()
