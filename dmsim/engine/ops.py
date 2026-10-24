"""効果DSLのコア語彙。新しい op はここ（または別モジュール）で @op("名前") を付けて登録する。"""
from __future__ import annotations

from .registry import op


@op("move")
def op_move(eng, t, op, env):
    cids, d = eng.select(t, op["select"], env)
    if d:
        return d
    if "as" in op:
        env.setdefault("vars", {})[op["as"]] = [eng.s.ref(c) for c in cids]
    evs = [{"ev": "move", "subject": eng.s.ref(c), "to": op["to"], "reason": op["reason"],
            "position": op.get("position", "top")} for c in cids]
    if not evs:
        return None
    if op["to"] == "bz":   # バトルゾーンへ複数枚は1枚ずつ（409.1e）
        eng._defer(t, [eng.ev_task(e, env) for e in evs])
    else:                  # それ以外は同時（400.7）
        eng._defer(t, [eng.ev_task(evs, env)])
    return None


@op("draw")
def op_draw(eng, t, op, env):
    p = eng._rel(op.get("player", "you"), env)
    n = eng.eval_expr(op.get("count", 1), env)
    eng._defer(t, [eng.ev_task({"ev": "draw", "player": p}, env) for _ in range(n)])   # 1枚ずつ（114.2）


@op("tap")
def op_tap(eng, t, op, env, kind="tap"):
    cids, d = eng.select(t, op["select"], env)
    if d:
        return d
    if cids:
        eng._defer(t, [eng.ev_task([{"ev": kind, "subject": eng.s.ref(c)} for c in cids], env)])
    return None


@op("untap")
def op_untap(eng, t, op, env):
    return op_tap(eng, t, op, env, "untap")


@op("may")
def op_may(eng, t, op, env):
    a, d = eng.ask(t, env["you"], "yes_no", [{"key": "yes"}, {"key": "no"}])
    if d:
        return d
    if a[0] == 0:
        eng._defer(t, [eng._child(op["body"], env)])
    return None


@op("if")
def op_if(eng, t, op, env):
    branch = op.get("then", []) if eng.eval_cond(op["cond"], env) else op.get("else", [])
    eng._defer(t, [eng._child(branch, env)])


@op("repeat")
def op_repeat(eng, t, op, env):
    n = eng.eval_expr(op["times"], env)
    eng._defer(t, [eng._child(op["body"], env) for _ in range(n)])


@op("break")
def op_break(eng, t, op, env):
    eng._defer(t, [{"t": "break", "victim": eng._rel(op.get("player", "opp"), env), "by": env["you"],
                     "count": eng.eval_expr(op.get("count", 1), env), "phase": 0, "in_effect": True}])


@op("modify")
def op_modify(eng, t, op, env):
    cids, d = eng.select(t, op["select"], env)
    if d:
        return d
    s = eng.s
    s.seq += 1
    s.continuous.append({"id": s.seq, "affected": [s.ref(c) for c in cids], "mod": op["mod"],
                         "duration": op.get("duration", "end_of_turn"), "controller": env["you"]})
    return None


@op("shuffle")
def op_shuffle(eng, t, op, env):
    eng._shuffle(eng._rel(op.get("player", "you"), env))


@op("win")
def op_win(eng, t, op, env):
    eng.s.result = {"winner": eng._rel(op.get("player", "you"), env), "reason": "effect", "turn": eng.s.turn}


@op("lose")
def op_lose(eng, t, op, env):
    p = eng._rel(op.get("player", "you"), env)
    eng.s.result = {"winner": 1 - p, "reason": "effect", "turn": eng.s.turn}


@op("set_var")
def op_set_var(eng, t, op, env):
    env.setdefault("vars", {})[op["name"]] = op.get("value", [])


@op("extra_turn")
def op_extra_turn(eng, t, op, env):
    """追加ターン（500.5）。現在のターンの直後に1つずつ積む。"""
    eng.s.extra_turns.insert(0, eng._rel(op.get("player", "you"), env))
