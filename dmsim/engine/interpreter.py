"""効果DSLのインタプリタ。op は ops.py で registry に登録する。"""
from __future__ import annotations

from ..types import BindTask, EffectTask, InvadeFixTask, PutUnderTask, SummonOnFixTask, SwapFixTask, SwapInTask
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


@task("effect", EffectTask)
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


@task("bind", BindTask)
def h_bind(eng, t):
    """移動の後、移動先にあるカードの新しい参照を変数に入れる（「その〜」が移動後のカードを指せるように）。"""
    eng._pop(t)
    s = eng.s
    t["env"].setdefault("vars", {})[t["name"]] = [s.ref(c) for c in t["cids"] if s.cards[c].zone == t["zone"]]
    return None


@task("swap_in", SwapInTask)
def h_swap_in(eng, t):
    s = eng.s
    eng._pop(t)
    o, i = t["out"], t["in"]
    if s.cards[o[0]].zone == "bz" or s.cards[o[0]].gen != t["out_gen_next"] or not s.alive(i):
        return None   # 701.26b 正常に離れなかったので入れ替えない
    cid = i[0]
    eng._push(eng.ev_task({"ev": "move", "subject": i, "to": "bz", "reason": "put", "via": "revolution_change"}, t["env"]),
              {"t": "swap_fix", "cid": cid, "out": o, "tapped": t["tapped"]})
    return None


@task("swap_fix", SwapFixTask)
def h_swap_fix(eng, t):
    s = eng.s
    eng._pop(t)
    c = s.cards[t["cid"]]
    if c.zone != "bz":
        return None
    c.tapped = t["tapped"]
    new = s.ref(t["cid"])
    for t_ in s.tasks:   # 攻撃中なら攻撃クリーチャーを入れ替える（701.26a）
        if t_["t"] == "attack" and t_["attacker"] == t["out"]:
            t_["attacker"] = new
    return None


@task("invade_fix", InvadeFixTask)
def h_invade_fix(eng, t):
    """侵略: 出たクリーチャーを攻撃中のクリーチャーの上に重ねる（進化と同じ重ね処理）。"""
    s = eng.s
    eng._pop(t)
    cid, onto = t["cid"], t["onto"]
    if s.cards[cid].zone != "bz" or not s.alive(onto) or s.cards[onto[0]].zone != "bz":
        return None
    eng._stack(cid, onto[0])
    return None


@task("summon_on_fix", SummonOnFixTask)
def h_summon_on_fix(eng, t):
    """無月の門の後始末: 重ねる処理（_stack）は進化の流儀で召喚酔いを消しタップ状態を引き継ぐため、
    通常の召喚として直す（召喚酔いする。タップ状態は op の指定どおり）。"""
    s = eng.s
    eng._pop(t)
    c = s.cards[t["cid"]]
    if c.zone != "bz":
        return None
    c.tapped = t["tapped"]
    c.entered_turn = s.turn
    return None


@task("put_under", PutUnderTask)
def h_put_under(eng, t):
    s = eng.s
    eng._pop(t)
    c = s.cards[t["cid"]]
    if c.gen != t["gen"] or not s.alive(t["onto"]):
        return None
    top = t["onto"][0]
    if s.cards[top].zone == "shield":
        eng._raw_move(t["cid"], "shield", controller=s.cards[top].controller)
        eng.zlist("shield", c.owner).remove(t["cid"])     # 束の下のカードはシールドの数に数えない（113.2）
    else:
        eng._raw_move(t["cid"], "bz", controller=s.cards[top].controller)
        c.entered_turn = -1
    c.top_of = top
    c.face_up = False if s.cards[top].zone == "shield" else c.face_up
    s.cards[top].under.append(t["cid"])
    eng._sba()   # 山札の最後の1枚を重ねたら敗北（104.2b）
    return None
