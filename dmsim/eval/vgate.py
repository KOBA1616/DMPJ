"""評価関数 V の採否ゲート（docs/value-function-design.md §7）。
段階目標の鎖（data/eval/stages/<コンボ>.yaml）への到達数を、手で決めた順位づけ（base）と v_priority の重み候補で、同じ seed・同じ強制開始から比べる。
採用は「合計の到達段階数が base 以上で、かつ base を上回る」候補だけ（同点・下回りは採らない）。足切りには使わない（順位づけの補助）。"""
from __future__ import annotations

import time
from functools import partial

import yaml

from ..discovery.bestfirst import priority
from ..discovery.reachsearch import reach_chain
from ..engine.core import Engine
from ..engine_view import force_hand
from ..plan.macro import macro_prio
from .vfeatures import v_priority

GRID = ((3.0, 1.0), (6.0, 1.0), (6.0, 3.0), (10.0, 3.0),
        (0.0, 0.0, 30.0), (0.0, 0.0, 100.0), (0.0, 0.0, 300.0))     # (under_w, res_w[, plan_w])。(0, 0) は base と同じ。plan_w>0 は大局観の計画項（macro_prio）


def stage_path(combo: str, root: str = "data/eval/stages") -> str | None:
    """手書きの <combo>.yaml を優先し、無ければ自動生成の <combo>.generated.yaml（tools/gen_stages.py）。どちらも無ければ None。"""
    from pathlib import Path
    for name in (f"{combo}.yaml", f"{combo}.generated.yaml"):
        if (Path(root) / name).exists():
            return str(Path(root) / name)
    return None


def load_stages(path) -> dict:
    return yaml.safe_load(open(path, encoding="utf-8"))


def start_engine(rules, deck, opp_deck, keys, seed):
    e = Engine.new_game(rules, [deck, opp_deck], seed, first_player=0)
    return e if force_hand(e, 0, keys) else None


def chain_score(rules, deck, opp_deck, keys, stages, seeds, prio, width=150, max_depth=80, max_turn=14, deadline=None, keep_later=True) -> dict:
    """seed ごとの到達段階数。deadline(time.time()) を過ぎたら残りの seed は測らない（打ち切り）。"""
    out = []
    for sd in seeds:
        if deadline and time.time() > deadline:
            break
        e = start_engine(rules, deck, opp_deck, keys, sd)
        if e is None:   # この seed は強制開始の札が山札に無い（盾などに落ちた）。測れないので飛ばす（全 seed で同じ seed が飛ぶ）
            continue
        out.append(reach_chain(e, stages, 0, keep_later=keep_later, width=width, max_depth=max_depth, max_turn=max_turn, prio=prio)["stages"])
    return {"stages": out, "total": sum(out)}


def run_gate(rules, deck, opp_deck, keys, stages, seeds, grid=GRID, deadline=None, **kw) -> dict:
    """base と各重みを同じ seed で測る。打ち切られて seed 数が違うときは短い方に揃えて比べる。"""
    base = chain_score(rules, deck, opp_deck, keys, stages, seeds, None, deadline=deadline, **kw)
    rows = []
    for u, r, *pw in grid:
        pw = pw[0] if pw else 0.0
        prio = macro_prio(stages, pw, under_w=u, res_w=r) if pw else partial(_vp, under_w=u, res_w=r)
        rows.append({"under_w": u, "res_w": r, "plan_w": pw, **chain_score(rules, deck, opp_deck, keys, stages, seeds, prio, deadline=deadline, **kw)})
    n = min([len(base["stages"])] + [len(x["stages"]) for x in rows])
    b = sum(base["stages"][:n])
    for x in rows:
        x["total_n"] = sum(x["stages"][:n])
        x["verdict"] = "adopt" if (n and x["total_n"] > b) else ("tie" if x["total_n"] == b else "worse")
    best = max((x for x in rows if x["verdict"] == "adopt"), key=lambda x: x["total_n"], default=None)
    return {"n": n, "base_total": b, "base": base["stages"][:n], "rows": rows, "best": best}


def _vp(eng, me, w, under_w, res_w):
    return v_priority(eng, me, w, priority, under_w=under_w, res_w=res_w)
