"""combo_hunt の検証済み結果を、計画の1種類「コンボ手順」（kind="combo_sequence"、計画仕様 v0 §4.7）として登録簿に入れる。
検証済み = エンジンの対局で実際にキル（kills>0）またはロック勝ち（lock_wins>0）が出たもの。静的な候補だけの組は入れない。

stages は大局観側（dmsim.plan.macro.load_plan_graph）が読む段の記述。ここでは「部品が手札にそろう」の1段（鎖）を置く。
勝ち筋の中継点（盾の束・手札の増加など）は、発見した手順から段階目標を作る後続の仕事で足す。"""
from __future__ import annotations

from dmsim.base.loopspec import Pred
from .spec import PlanSpec


def is_verified(rec: dict) -> bool:
    return (rec.get("kills") or 0) > 0 or (rec.get("lock_wins") or 0) > 0


def from_hunt_record(rec: dict, origin: str = "combo_hunt") -> PlanSpec:
    cards = list(rec["cards"])
    ev = {k: rec[k] for k in ("games", "kills", "kill_rate", "lock_wins", "self_lost", "turns", "errors") if k in rec}
    return PlanSpec(
        kind="combo_sequence", roles=("win_path",),
        minimal=[Pred(0, {"name": c}, zones=("hand", "bz")) for c in cards],
        params={"cards": cards, "names": list(rec.get("names", [])), "period": rec.get("period"),
                "delta": dict(rec.get("delta") or {}), "opp_delta": dict(rec.get("opp_delta") or {}),
                "evidence": ev,
                "stages": [{"id": "parts", "name": "部品が手札にそろう", "target": {"hand": {c: 1 for c in cards}}}]},
        source={"origin": origin, "deck": list(rec.get("deck") or []), "score": rec.get("score")},
    )


def register_verified(records, origin: str = "combo_hunt") -> list[PlanSpec]:
    """検証済みだけを PlanSpec にし、plan_id で重複を除く（先に来たものを残す）。"""
    out, seen = [], set()
    for r in records:
        if not is_verified(r):
            continue
        p = from_hunt_record(r, origin)
        if p.plan_id not in seen:
            seen.add(p.plan_id)
            out.append(p)
    return out
