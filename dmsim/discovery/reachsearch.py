"""目標局面への到達探索: 通常の開幕から、指定した局面（ゾーン→{カード定義ID: 枚数}の下限）に自分のターンで届けるかを探す。

用途: 仕込み局面の生成器（zone_graph の閉路など）が出した局面について「通常の開幕から本当に到達できるか」を判定する入口。
bestfirst.beam と同じ骨格（同じ局面は1度だけ展開、相手のターンもまたぐ）で、勝ちの代わりに目標の充足を探す。
目標が満たされていく割合を評価に大きく足して導く（山札・盾の中身は見ない公平な探索ではなく、真の山札順を見る探索である点に注意）。"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ..engine import Engine
from ..engine_view import defn_of, result_of, tapped_of, turn_of, zone_of
from ..eval.stage import zone_counts
from ..loop import abstract
from ..solitaire import Weights, candidates, charge_only_policy
from .bestfirst import _Settler, priority

GOAL_W = 1000.0
ANY = "*"      # target の ID に "*" を書くと、そのゾーンの枚数の合計（例 {"shield": {"*": 10}} = 自分の盾が10枚以上）


def _have(eng: Engine, me: int, z: str, i: str) -> int:
    return len(eng.zlist(z, me)) if i == ANY else zone_counts(eng, me, z).get(i, 0)


def board_met(eng: Engine, me: int, target: dict) -> bool:
    return all(_have(eng, me, z, i) >= n for z, want in target.items() for i, n in want.items())


@dataclass
class ReachResult:
    reached: bool
    nodes: int
    engine: Engine | None      # 到達した局面（再生は engine.log）
    turn: int | None           # 到達した時の通しターン
    best_fraction: float       # 探索中に届いた最大の充足率（届かなかった時の目安）


def fraction(eng: Engine, me: int, target: dict) -> float:
    """目標のうち満たされている割合（各 (ゾーン, ID) の min(所持, 必要) の和 / 必要の和）。"""
    need = sum(n for z in target.values() for n in z.values())
    if not need:
        return 1.0
    have = sum(min(_have(eng, me, z, i), n) for z, want in target.items() for i, n in want.items())
    return have / need


def reach_target(eng: Engine, target: dict, me: int = 0, width: int = 300, max_depth: int = 80, max_turn: int = 6,
                 w: Weights | None = None, opp_policy=None) -> ReachResult:
    w = w or Weights()
    ts = _Settler(me, opp_policy or charge_only_policy, max_turn)
    layer = [eng.clone()]
    seen: set = set()
    nodes, best = 0, 0.0
    for _ in range(max_depth):
        nxt = []
        for cur in layer:
            d = ts._settle(cur)
            if board_met(cur, me, target):
                return ReachResult(True, nodes, cur, turn_of(cur), 1.0)
            if result_of(cur) is not None or d is None:
                continue
            h, ctr = abstract(cur, "in_turn")
            deck_order = tuple(defn_of(cur, c) for c in zone_of(cur, "deck", me))
            key = (h, deck_order, tuple(sorted(ctr.items())), tuple(sorted(defn_of(cur, x) + str(tapped_of(cur, x)) for p in (0, 1) for x in zone_of(cur, "mana", p))))
            if key in seen:
                continue
            seen.add(key)
            for ch in candidates(cur, d, w, 6):
                nodes += 1
                child = cur.clone()
                child.answer(ch)
                ts._settle(child)
                if board_met(child, me, target):
                    return ReachResult(True, nodes, child, turn_of(child), 1.0)
                if result_of(child) is not None:
                    continue
                fr = fraction(child, me, target)
                best = max(best, fr)
                nxt.append((priority(child, me, w) + GOAL_W * fr, nodes, child))
        if not nxt:
            break
        nxt.sort(key=lambda x: (-x[0], x[1]))
        layer = [c for _, _, c in nxt[:width]]
    return ReachResult(False, nodes, None, None, best)


def reach_rate(rules, deck: list[str], target: dict, seeds, opp_deck: list[str] | None = None, **kw) -> dict:
    """seeds ごとに通常の開幕から到達探索。{"rate", "reached": [seed], "turns": {seed: ターン}, "nodes"}。先後は seed の偶奇で交互。"""
    out = {"reached": [], "turns": {}, "nodes": 0}
    seeds = list(seeds)
    for sd in seeds:
        e = Engine.new_game(rules, [deck, opp_deck or ["T001"] * 40], sd, first_player=sd % 2)
        r = reach_target(e, target, 0, **kw)
        out["nodes"] += r.nodes
        if r.reached:
            out["reached"].append(sd)
            out["turns"][sd] = r.turn
    out["rate"] = len(out["reached"]) / len(seeds) if seeds else 0.0
    return out


def reach_chain(eng: Engine, stages: list[dict], me: int = 0, **kw) -> dict:
    """段階目標を順に到達させる（勝利条件から分解した中継点を、前の段階の到達局面から続けて探す）。
    {"stages": 到達した段階数, "turns": [各段階の到達ターン], "nodes", "engine": 最後に届いた局面}"""
    cur, turns, nodes = eng, [], 0
    for tg in stages:
        r = reach_target(cur, tg, me, **kw)
        nodes += r.nodes
        if not r.reached:
            break
        cur = r.engine
        turns.append(r.turn)
    return {"stages": len(turns), "turns": turns, "nodes": nodes, "engine": cur}
