"""2枚組の有限ループ候補（loop_enum.finite_pairs）を、通常開幕から実際に探索して検証する。
各組を4枚ずつ＋無効呪文のデッキにし、reach_target の探索（相手資源の減少を加点）で、max_turn までに
相手のマナ・盾・山札をどれだけ減らせたか（相手の墓地の枚数＋失った盾の最大値）を記録する。結果は JSONL（再開可能）。
使い方: python tools/pair_verify.py --pairs /tmp/pairs.json --out data/loops/pair_verify.jsonl --max-turn 8 --limit 50"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.search.bestfirst import priority  # noqa: E402
from dmsim.search.reachsearch import reach_target  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.eval.opp_pressure import make_term  # noqa: E402
from dmsim.eval.vfeatures import v_priority  # noqa: E402

FILLER = "T022"


def verify(rules, pair, seed=1, width=80, max_turn=8, copies=4):
    deck = [c for c in pair for _ in range(copies)]
    deck += [FILLER] * (40 - len(deck))
    e = Engine.new_game(rules, [deck, ["T001"] * 40], seed, first_player=0)
    best = [0.0]
    term = make_term()

    def prio(en, me, w):
        # 相手の墓地の枚数（マナ破壊・山札破棄で増える）＋失った盾。受け身の相手では他で増えない
        best[0] = max(best[0], len(en.zlist("graveyard", 1)) + max(0, 5 - len(en.zlist("shield", 1))))
        return v_priority(en, me, w, priority, under_w=0, res_w=0, terms=[term])
    reach_target(e, {"graveyard": {"*": 999}}, 0, width=width, max_turn=max_turn, max_depth=300, prio=prio)
    return best[0]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-turn", type=int, default=8)
    ap.add_argument("--width", type=int, default=80)
    ap.add_argument("--limit", type=int, default=50)
    a = ap.parse_args(argv)
    rules = load_rules()
    pairs = json.loads(Path(a.pairs).read_text())
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {tuple(json.loads(l)["pair"]) for l in out.read_text().splitlines()} if out.exists() else set()
    n = 0
    for p in pairs:
        if tuple(p) in done:
            continue
        if n >= a.limit:
            break
        t = time.time()
        try:
            s = verify(rules, p, width=a.width, max_turn=a.max_turn)
            rec = {"pair": p, "names": [rules.cards[c].name for c in p], "pressure": s, "sec": round(time.time() - t, 1)}
        except Exception as ex:  # noqa: BLE001
            rec = {"pair": p, "error": f"{type(ex).__name__}: {ex}"}
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        n += 1
        print(rec, flush=True)


if __name__ == "__main__":
    main()
