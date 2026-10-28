"""最良優先探索: 自分のターン内の選択を、述語までの距離で導いて探す（深さ優先の予算切れで勝ちを逃す盤面向け）。

評価は solitaire.evaluate に、次の2つの形（カード名を含まない）を足したもの:
- 自分の待機中の誘発（pending）の数: 解決前に積んだ効果は、後でまとめて使える資源とみなす。
- 常在の勝利条件（kind: state）を持つカードが、場・手札のどこかにある時、その条件の数（自分の盾など）。
同じ局面（骨格＋カウンタ）は1度だけ展開する。"""
from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass

from ..engine import Engine
from ..loop import abstract
from ..solitaire import Weights, candidates, evaluate, goal_distance


@dataclass
class BFResult:
    won: bool
    nodes: int
    engine: Engine
    log_len: int


def _goal_cards(eng: Engine, me: int) -> bool:
    for z in ("bz", "hand"):
        for c in eng.zlist(z, me):
            if eng.rules.cards[eng.s.cards[c].defn].abilities and any(a["kind"] == "state" for a in eng.rules.cards[eng.s.cards[c].defn].abilities):
                return True
    return False


def priority(eng: Engine, me: int, w: Weights, pend_w: float = 40.0, own_shield_w: float = 5.0) -> float:
    v = evaluate(eng, me, w)
    v += pend_w * sum(1 for p in eng.s.pending if p["controller"] == me)
    if _goal_cards(eng, me):
        v += own_shield_w * len(eng.zlist("shield", me))
    return v


def search(eng: Engine, me: int = 0, budget: int = 20000, w: Weights | None = None, opp_policy=None) -> BFResult:
    from ..solitaire import TurnSearch, charge_only_policy
    w = w or Weights()
    ts = TurnSearch(me, 1, w, opp_policy or charge_only_policy)
    tie = itertools.count()
    start = eng.clone()
    heap = [(0.0, next(tie), start)]
    seen: set = set()
    nodes, best = 0, (-1e18, start)
    while heap and nodes < budget:
        _, _, cur = heapq.heappop(heap)
        d = ts._settle(cur)
        if cur.s.result is not None:
            if cur.s.result["winner"] == me:
                return BFResult(True, nodes, cur, len(cur.log))
            continue
        if d is None:
            continue
        h, ctr = abstract(cur, "in_turn")
        key = (h, tuple(sorted(ctr.items())), tuple(sorted((c.defn, c.tapped) for p in (0, 1) for x in cur.s.zones["mana"][p] for c in [cur.s.cards[x]])))
        if key in seen:
            continue
        seen.add(key)
        for ch in candidates(cur, d, w, 6):
            nodes += 1
            child = cur.clone()
            child.answer(ch)
            pr = -priority(child, me, w)
            heapq.heappush(heap, (pr, next(tie), child))
            if -pr > best[0]:
                best = (-pr, child)
    return BFResult(False, nodes, best[1], len(best[1].log))
