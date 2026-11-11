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


def graph_from_items(items: list[tuple[str, str, int]], goal: dict | None = None):
    """部品 [(zone, id, n)] から前提つきの段の集合（StageGraph）を作る。
    同じゾーンの部品は並列（前提なし。引く順・出す順は探索が決める）。次のゾーンの部品は、前のゾーンの部品がすべて済んでいることが前提
    （ゾーン順 手札 → 場 → 墓地 → 盾 → マナ）。勝ちの出口 goal があれば、最後の部品がすべて済んでいることを前提に足す。
    各段の target はその部品だけ（済んだ段の目標は探索側で足す）。"""
    from .stagegraph import Node, StageGraph
    items = sorted({(z, i, n) for z, i, n in items if z in ZONE_ORDER}, key=lambda t: (ZONE_ORDER.index(t[0]), t[2], t[1]))
    nodes, prev, cur_zone, cur = [], [], None, []
    for z, i, n in items:
        if z != cur_zone:
            prev, cur, cur_zone = cur, [], z
        nid = f"{z}:{i}x{n}"
        nodes.append(Node(nid, {z: {i: n}}, tuple(prev), nid))
        cur.append(nid)
    if goal:
        nodes.append(Node("goal", goal, tuple(cur), "goal"))
    return StageGraph(nodes)


def graph_from_leaf_parts(parts):
    """combos.yaml の leaf_parts から（stages_from_leaf_parts の前提つき版）。"""
    items = []
    for p in parts:
        if p.get("weight", 1.0) < 1.0:
            continue
        for i in (p.get("ids") or ["*"]):
            items.append((p["zone"], i, p.get("need", 1)))
    return graph_from_items(items)


def graph_from_loopspec(ls):
    """LoopSpec の最小盤面 M（と出口 G）から。"""
    goal: dict = {}
    for z, i, n in _pred_items(ls.goal):
        goal.setdefault(z, {})[i] = n
    return graph_from_items(_pred_items(ls.minimal), goal or None)


def graph_from_planspec(plan):
    """登録簿の計画（dmsim.plan.spec.PlanSpec）から段階目標のグラフ（StageGraph）を作る。大局観が計画の種類を問わず読む入口。
    1. kind が combo_sequence（コンボ手順）で params["stages"] があれば、それを段の記述として読む
       （data/eval/stages/*.yaml の stages と同じ形: [{id?, name?, requires?, target}]。id / requires が無ければ鎖）。
       params["goal"]（reach_target 形式）があれば、最後に出口の段として足す。
    2. それ以外（loop など）や params["stages"] が無いときは、最小盤面 minimal（と出口 goal）の部品から
       graph_from_items と同じ作り方（同じゾーンの部品は並列、ゾーン順に前提）。"""
    from .stagegraph import Node, StageGraph
    stages = (plan.params or {}).get("stages")
    if plan.kind == "combo_sequence" and stages:
        g = StageGraph.from_stage_dicts(stages)
        goal = (plan.params or {}).get("goal")
        if goal:
            used = {x for m in g.nodes for r in m.requires for x in (r if isinstance(r, (list, tuple)) else (r,))}
            last = [n.id for n in g.nodes if n.id not in used]       # 他の段の前提になっていない段（末端）
            g = StageGraph(list(g.nodes) + [Node("goal", goal, tuple(last), "goal")])
        return g
    goal_items = _pred_items(plan.goal)
    goal: dict = {}
    for z, i, n in goal_items:
        goal.setdefault(z, {})[i] = n
    return graph_from_items(_pred_items(plan.minimal), goal or None)
