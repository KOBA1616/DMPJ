"""全探索の爆発点を切り分けるための計測プローブ（使い捨て計測用）。

ケースD（saga_setup + ドラゲリオン）について、外す上限の組み合わせを変えて
展開ノード数を数える。DIAG_ABORT は計測を打ち切るためのもので、探索仕様の制限ではない。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402
from dmsim import load_rules  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
import dmsim.search.turn as turn  # noqa: E402
import dmsim.search.game as game  # noqa: E402
from dmsim.search.turn import TurnSearch  # noqa: E402
from exhaustive_proto import exhaustive_candidates, DRAG  # noqa: E402

DIAG_ABORT = 400_000


class Abort(Exception):
    pass


_orig_search = TurnSearch._search


def _counted(self, eng, det):
    if self.stats.nodes > DIAG_ABORT:
        raise Abort()
    return _orig_search(self, eng, det)


class CandOnlySearch(TurnSearch):
    """候補列挙だけ全列挙（combo_cap 解除）。stock_offsets は通常の (0, 1)。"""

    def __init__(self, me, budget=10 ** 12, weights=None, **kw):
        kw["combo_cap"] = 10 ** 9
        super().__init__(me, budget, weights, **kw)


class FullExhSearch(CandOnlySearch):
    def __init__(self, me, budget=10 ** 12, weights=None, **kw):
        super().__init__(me, budget, weights, **kw)
        self.stock_offsets = tuple(range(0, 128))


def main():
    rules = load_rules()
    setup = yaml.safe_load(Path("tests/saga_setup.yaml").read_text(encoding="utf-8"))
    hand = list(setup["p0"]["hand"])
    hand[hand.index("T001")] = DRAG
    setup["p0"]["hand"] = hand

    TurnSearch._search = _counted
    variants = [
        ("V0 baseline (budget=200, caps on)", TurnSearch, 200, False),
        ("V1 candidates exhaustive, stock (0,1)", CandOnlySearch, 10 ** 12, True),
        ("V2 V1 + all stock counts", FullExhSearch, 10 ** 12, True),
    ]
    for name, cls, budget, exh in variants:
        if exh:
            turn.candidates = exhaustive_candidates
        game.TurnSearch = cls
        eng = sc.build(rules, setup)
        t0 = time.perf_counter()
        try:
            res, _ = game.play_game(rules, None, None, 1, max_turn=1, start=eng, lock_rounds=0, budget=budget)
            print(f"[{name}] kind={res.kind} nodes={res.nodes} wall={time.perf_counter()-t0:.1f}s", flush=True)
        except Abort:
            print(f"[{name}] ABORTED >{DIAG_ABORT} nodes wall={time.perf_counter()-t0:.1f}s", flush=True)
    TurnSearch._search = _orig_search


if __name__ == "__main__":
    main()
