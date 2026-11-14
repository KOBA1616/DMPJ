"""物差しの「速さ」の隣の目盛り「上限ターン」（2026-11-13）。

(1) static_bound: 中核の札と入口の条件から、通常の開幕（マナは1ターンに1枚、加速なし）で最速何ターン目に入口へ届きうるかを
    効果データだけで見積もる。カード名は見ない。発見の層が候補すべてに安く当てて、遅い中核を探索の前に落とすための足切り。
    - 場（bz）に要る札は、自分で出す（最安のコスト）か、中核の別の札の効果（play_free / move to bz）で出す。
    - 最安のコスト: 両面の最小、代替コスト alt_cost.cost、マナ爆誕。条件や盤面しだいで決まる軽減（進化元の数・タップ・
      フシギバース・G・ゼロ・ムゲンクライム・リサイクル・ビビッドロー・数値でない代替コスト・コストを変える常在能力）は読み取らず「不明」。
    - 入口が無い候補は、中核の札をすべて出す（呪文は唱える）ことを入口とみなす。手札・墓地の枚数は数えない（ドロー効果を読まないため）。
    - 戻り値の turn は「これより早くは届かない」下限（先攻、加速なし）。読み取れない経路が1つでもあれば turn は None（不明）。
(2) measured_bound: 山札が見える探索（CHEAT、play_game）で多数の並びを回し、最速の勝ちを拾う（tools/ideal_draw.py と同じ）。
"""
from __future__ import annotations

from itertools import product


UNREAD = ("cost_reduce_per_evo", "tap_reduce", "fushigi", "free_if", "mugen_climb", "recycle", "vividraw")
PUT_FROM = ("hand", "graveyard", "deck", "mana", "shield")



def _walk_ops(ops):
    # discovery.candidates._walk_ops と同じ（S4 から S5 を import しないための写し）
    for op in ops or []:
        if not isinstance(op, dict):
            continue
        yield op
        for key in ("body", "then", "else", "win", "lose", "draw", "effect"):
            if isinstance(op.get(key), list):
                yield from _walk_ops(op[key])
        for m in op.get("modes") or []:
            yield from _walk_ops(m)

def _faces(d):
    return list(getattr(d, "faces", None) or []) or [d]


def min_cost(d) -> tuple[int | None, list[str]]:
    """(最安のコスト, 読み取れなかった理由)。理由があればコストは None。"""
    why, best = [], None
    for f in _faces(d):
        for k in UNREAD:
            if getattr(f, k, None):
                why.append(k)
        c = f.cost
        alt = getattr(f, "alt_cost", None)
        if alt:
            if isinstance(alt, dict) and isinstance(alt.get("cost"), int):
                c = min(c, alt["cost"])
            else:
                why.append("alt_cost")
        if isinstance(getattr(f, "mana_bakutan", None), int):
            c = min(c, f.mana_bakutan)
        best = c if best is None else min(best, c)
    for a in d.abilities or []:
        if a.get("kind") == "static" and any("cost" in str(k) for k in (a.get("mod") or {})):
            why.append("static_cost")
    return (None if why else best), sorted(set(why))


def _ops(d):
    for f in _faces(d):
        for a in f.abilities or []:
            yield from _walk_ops(a.get("effect") or [])
        yield from _walk_ops(getattr(f, "spell", None) or [])


def _admits(flt: dict, x) -> bool:
    if not flt:
        return True
    if "types" in flt and not set(flt["types"]) & set(x.types):
        return False
    if "not_types" in flt and set(flt["not_types"]) & set(x.types):
        return False
    if "races" in flt and not set(flt["races"]) & set(x.races):
        return False
    if "civs" in flt and not set(flt["civs"]) & set(x.civs):
        return False
    if "cost_le" in flt and not (isinstance(flt["cost_le"], int) and x.cost <= flt["cost_le"]):
        return False
    if "total_cost_le" in flt and not (isinstance(flt["total_cost_le"], int) and x.cost <= flt["total_cost_le"]):
        return False     # 合計コストの上限（1枚ならその札のコストの上限）
    if "name" in flt and flt["name"] not in (x.name, x.id):
        return False     # 名前で指す（自分と同じ名前の札だけ、など）
    return True


def enablers(rules, ids) -> dict[str, list[str]]:
    """{X: [X を無償で出す・唱える中核の札 E]}。E の効果の play_free と、手札・墓地・山札・マナ・盾から場へ動かす move を読む。"""
    out: dict[str, list[str]] = {}
    for e in ids:
        for op in _ops(rules.cards[e]):
            sel = op.get("select") or {}
            mine = sel.get("zone") in PUT_FROM and sel.get("owner", "you") in ("you", "self")   # ref（自分自身など）は数えない
            ok = mine and (op.get("op") == "play_free" or (op.get("op") == "move" and op.get("to") == "bz"))
            if not ok:
                continue
            for x in ids:
                if x != e and _admits(sel.get("filter") or {}, rules.cards[x]):
                    out.setdefault(x, []).append(e)
    return out


def _feasible(costs: list[int], T: int) -> bool:
    """コストの列を、ターン t（マナ t）ごとの合計が t 以下になるよう T ターン以内に割り振れるか（小さい集合の総当たり）。"""
    costs = [c for c in costs if c > 0]
    if not costs:
        return True
    if max(costs) > T:
        return False
    for assign in product(range(1, T + 1), repeat=len(costs)):
        use = [0] * (T + 1)
        if all((use.__setitem__(t, use[t] + c) or use[t] <= t) for t, c in zip(assign, costs)):
            return True
    return False


def static_bound(rules, core: list[str], bz_need: list[str] | None = None, max_turn: int = 12) -> dict:
    """bz_need: 場に要る（呪文は唱える）札。None なら中核すべて。戻り値 {turn, costs, via, unknown}。"""
    need = list(dict.fromkeys(bz_need if bz_need is not None else core))
    en = enablers(rules, core)
    mc = {i: min_cost(rules.cards[i]) for i in set(core) | set(need)}
    unknown = {}
    plan = {}
    for x in need:
        c, why = mc[x]
        opts = []
        if c is not None:
            opts.append((c, "cast", ()))
        for e in en.get(x, []):
            ce, we = mc[e]
            if ce is not None:
                opts.append((ce, f"via {e}", (e,)))
            else:
                unknown.setdefault(x, []).append(f"{e}:{','.join(we)}")
        if not opts:
            unknown.setdefault(x, []).extend(why or ["no_route"])
            continue
        plan[x] = min(opts)
    if unknown:     # 読み取れない経路が1つでもあれば、それが速いかもしれないので下限は出さない
        return {"turn": None, "plan": {k: v[1] for k, v in plan.items()}, "unknown": unknown}
    # 経由で出す札は E を出す手と同じ。E のコストは1回だけ数える
    pay = {}
    for x, (c, how, dep) in plan.items():
        key = dep[0] if dep else x
        pay[key] = c
    costs = sorted(pay.values(), reverse=True)
    for T in range(1, max_turn + 1):
        if _feasible(costs, T):
            return {"turn": T, "plan": {k: v[1] for k, v in plan.items()}, "costs": pay, "unknown": unknown}
    return {"turn": None, "plan": {k: v[1] for k, v in plan.items()}, "costs": pay, "unknown": {"*": [f"> {max_turn}"]}}


def bz_need_of_entry(minimal: list[dict]) -> list[str]:
    """入口の述語から、場に要る札の名前（自分の bz、match.name）。"""
    return [p["match"]["name"] for p in minimal
            if p.get("owner", 0) == 0 and p.get("zone") == "bz" and "name" in p.get("match", {})]


def measured_bound(rules, deck: list[str], seeds, *, budget: int = 1000, max_turn: int = 4, opp_deck=None) -> dict:
    """山札が見える探索で seeds の並び × 先攻・後攻を回し、max_turn 以内の最速勝ち（上限ターン）と内訳を返す。"""
    from .lockcheck import lock_probe
    from ..search.game import play_game
    rows = []
    for s in seeds:
        for first in (0, 1):
            res, _ = play_game(rules, list(deck), list(opp_deck or ["T001"] * 40), s, first_player=first,
                               max_turn=max_turn, budget=budget, lock_judge=lock_probe)
            rows.append({"seed": s, "first": first, "kill_turn": res.kill_turn, "origin": res.origin, "kind": res.kind})
    kills = [r for r in rows if r["kill_turn"]]
    return {"games": len(rows), "best_turn": min((r["kill_turn"] for r in kills), default=None),
            "kills": len(kills), "rows": rows}
