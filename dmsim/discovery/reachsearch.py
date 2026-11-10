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
    if z == "shield_under":   # 盾の下に置かれたカードの合計枚数（ID は "*" のみ）。盾の束の大きさ
        return sum(len(eng.s.cards[c].under) for c in eng.zlist("shield", me))
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


QUIET_KINDS = ("main", "charge")   # 自分のターンの通常の選択点（効果の解決中でない）


def _quiet(d, settled: bool) -> bool:
    """settled=True の時は、効果の解決（モード選択・対象選択など）が終わった通常の選択点でだけ到達と数える。
    ミルザムの『出た時』の効果のように、出た直後に未解決の効果が残る目標（盾の下の枚数など）を、解決後に測るため。"""
    return (not settled) or d is None or d.get("kind") in QUIET_KINDS


def reach_target(eng: Engine, target: dict, me: int = 0, width: int = 300, max_depth: int = 80, max_turn: int = 6,
                 w: Weights | None = None, opp_policy=None, prio=None, settled: bool = False,
                 reserve: int = 0, reserve_target: dict | None = None) -> ReachResult:
    """reserve>0 かつ reserve_target: 幅のうち reserve 枠を「計画の次の段 reserve_target の充足率が高い局面」に予約する（点数に足さず、枝刈りで残す）。"""
    w = w or Weights()
    prio = prio or priority
    ts = _Settler(me, opp_policy or charge_only_policy, max_turn)
    layer = [eng.clone()]
    seen: set = set()
    nodes, best = 0, 0.0
    for _ in range(max_depth):
        nxt = []
        for cur in layer:
            d = ts._settle(cur)
            if board_met(cur, me, target) and _quiet(d, settled):
                return ReachResult(True, nodes, cur, turn_of(cur), 1.0)
            if result_of(cur) is not None or d is None:
                continue
            h, ctr = abstract(cur, "in_turn")
            deck_order = tuple(defn_of(cur, c) for c in zone_of(cur, "deck", me))
            key = (h, deck_order, tuple(sorted(ctr.items())), tuple(sorted(defn_of(cur, x) + str(tapped_of(cur, x)) for p in (0, 1) for x in zone_of(cur, "mana", p))))
            if d["kind"] not in QUIET_KINDS:   # 効果の解決の途中: 直前の答え（選んだモードなど）が未解決の効果の引数になるので、同じ局面とみなさない
                key += (d["kind"], tuple(tuple(x.get("keys", ())) for x in cur.log[-3:]))
            if key in seen:
                continue
            seen.add(key)
            for ch in candidates(cur, d, w, 6):
                nodes += 1
                child = cur.clone()
                child.answer(ch)
                cd = ts._settle(child)
                if board_met(child, me, target) and _quiet(cd, settled):
                    return ReachResult(True, nodes, child, turn_of(child), 1.0)
                if result_of(child) is not None:
                    continue
                fr = fraction(child, me, target)
                best = max(best, fr)
                nxt.append((prio(child, me, w) + GOAL_W * fr, nodes, child))
        if not nxt:
            break
        nxt.sort(key=lambda x: (-x[0], x[1]))
        if reserve and reserve_target and len(nxt) > width:
            head, tail = nxt[:max(width - reserve, 1)], nxt[max(width - reserve, 1):]
            tail.sort(key=lambda x: (-fraction(x[2], me, reserve_target), -x[0], x[1]))     # 次の段に近い順（同点は元の点数順）
            nxt = head + tail[:reserve]
            layer = [c for _, _, c in nxt]
        else:
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


def _merge(a: dict, b: dict) -> dict:
    """2つの段の目標を1つにまとめる（同じ (ゾーン, 札) は大きい方の枚数）。"""
    out = {z: dict(v) for z, v in a.items()}
    for z, v in b.items():
        for i, n in v.items():
            out.setdefault(z, {})[i] = max(out.get(z, {}).get(i, 0), n)
    return out


def _with_keep(eng: Engine, me: int, stages: list[dict], k: int) -> dict:
    """段 k の目標に、「後ろの段が要る札で今手札にあるものを手札に残す」条件を足す（先に使い切る手を選ばせない）。
    後ろの段のゾーンが hand 以外（場・墓地・盾）の札が対象。既に目標に手札で入っているものは足さない。"""
    tg = {z: dict(v) for z, v in stages[k].items()}
    here = {i for v in stages[k].values() for i in v}            # この段の目標に出る札は残さない（同じ札が目標と手札に二重に要る矛盾を避ける）
    later: dict[str, int] = {}
    for st in stages[k + 1:]:
        for z, want in st.items():
            for i, n in want.items():
                if z != "hand" and i != "*" and i not in here:
                    later[i] = max(later.get(i, 0), n)
    for i, n in later.items():
        have = _have(eng, me, "hand", i)
        if have and i not in tg.get("hand", {}):
            tg.setdefault("hand", {})[i] = min(have, n)
    return tg


def reach_chain(eng: Engine, stages: list[dict], me: int = 0, keep_later: bool = False, lookahead: int = 3, **kw) -> dict:
    """段階目標を順に到達させる（勝利条件から分解した中継点を、前の段階の到達局面から続けて探す）。
    keep_later=True: 次の段と合わせて一度に届く経路、次に後ろの段が要る札を手札に残したまま届く局面を先に探す（届かなければ元の目標で探す）。
    前段の最短経路が後ろの段の札を使い切ってしまい、鎖が途中で止まるのを防ぐ。
    {"stages": 到達した段階数, "turns": [各段階の到達ターン], "nodes", "engine": 最後に届いた局面}"""
    cur, turns, nodes = eng, [], 0
    k = 0
    cnt = [0]

    def moves(c, i):
        """段 i から進める手の候補: [(到達局面, 進む段数, ターン)]。keep（後ろの段の札を残す）→ 素直に1段 →（keep_later のとき）次段と合わせた目標。"""
        out = []
        kw2 = dict(kw)
        if kw2.get("reserve"):
            kw2["reserve_target"] = stages[i + 1] if i + 1 < len(stages) else None
        r = reach_target(c, _with_keep(c, me, stages, i), me, **kw2) if keep_later and i + 1 < len(stages) else None
        if r is not None:
            cnt[0] += r.nodes
        if r is None or not r.reached:
            r = reach_target(c, stages[i], me, **kw2)
            cnt[0] += r.nodes
        if r.reached:
            out.append((r.engine, 1, r.turn))
        if keep_later and i + 1 < len(stages):
            mg = reach_target(c, _merge(stages[i], stages[i + 1]), me, **{**kw2, "reserve_target": stages[i + 2] if i + 2 < len(stages) else None})
            cnt[0] += mg.nodes
            if mg.reached:
                out.append((mg.engine, 2, mg.turn))
        return out

    def plan(c, i, depth):
        """depth 手先まで読んで、進める段数が最大の最初の手を返す（(進んだ合計, 手)）。同点は手前の候補（keep の1段）を優先。"""
        if i >= len(stages) or depth == 0:
            return 0, None
        best = (0, None)
        for mv in moves(c, i):
            tot = mv[1] + (plan(mv[0], i + mv[1], depth - 1)[0] if depth > 1 else 0)
            if tot > best[0]:
                best = (tot, mv)
        return best

    while k < len(stages):
        _, mv = plan(cur, k, lookahead if keep_later else 1)
        if mv is None:
            break
        cur, took, t = mv
        turns.extend([t] * took)
        k += took
    nodes = cnt[0]
    return {"stages": len(turns), "turns": turns, "nodes": nodes, "engine": cur}
