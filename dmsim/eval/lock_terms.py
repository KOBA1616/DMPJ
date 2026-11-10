"""場にいる間続く継続効果（常在型の静的能力）を評価する項。v_priority の `terms` に渡す (eng, me) -> 加点 の関数。
docs/value-function-design.md §3・§4。足切りには使わず順位づけのみ。

分類（効果データから自動）:
- lock: 相手を縛る静的能力（affects が相手側、または自分以外を対象にした deny / cost 増）。相手の「できること」を減らす。
- buff: 自分側への付与（grant・breaks など）。 self だけに効くもの（W・ブレイカー等）は数えない。"""
from __future__ import annotations


def _targets_opponent(aff, controller_is_me: bool) -> bool:
    if aff == "self" or aff is None:
        return False
    if isinstance(aff, dict):
        return aff.get("owner") in ("opp", "opponent", "each", "all")
    return False


def classify_static(ab: dict) -> str | None:
    """静的能力 1 つを 'lock' / 'buff' / None に分ける。"""
    if ab.get("kind") != "static":
        return None
    aff, mod = ab.get("affects"), ab.get("mod") or {}
    if aff == "self":
        return None
    if _targets_opponent(aff, True) and ("deny" in mod or "cost" in mod or "grant" not in mod):
        return "lock"
    if isinstance(aff, dict) and aff.get("owner") == "you" and "grant" in mod:
        return "buff"
    return None


def static_counts(eng, me: int) -> dict:
    n = {"lock": 0, "buff": 0}
    for cid in eng.bz_tops(me):
        for ab in eng.cdef(cid).abilities or []:
            k = classify_static(ab) if isinstance(ab, dict) else None
            if k:
                n[k] += 1
    return n


def _moves_opp_resource(ops) -> bool:
    """効果列（ops）に、相手のマナ・山札・盾を墓地へ送る移動が含まれるか（マナ破壊・山札破壊の呪文など）。"""
    for op in ops or []:
        if not isinstance(op, dict):
            continue
        sel = op.get("select") or {}
        if op.get("op") == "move" and isinstance(sel, dict) and sel.get("owner") in ("opp", "opponent") \
                and sel.get("zone") in ("mana", "deck", "shield") and op.get("to") == "graveyard":
            return True
    return False


def is_drain_spell(cdef) -> bool:
    """相手の資源を減らす呪文（ドリル・スコールなど）。"""
    return "spell" in (cdef.types or []) and _moves_opp_resource(cdef.spell)


def is_recursion_engine(cdef) -> bool:
    """場にいる間、自分の墓地から呪文を手札へ戻す誘発を持つ（ジョバンニなど）。繰り返し除去の「繰り返し」側。"""
    for ab in cdef.abilities or []:
        if not (isinstance(ab, dict) and ab.get("kind") == "trigger"):
            continue
        for op in ab.get("effect") or []:
            sel = op.get("select") if isinstance(op, dict) else None
            if isinstance(sel, dict) and op.get("op") == "move" and op.get("to") == "hand" \
                    and sel.get("zone") == "graveyard" and sel.get("owner") == "you" \
                    and "spell" in ((sel.get("filter") or {}).get("types") or []):
                return True
    return False


def recur_counts(eng, me: int) -> dict:
    """繰り返し除去の部品: 戻す役が場に何体いるか、除去呪文が墓地・手札に何枚あるか。"""
    engines = sum(1 for cid in eng.bz_tops(me) if is_recursion_engine(eng.cdef(cid)))
    drains = sum(1 for z in ("graveyard", "hand") for cid in eng.zlist(z, me) if is_drain_spell(eng.cdef(cid)))
    return {"engines": engines, "drains": drains}


def lock_term(eng, me: int, lock_w: float = 150.0, buff_w: float = 20.0, recur_w: float = 150.0) -> float:
    """静的ロック・付与に加え、繰り返し除去（戻す役 × 墓地・手札の除去呪文）を継続的な資源減少として加点する。"""
    c = static_counts(eng, me)
    r = recur_counts(eng, me)
    return lock_w * c["lock"] + buff_w * c["buff"] + recur_w * min(r["engines"], 1) * r["drains"]


def make_term(**kw):
    return lambda eng, me: lock_term(eng, me, **kw)
