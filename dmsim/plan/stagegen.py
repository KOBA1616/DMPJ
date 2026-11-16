"""段階目標の鎖を、既知コンボの部品データから自動で作る（手で data/eval/stages/*.yaml を書かない）。
入力は LoopSpec の最小盤面 M か、combos.yaml の leaf_parts（部品表）。どちらも「最終盤面を満たす部品の集合」なので、
ゾーンの順（手札 → 場 → 墓地 → 盾 → マナ）に1つずつ足した累積の目標を中継点にする（最後の段 = 最終盤面）。
- 山札の中身は公開情報ではないので deck の述語は捨てる（公平探索）。相手側(owner=1)の述語も捨てる。
- 名前のある述語は {ID: n}、名前の無いもの（型だけ）は {"*": n} とする。
- 勝ちの出口 G（LoopSpec.goal）があれば最後に足す。
reach_chain に渡す形は MacroPlanner と同じ（data/eval/stages/tenmon.yaml と同形式）。"""
from __future__ import annotations

ZONE_ORDER = ("hand", "bz", "graveyard", "shield", "mana")


def _merge(a: dict, b: dict) -> dict:
    out = {z: dict(v) for z, v in a.items()}
    for z, v in b.items():
        for i, n in v.items():
            out.setdefault(z, {})[i] = max(out.get(z, {}).get(i, 0), n)
    return out


def _chain(items: list[tuple[str, str, int]], goal: dict | None = None) -> list[dict]:
    """items: [(zone, id, n)]。ゾーン順に並べ、同じゾーンは必要枚数の少ない方から1つずつ足した累積の段を返す。"""
    items = sorted({(z, i, n) for z, i, n in items if z in ZONE_ORDER}, key=lambda t: (ZONE_ORDER.index(t[0]), t[2], t[1]))
    stages, cur = [], {}
    for z, i, n in items:
        cur = _merge(cur, {z: {i: n}})
        stages.append({"name": f"{z}:{i}x{n}", "target": {k: dict(v) for k, v in cur.items()}})
    if goal:
        stages.append({"name": "goal", "target": _merge(cur, goal)})
    return stages


def _pred_items(preds) -> list[tuple[str, str, int]]:
    out = []
    for p in preds:
        zone = p.zone or (p.zones[0] if p.zones else None)
        if p.owner != 0 or p.op != ">=" or zone is None or zone == "deck":
            continue
        out.append((zone, p.match.get("name", "*"), p.n))
    return out


def stages_from_loopspec(ls) -> list[dict]:
    """LoopSpec の最小盤面 M（と出口 G）から段階目標の鎖。"""
    goal: dict = {}
    for z, i, n in _pred_items(ls.goal):
        goal.setdefault(z, {})[i] = n
    return _chain(_pred_items(ls.minimal), goal)


def stages_from_leaf_parts(parts) -> list[dict]:
    """combos.yaml の leaf_parts（zone/ids/need/weight）から。重みの小さい部品（補助）は捨て、ids が空の部品は {"*": need}。"""
    items = []
    for p in parts:
        if p.get("weight", 1.0) < 1.0:
            continue
        for i in (p.get("ids") or ["*"]):
            items.append((p["zone"], i, p.get("need", 1)))
    return _chain(items)
