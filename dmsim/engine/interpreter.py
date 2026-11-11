"""効果DSLのインタプリタ。op は ops.py で registry に登録する。"""
from __future__ import annotations

from ..types import BindTask, EffectTask, InvadeFixTask, PutStackedTask, PutUnderTask, SummonOnFixTask, SwapFixTask, SwapInTask
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


@task("put_stacked", PutStackedTask)
def h_put_stacked(eng, t: PutStackedTask):
    """重ね出し: 選んだカードを1体ずつ順に出す（put_evolution_stacking）。
    進化クリーチャーは出る直前に進化元を選ぶ（_evo_sources / 進化V のフィルタ別選択）。
    先に出たカードも後のカードの進化元候補になる（公式QA 31610。順序が逆で元が無い
    進化クリーチャーは出さない＝§5-1 採用読み）。ev は元の effect の子として積まれる
    ため、「出た時」は全員出し終わるまで待機する（QA 31611。pilot147 の型3テストで実証済みの構造）。"""
    s = eng.s
    env = t["env"]
    you = t["player"]
    if not t["cids"]:
        eng._pop(t)
        if "bind" in t:
            eng._push({"t": "bind", "env": env, "name": t["bind"], "cids": t["all_cids"], "zone": "bz"})
        return None
    cid = t["cids"][0]
    c = s.cards[cid]
    if c.zone == "bz":
        t["cids"] = t["cids"][1:]   # 既に場に出ているもの（置換等で動いた）は飛ばす
        return None
    ev = {"ev": "move", "subject": s.ref(cid), "to": "bz", "reason": t["reason"]}
    if t["tapped"]:
        ev["tapped"] = True
    if t["face_up"]:
        ev["face_up"] = True
    if "seal" in t:
        ev["seal"] = t["seal"]
    f = eng.fdef(cid)
    if "evolution" in f.types:
        if isinstance(f.evolve_from, list):   # 進化V: フィルタごとに1体ずつ選ぶ（h_play と同型）
            chosen = t.setdefault("evo_v", [])
            if len(chosen) < len(f.evolve_from):
                ef = {k: v for k, v in f.evolve_from[len(chosen)].items() if k != "zone"}
                used = {r[0] for r in chosen}
                cands = [x for x in eng._evo_pool(cid, you) if x not in used and eng.filter_match(x, ef)]
                if not cands:
                    t["cids"] = t["cids"][1:]   # 進化元が足りない: このカードは出さない（残りは続ける）
                    t.pop("evo_v", None)
                    return None
                ans, d = eng.ask(t, you, "choose_evo_source", [eng._card_option(x) for x in cands], 1, 1)
                if d:
                    return d
                chosen.append(s.ref(cands[ans[0]]))
                return None
            ev["stack_on"] = chosen[0]
            if len(chosen) > 1:
                ev["stack_more"] = list(chosen[1:])
            ev["evolution"] = True
            t.pop("evo_v", None)
        else:
            if t.get("evo_source"):   # 重ね先を固定する（第173弾）: 適格性を照合し、不適格なら出さない
                src = t["evo_source"]
                ef = {k: v for k, v in (f.evolve_from or {}).items() if k != "zone"} or {}
                if (not s.alive(src) or s.cards[src[0]].zone != "bz"
                        or not eng.filter_match(src[0], ef)):
                    t["cids"] = t["cids"][1:]   # 固定の進化元が適格でない: このカードは出さない（残りは続ける）
                    return None
                ev["stack_on"] = src
                ev["evolution"] = True
            else:
                srcs = eng._evo_sources(cid, you)
                if not srcs:
                    t["cids"] = t["cids"][1:]   # 進化元が無い: このカードは出さない（残りは続ける）
                    return None
                ans, d = eng.ask(t, you, "choose_evo_source", [eng._card_option(x) for x in srcs], 1, 1)
                if d:
                    return d
                ev["stack_on"] = s.ref(srcs[ans[0]])
                ev["evolution"] = True
    eng._pop(t)
    rest = dict(t, cids=t["cids"][1:])
    rest.pop("answer", None)
    eng._push(eng.ev_task(ev, env), rest)
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
