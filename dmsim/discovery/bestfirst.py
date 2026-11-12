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
from ..engine_view import defn_of, pending_of, result_of, tapped_of, turn_of, zone_of


@dataclass
class BFResult:
    won: bool
    nodes: int
    engine: Engine
    log_len: int


def _goal_cards(eng: Engine, me: int) -> bool:
    for z in ("bz", "hand"):
        for c in eng.zlist(z, me):
            if eng.rules.cards[defn_of(eng, c)].abilities and any(a["kind"] == "state" for a in eng.rules.cards[defn_of(eng, c)].abilities):
                return True
    return False


class _Settler:
    """相手の決定を相手役に答えさせながら、自分の決定か終局まで進める（相手のターンもまたぐ）。max_turn を超えたら打ち切る。"""

    def __init__(self, me: int, opp_policy, max_turn: int | None):
        self.me, self.opp_policy, self.max_turn = me, opp_policy, max_turn

    def _settle(self, eng: Engine):
        while True:
            d = eng.advance()
            if d is None:
                return None
            if self.max_turn is not None and turn_of(eng) > self.max_turn:
                return None
            if d["player"] == self.me:
                return d
            eng.answer(self.opp_policy(eng, d))


MID_RESOLUTION_KEY = True   # 解決途中の決定点では、直前の答えを重複除外のキーに足す（同じ骨格でも選んだモードなどが違えば別の局面）
_TOP_LEVEL = ("main", "charge", "attack")


def _mid_key(cur, d) -> tuple:
    if not MID_RESOLUTION_KEY or d["kind"] in _TOP_LEVEL:
        return ()
    return (d["kind"], tuple(tuple(x.get("keys", ())) for x in cur.log[-3:]))


def priority(eng: Engine, me: int, w: Weights, pend_w: float = 40.0, own_shield_w: float = 5.0) -> float:
    v = evaluate(eng, me, w)
    v += pend_w * sum(1 for p in pending_of(eng) if p["controller"] == me)
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
        if result_of(cur) is not None:
            if result_of(cur)["winner"] == me:
                return BFResult(True, nodes, cur, len(cur.log))
            continue
        if d is None:
            continue
        h, ctr = abstract(cur, "in_turn")
        deck_order = tuple(defn_of(cur, c) for c in zone_of(cur, "deck", me))   # 山札の並びは次に引く・積むカードを決める
        key = (h, deck_order, tuple(sorted(ctr.items())), tuple(sorted((defn_of(cur, x), tapped_of(cur, x)) for p in (0, 1) for x in zone_of(cur, "mana", p)))) + _mid_key(cur, d)
        if key in seen:
            continue
        seen.add(key)
        for ch in candidates(cur, d, w, 6):
            nodes += 1
            child = cur.clone()
            child.answer(ch)
            ts._settle(child)      # 次の決定まで進めてから評価する（選んだ効果の結果を見る）
            pr = -priority(child, me, w)
            heapq.heappush(heap, (pr, next(tie), child))
            if -pr > best[0]:
                best = (-pr, child)
    return BFResult(False, nodes, best[1], len(best[1].log))


def beam(eng: Engine, me: int = 0, width: int = 200, max_depth: int = 80, w: Weights | None = None, opp_policy=None,
         max_turn: int | None = None, prio=None) -> BFResult:
    """ビーム探索: 決定の深さごとに、評価の高い width 個だけを残して進める。最良優先探索が「いま良く見える枝」に偏って
    谷（盾をいったん減らしてから増やす、など）を越えられない盤面向け。同じ局面（骨格＋山札の並び＋カウンタ）は1度だけ展開する。"""
    from ..solitaire import TurnSearch, charge_only_policy
    w = w or Weights()
    prio = prio or priority        # 順位づけ (eng, me, w) -> 点。大局観つき: dmsim.eval.vfeatures.macro_prio
    ts = TurnSearch(me, 1, w, opp_policy or charge_only_policy)
    if max_turn is not None:       # 複数ターンの探索: 相手のターンもまたいで、max_turn ターン目までに勝てるかを見る
        ts = _Settler(me, opp_policy or charge_only_policy, max_turn)
    layer = [eng.clone()]
    seen: set = set()
    nodes = 0
    best = (-1e18, layer[0])
    for _ in range(max_depth):
        nxt = []
        for cur in layer:
            d = ts._settle(cur)
            if result_of(cur) is not None:
                if result_of(cur)["winner"] == me:
                    return BFResult(True, nodes, cur, len(cur.log))
                continue
            if d is None:
                continue
            h, ctr = abstract(cur, "in_turn")
            deck_order = tuple(defn_of(cur, c) for c in zone_of(cur, "deck", me))
            key = (h, deck_order, tuple(sorted(ctr.items())), tuple(sorted(defn_of(cur, x) + str(tapped_of(cur, x)) for p in (0, 1) for x in zone_of(cur, "mana", p)))) + _mid_key(cur, d)
            if key in seen:
                continue
            seen.add(key)
            for ch in candidates(cur, d, w, 6):
                nodes += 1
                child = cur.clone()
                child.answer(ch)
                ts._settle(child)
                if result_of(child) is not None and result_of(child)["winner"] == me:
                    return BFResult(True, nodes, child, len(child.log))
                pr = prio(child, me, w)
                nxt.append((pr, nodes, child))
                if pr > best[0]:
                    best = (pr, child)
        if not nxt:
            break
        nxt.sort(key=lambda x: (-x[0], x[1]))
        layer = [c for _, _, c in nxt[:width]]
    return BFResult(False, nodes, best[1], len(best[1].log))
