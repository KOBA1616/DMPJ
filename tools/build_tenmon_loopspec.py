"""天門(初期型)の勝ち筋をビーム探索で見つけ、手順を再生して盤面を縮約し、LoopSpec として data/loops/ に保存する。
約2分かかる。   python tools/build_tenmon_loopspec.py"""
from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dmsim import scenario  # noqa: E402
from dmsim.discovery import bestfirst, replay, shrink  # noqa: E402
from dmsim.discovery.loopspec import LoopSpec, Pred  # noqa: E402
from dmsim.engine_view import defn_of, order_zone, zone_of  # noqa: E402

ns = {"STOP": 0, "__name__": "tenmon_walk"}
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile((ROOT / "tools" / "tenmon_walk.py").read_text(), "tenmon_walk.py", "exec"), ns)
rules, spec, TS, FA, AL = ns["rules"], ns["spec"], ns["TS"], ns["FA"], ns["AL"]


def prepare(e):
    dk = zone_of(e, "deck", 0)
    order_zone(e, "deck", 0, lambda c: (defn_of(e, c) != TS, defn_of(e, c) != FA))   # 山札の上は 転生スイッチ、FA の順


def main(width: int = 2000):
    e = scenario.build(rules, spec)
    prepare(e)
    r = bestfirst.beam(e, 0, width)
    assert r.won, "勝ちが見つからない"
    steps = replay.steps_of(r.engine)
    test = replay.replay_test(rules, steps, prepare)
    sk = shrink.shrink(spec, test, order=("hand", "mana", "bz", "graveyard", "shield", "deck"))
    ls = shrink.to_loopspec(rules, "天門ループ（初期型）", sk, delta={}, source={})
    ls.kind = "reroll"      # オリーブオイルの山札シャッフルで引くカードが運に左右される（同じ手順がシードごとに通るか通らないか）
    ls.goal = [Pred(0, {"name": AL}, 1, ">=", zone="bz"), Pred(0, {"types": ["creature", "spell"]}, 10, ">=", zone="shield")]
    seeds = range(1, 201)
    wins = 0
    for sd in seeds:
        b = dict(sk.spec, seed=sd)
        wins += replay.replay_test(rules, steps, prepare)(b)
    ls.source = {"win_rate_same_line": wins / len(seeds), "seeds": [seeds[0], seeds[-1]], "board": sk.spec, "steps": [[k, list(keys), list(idx)] for k, keys, idx in steps],
                 "search": {"kind": "beam", "width": width, "nodes": r.nodes}, "deck_order": "転生スイッチ, フォース・アゲイン, …",
                 "note": "手順を再生できる盤面の下限(シード1)。山札のシャッフルが運なので、カードを外すと勝てなくなる(最小化はシード依存)。win_rate_same_line は同じ手順が通るシードの割合"}
    out = ROOT / "data" / "loops" / "tenmon_initial.json"
    out.write_text(ls.to_json() + "\n")
    print("saved", out, "removed", len(sk.removed))


if __name__ == "__main__":
    main()
