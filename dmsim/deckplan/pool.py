"""加速・ドロー・サーチ・仕込み札の候補プール。変換済みカード全体を効果データ（op）で自動分類する（読むだけ。エンジン・カードデータは変えない）。
役割: accel=山札/手札から自分のマナへ置く、draw=自分が引く、search=山札から手札へ加える、prep=自分の山札・手札などを墓地へ送る。
deck_fix の候補生成（change.add_support）が、デッキの文明に収まる札だけをここから選ぶ。採否は evaluate.decide のみ。"""
from __future__ import annotations

from pathlib import Path

import yaml
from ..base.store import REPO

ROOT = REPO
ROLES = ("accel", "draw", "search", "prep")
_MINE = ("you", "self", None)


def _walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from _walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from _walk(v)


def _zone(sel) -> str | None:
    z = sel.get("zone") if isinstance(sel, dict) else None
    return z if isinstance(z, str) else None


def _mine(sel) -> bool:
    return isinstance(sel, dict) and sel.get("owner") in _MINE


def classify(card: dict) -> set[str]:
    """カードの効果データから役割の集合を返す。"""
    out: set[str] = set()
    for d in _walk(card.get("abilities", []) + [card.get("spell", [])] if isinstance(card.get("abilities"), list) else card):
        op, to, sel = d.get("op"), d.get("to"), d.get("select")
        if op == "draw" and d.get("player", "you") in ("you", "self") and (d.get("count") or 1) != 0:
            out.add("draw")
        elif op == "mana_put" and _mine(sel) and _zone(sel) in ("deck", "hand"):
            out.add("accel")
        elif op == "mill" and d.get("owner", "you") in ("you", "self"):
            out.add("prep")
        elif op == "move" and _mine(sel):
            z = _zone(sel)
            if to == "mana" and z in ("deck", "hand"):
                out.add("accel")
            elif to == "hand" and z == "deck":
                out.add("search")
            elif to == "graveyard" and z in ("hand", "deck", "mana", "shield", "shields"):
                out.add("prep")
    return out


def load_pool(paths: list[Path] | None = None, max_cost: int = 4) -> list[dict]:
    """[{name, id, cost, civs, roles}]。同名は先に見つかった版。コスト不明・max_cost 超は除く。"""
    paths = paths or sorted((ROOT / "data/cards").glob("*.yaml"))
    found, seen = [], set()
    for p in paths:
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        items = (data.get("cards", data) if isinstance(data, dict) else data) or []
        for c in items.values() if isinstance(items, dict) else items:
            if not isinstance(c, dict) or not c.get("name") or c["name"] in seen:
                continue
            cost = c.get("cost")
            if not isinstance(cost, int) or cost > max_cost:
                continue
            roles = classify(c)
            if roles:
                seen.add(c["name"])
                found.append({"name": c["name"], "id": c.get("id"), "cost": cost, "civs": list(c.get("civs") or []), "roles": sorted(roles)})
    return found


def support_names(deck_civs: set[str], roles=("accel", "draw", "search"), max_cost: int = 4, pool: list[dict] | None = None) -> dict[str, list[str]]:
    """デッキの文明に収まる（無色は可）候補の名前を役割ごとに返す。コストの軽い順。"""
    out: dict[str, list[str]] = {r: [] for r in roles}
    for r in sorted(pool if pool is not None else load_pool(max_cost=max_cost), key=lambda r: (r["cost"], r["name"])):
        if r["cost"] > max_cost or not set(r["civs"]) <= deck_civs:
            continue
        for role in roles:
            if role in r["roles"]:
                out[role].append(r["name"])
    return out
