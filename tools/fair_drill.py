"""公平探索（相手の山札を見ない）で、ドリル＋ジョバンニの通常開幕から相手マナ破壊に届くかの測定。
葉の評価に opp_pressure を足した版と足さない版を比べる。使い方: python tools/fair_drill.py --seeds 6 --turns 12 --budget 200 --n-det 4"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.engine.view import active_of, result_of  # noqa: E402
from dmsim.eval.opp_pressure import opp_pressure  # noqa: E402
from dmsim.play_api import InfoLevel, PlayConfig, search_turn  # noqa: E402
from dmsim.search.leaf_eval import Weights, evaluate  # noqa: E402
from dmsim.search.turn import charge_only_policy, own_turn  # noqa: E402

D, J = "dm16-051", "dm36-015"


def run(rules, seed, use_term, turns, budget, n_det, copies, filler="T001", extra=()):
    deck = [D] * copies + [J] * copies + [c for c, n in extra for _ in range(n)]
    deck += [filler] * (40 - len(deck))
    eng = Engine.new_game(rules, [deck, ["T001"] * 40], seed, first_player=0)
    w = Weights()
    vf = (lambda e, me: evaluate(e, me, w) + opp_pressure(e, me)) if use_term else None
    low, dk = 0, 40
    while (d := eng.advance()) is not None:
        if active_of(eng) != 0 or d["player"] != 0:
            eng.answer(charge_only_policy(eng, d))
            continue
        if own_turn(eng, 0) > turns:
            break
        eng, _ = search_turn(eng, PlayConfig(me=0, budget=budget, n_det=n_det, seed=seed * 7919 + own_turn(eng, 0),
                                             value_fn=vf), InfoLevel.FAIR)
        low = max(low, len(eng.zlist("graveyard", 1)))  # 開幕は相手マナ0。墓地の最大枚数で測る
        dk = min(dk, len(eng.zlist("deck", 1)))
    return low, dk, result_of(eng)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--turns", type=int, default=6, help="自分のターン数")
    ap.add_argument("--budget", type=int, default=200)
    ap.add_argument("--n-det", type=int, default=4)
    ap.add_argument("--filler", default="T001", help="穴埋めカード（既定は効果なしのダミー）")
    ap.add_argument("--copies", type=int, default=4)
    ap.add_argument("--extra", default="", help="追加カード 例 T012:4（ID:枚数をカンマ区切り）。攻撃しない呪文だけで組むと殴り勝ちを除ける")
    a = ap.parse_args(argv)
    extra = tuple((x.split(":")[0], int(x.split(":")[1])) for x in a.extra.split(",") if x)
    rules = load_rules()
    for use in (False, True):
        res = []
        for s in range(1, a.seeds + 1):
            low, dk, r = run(rules, s, use, a.turns, a.budget, a.n_det, a.copies, a.filler, extra)
            res.append(low)
            print(f"  term={use} seed={s} 相手墓地最大={low} 相手山札最小={dk} 結果={r}", flush=True)
        print(f"[公平] opp_pressure={'あり' if use else 'なし'}: 相手墓地の最大枚数 {res}", flush=True)


if __name__ == "__main__":
    main()
