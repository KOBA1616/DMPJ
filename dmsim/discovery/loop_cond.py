"""静的なループ判定の「条件」を読む部分（tools/fast_loop_screen.py が使う、2026-11-14）。

engine.zone_graph の束（Bundle）は日次の経路も使うので変えない。ここでは同じ形の束を作り直し、移動に条件を付ける。
- 移動の条件 Move.conds: その移動を囲む if の cond の並び（may・modal の選択はいつでも選べるので条件にしない）。
- modal（モードを選ぶ呪文）の各モードの移動も拾う（zone_graph は拾わない。H.D.2. の「相手の山札の上2枚をマナへ」）。
- play_free で自分自身（ref: self / self_moved）を唱える・出す移動は、誘発の後に札がいるゾーン（premise の to）から動かす。
  呪文の面を唱えるなら、その面の呪文の移動も同じ束に足す（H.D.2. のラスト・バースト）。
- 特殊勝利 win_paths: 勝つ効果（op: win）と、そこに至る条件（能力の if・置換の if・囲む if）と前提（誘発・置換の when）。

条件の評価 cond_state(cond, ctx) は "yes"（組の中で満たせる）/ "no"（満たせない）/ "unknown"（読めない）。ctx はループ1周の収支など。
"""
from __future__ import annotations

from dmsim.engine import zone_graph as Z

CHILD = ("then", "else", "body")


def _walk(ops, conds=(), delayed=False):
    for op in ops or []:
        if not isinstance(op, dict):
            continue
        o = op.get("op")
        if o in ("move", "draw", "play_free", "swap"):
            yield op, conds, delayed
        if o == "if":
            c = conds + (op.get("cond"),)
            yield from _walk(op.get("then"), c, delayed)
            yield from _walk(op.get("else"), conds + ({"not": op.get("cond")},), delayed)
            continue
        if o == "modal":
            for m in op.get("modes") or []:
                yield from _walk(m, conds, delayed)
            continue
        for k in CHILD:
            if isinstance(op.get(k), list):
                yield from _walk(op[k], conds, delayed)
        if o == "delayed_trigger":
            yield from _walk(op.get("effect", []), conds, True)


def _many(sel):
    c = sel.get("count", 1)
    return c in ("any", "all") or (isinstance(c, int) and c > 1)


def moves(ops, zone="bz", after=None, card=None) -> list[Z.Move]:
    """zone: 能力が働くゾーン。after: 誘発の後に自分がいるゾーン（ref: self_moved）。card: 自分の札の定義（呪文の面を唱える時）。"""
    out = []
    for op, conds, dl in _walk(ops):
        o = op["op"]
        if o == "draw":
            m = Z.Move("deck", "hand", conditional=bool(conds), draw=True, delayed=dl, blind=True, owner=op.get("player", "you"))
        elif o == "move":
            sel = op["select"]
            ref = sel.get("ref")
            ref_self = ref in ("self", "self_moved")
            src = (after or zone) if ref == "self_moved" else zone if ref_self else sel.get("zone", "?")
            m = Z.Move(src, op["to"], ref_self, dict(sel.get("filter", {})), bool(conds), sel.get("owner", "you"),
                       delayed=dl, blind=src == "deck" and "from_top" in sel, many=_many(sel), alias=op.get("as"),
                       ref=None if ref_self else ref)
        elif o == "play_free":
            sel = op["select"]
            ref = sel.get("ref")
            ref_self = ref in ("self", "self_moved")
            src = (after or zone) if ref_self else sel.get("zone", "hand")
            face = op.get("face")
            spell = None
            if ref_self and card is not None and face == "spell":
                for f in (card.faces or [card]):
                    if f.spell:
                        spell = f
            dst = (spell.resolve_to if spell else None) or op.get("resolve_to", "bz")
            m = Z.Move(src, dst, ref_self, dict(sel.get("filter", {})), bool(conds), sel.get("owner", "you"),
                       delayed=dl, many=_many(sel), alias=op.get("as"))
            m.conds = conds
            out.append(m)
            if spell is not None:
                for x in moves(spell.spell, dst, card=card):
                    x.conds = tuple(conds) + tuple(getattr(x, "conds", ()))
                    x.conditional = x.conditional or bool(conds)
                    out.append(x)
            continue
        else:   # swap
            for m in (Z.Move("bz", "hand", False, {}, bool(conds), delayed=dl), Z.Move("hand", "bz", True, {}, bool(conds), delayed=dl)):
                m.conds = conds
                out.append(m)
            continue
        m.conds = conds
        out.append(m)
    return out


def bundles(rules) -> list[Z.Bundle]:
    """zone_graph.bundles_of と同じ束を、条件つきの移動で作る（日次の経路は使わない）。"""
    out = []
    for cd in rules.cards.values():
        faces = cd.faces or [cd]
        for f in faces:
            if f.free_if and f.is_creature():
                out.append(Z.Bundle(cd.id, cd.name, Z.Premise("move", "hand", subject="self", zone="hand"),
                                    [Z.Move("hand", "bz", True)], origin="free"))
            for ab in f.abilities:
                if ab.get("kind") not in ("trigger", "declare"):
                    continue
                pr = Z._premise(ab)
                ms = moves(ab.get("effect", []), ab.get("zone", "bz"), after=(pr.to if pr else None), card=cd)
                top = ab.get("if")
                if top is not None:
                    for m in ms:
                        m.conds = (top,) + tuple(m.conds)
                        m.conditional = True
                if pr and (ms or Z._rearms(ab.get("effect", []))):
                    b = Z.Bundle(cd.id, cd.name, pr, ms, rearm=Z._rearms(ab.get("effect", [])))
                    b.when = ab.get("when") or {}
                    b.once = bool(ab.get("once_per_turn"))
                    out.append(b)
            if f.spell:
                ms = ([Z.Move("hand", f.resolve_to, True)] + moves(f.spell, card=cd)
                      + moves(f.after_resolve, f.resolve_to, card=cd))
                for m in ms:
                    if not hasattr(m, "conds"):
                        m.conds = ()
                out.append(Z.Bundle(cd.id, cd.name, Z.Premise("move", "hand", subject="self", zone="hand"), ms,
                                    origin="spell", cost=f.cost))
        if "creature" in cd.types:
            out.append(Z.Bundle(cd.id, cd.name, Z.Premise("move", "hand", subject="self", zone="hand"),
                                [Z.Move("hand", "bz", True)], origin="summon", cost=cd.cost))
    for b in out:
        if not hasattr(b, "when"):
            b.when, b.once = {}, False
        for m in b.moves:
            if not hasattr(m, "conds"):
                m.conds = ()
    return out


def gate(b) -> str | None:
    """誘発の前提のうち、カードの移動だけでは満たせない限定。via（特定の方法で出た時: D・D・D 等）・unpaid（コストを払わずに出た時）は
    閉路の移動がその方法かを読めないので受け渡しに数えない。once_per_turn は1ターンに1回なので回らない。"""
    w = getattr(b, "when", {}) or {}
    if w.get("via") or w.get("unpaid"):
        return "via"
    if getattr(b, "once", False):
        return "once"
    return None


# ---- 条件の評価 ----

def _count_ok(spec, op, n, ctx):
    """count {zone, owner, filter} op n を、ループの収支と組の中の札で満たせるか。"""
    if not isinstance(spec, dict) or not isinstance(n, int):
        return "unknown"
    owner = spec.get("owner", "you")
    zone = spec.get("zone")
    if not isinstance(zone, str):
        return "unknown"
    flt = spec.get("filter") or {}
    net = ctx["opp_net" if owner == "opp" else "net"]
    inflow = ctx["inflow_opp" if owner == "opp" else "inflow"]
    if "name" in flt:   # 名前で数える条件: 組の中のその札が、ループでそのゾーンへ増えていく時だけ
        name = flt["name"]
        grows = any(z == zone and nm == name for z, nm in ctx["named_in"])
        if op in (">=", ">"):
            return "yes" if grows else "no"
        return "unknown"
    d = net.get(zone, 0)
    if op in (">=", ">"):
        if n <= 1 and zone in inflow:
            return "yes"
        return "yes" if d > 0 or (zone in inflow and n <= ctx.get("seed_cap", 3)) else "no"
    if op in ("<=", "<", "=="):
        if n == 0 and zone in ("deck",) and d < 0:
            return "yes"
        return "yes" if d < 0 else ("unknown" if d == 0 else "no")
    return "unknown"


def cond_state(c, ctx) -> str:
    if c is None:
        return "yes"
    if not isinstance(c, dict):
        return "unknown"
    if "all" in c:
        s = [cond_state(x, ctx) for x in c["all"]]
        return "no" if "no" in s else "unknown" if "unknown" in s else "yes"
    if "any" in c:
        s = [cond_state(x, ctx) for x in c["any"]]
        return "yes" if "yes" in s else "unknown" if "unknown" in s else "no"
    if "not" in c:
        s = cond_state(c["not"], ctx)
        return "unknown" if s == "unknown" else "yes"    # 否定は満たせる向きに倒す（その時点の盤面しだい）
    if "exists" in c:
        return "yes"
    if "is_turn" in c:
        return "yes" if c["is_turn"] in ("you", True) else "no"
    if "cmp" in c:
        a, op, b = c["cmp"]
        if isinstance(a, dict) and "count" in a:
            return _count_ok(a["count"], op, b, ctx)
        return "unknown"
    return "unknown"


def conds_state(conds, ctx) -> str:
    s = [cond_state(c, ctx) for c in conds]
    return "no" if "no" in s else "unknown" if "unknown" in s else "yes"


def _all_ops_with_conds(ops, conds=()):
    for op in ops or []:
        if not isinstance(op, dict):
            continue
        yield op, conds
        if op.get("op") == "if":
            yield from _all_ops_with_conds(op.get("then"), conds + (op.get("cond"),))
            yield from _all_ops_with_conds(op.get("else"), conds + ({"not": op.get("cond")},))
            continue
        for k in ("body", "then", "else", "effect", "instead"):
            if isinstance(op.get(k), list):
                yield from _all_ops_with_conds(op[k], conds)
        for m in op.get("modes") or []:
            yield from _all_ops_with_conds(m, conds)


def win_paths(d) -> list[dict]:
    """自分の特殊勝利: [{conds, when}]。when は誘発・置換の前提（{event, ...}）。"""
    out = []
    for f in (getattr(d, "faces", None) or [d]):
        for ab in f.abilities or []:
            top = tuple(x for x in (ab.get("if"),) if x is not None)
            for key in ("effect", "instead"):
                for op, conds in _all_ops_with_conds(ab.get(key) or []):
                    if op.get("op") == "win" and op.get("player", "you") == "you":
                        out.append({"conds": top + conds, "when": ab.get("when") or {}, "kind": ab.get("kind")})
        for op, conds in _all_ops_with_conds(getattr(f, "spell", None) or []):
            if op.get("op") == "win" and op.get("player", "you") == "you":
                out.append({"conds": conds, "when": {"event": "cast"}, "kind": "spell"})
    return out


def win_state(paths, ctx) -> str:
    """特殊勝利の札が、ループの蓄積で勝利条件に近づくか。yes / no / unknown。"""
    best = "no"
    for p in paths:
        w = p["when"] or {}
        ev = w.get("event")
        if ev == "draw" and not ctx["draws"]:
            continue                     # 引いた時の置換: ループが引かないなら起きない
        s = conds_state(p["conds"], ctx)
        if not p["conds"] and ev not in ("draw", "cast"):
            s = "unknown"                # 条件のない勝ち（出た時に勝つ等）は、ループで近づくとは言えない
        if s == "yes":
            return "yes"
        if s == "unknown":
            best = "unknown"
    return best
