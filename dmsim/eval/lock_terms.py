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


def lock_term(eng, me: int, lock_w: float = 150.0, buff_w: float = 20.0) -> float:
    c = static_counts(eng, me)
    return lock_w * c["lock"] + buff_w * c["buff"]


def make_term(**kw):
    return lambda eng, me: lock_term(eng, me, **kw)
