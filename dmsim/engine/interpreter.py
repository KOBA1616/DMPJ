"""効果DSLのインタプリタ。op は ops.py で registry に登録する。"""
from __future__ import annotations

from .registry import OPS, task


class InterpreterMixin:
    @staticmethod
    def _child(ops, env):
        return {"t": "effect", "ops": ops, "pc": 0, "env": env, "os": {}}

    def _defer(self, t, children):
        """t の次の op を children が終わった後に回す。書かれた順に解決する（605.2c）。"""
        t["pc"] += 1
        t["os"] = {}
        self._push(*children)


@task("effect")
def h_effect(eng, t):
    if t["pc"] >= len(t["ops"]) or eng.s.result is not None:
        eng._pop(t)
        return None
    op = t["ops"][t["pc"]]
    r = OPS[op["op"]](eng, t, op, t["env"])
    if isinstance(r, dict):
        return r
    if eng.s.tasks and eng.s.tasks[-1] is t:   # _defer していなければ次の op へ
        t["pc"] += 1
        t["os"] = {}
    return None
