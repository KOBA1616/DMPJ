"""デッキ単位の再現性: 狙うカードを、必要な文明がそろった状態で、指定ターンまでにプレイできる確率。

多色のカードをプレイするには、必要な各文明のカードがマナゾーンに最低1枚ずつ要る（マナの合計もコスト以上）。
モデル（デッキをシャッフルするモンテカルロ）:
- 自分のターン t までに見たカード = 初手5枚 + 引いた分（先手はターン1に引かない）。
- 各ターン1枚、見たカードのうち1枚をチャージできる。狙うカードを手札に持ち続ける必要はなく、状況次第でチャージしてもよい。
- 'hindsight'（上限）: 全部見えた後で最善のチャージを選べたと仮定した成功率。実際の方策では下がる。
- 'online'（現実的な方策）: その時点で見えている手札だけで、足りない文明を持つカードを優先してチャージ（狙うカードの2枚目以降も可）。
- reach: {カード: k} …「手札、または山札の上から k 枚にあれば可」（騎士の「3枚引く」で DMC に届く、など）。
"""
from __future__ import annotations

import itertools
import random


def _face(rules, cid: str):
    cd = rules.cards[cid]
    return cd.face(None) if hasattr(cd, "face") else cd


def _civs(rules, cid: str) -> set:
    return set(_face(rules, cid).civs) - {"zero"}


def _cost(rules, cid: str) -> int:
    return _face(rules, cid).cost


def _can_charge_ok(rules, others: list[str], req: set, k: int) -> bool:
    """others（チャージに使える候補）から k 枚選んで、req の文明をすべて覆えるか。"""
    if len(others) < k:
        return False
    if not req:
        return True
    civs = [_civs(rules, c) & req for c in others]
    for r in range(1, min(k, len(req)) + 1):
        for comb in itertools.combinations(range(len(others)), r):
            if set().union(*[civs[i] for i in comb]) >= req:
                return True
    return False


def play_ready_prob(rules, deck: list[str], target: str, turns=(2, 3, 4, 5, 6), first_player: bool = True, n: int = 2000,
                    seed: int = 1, need: list[str] | None = None, reach: dict | None = None, mode: str = "both") -> dict:
    """target を、文明がそろった状態でターン t までにプレイできる確率。
    need: 同時に手札（または reach の範囲）にそろえるカード。ただしコストと文明の条件は target だけに課す
    （need のカードは、騎士が捨てて墓地から戻すだけなど、プレイしないことが多いため）。
    戻り値: {"hindsight": {t: p}, "online": {t: p}}。"""
    reach = reach or {}
    req = _civs(rules, target)
    cost = _cost(rules, target)
    rng = random.Random(seed)
    hs = {t: 0 for t in turns}
    on = {t: 0 for t in turns}
    tmax = max(turns)
    for _ in range(n):
        d = list(deck)
        rng.shuffle(d)
        # --- online 方策 ---
        hand, mana, pos = d[:5], [], 5
        for t in range(1, tmax + 1):
            if not (t == 1 and first_player):
                hand.append(d[pos])
                pos += 1
            have = set().union(*[_civs(rules, c) for c in mana]) if mana else set()
            # 狙うカードと need を1枚ずつ手札に残し、残りからチャージする。足りない文明を優先。
            keep, rest = [], list(hand)
            for c in [target] + list(need or []):
                if c in rest:
                    rest.remove(c)
                    keep.append(c)
            if rest:
                rest.sort(key=lambda c: -len((_civs(rules, c) & req) - have))
                mana.append(rest.pop(0))
            elif len(keep) > 1 or (keep and t >= cost):
                pass
            hand = keep + rest
            if t in on:
                have = set().union(*[_civs(rules, c) for c in mana]) if mana else set()
                top = d[pos:pos + max([0] + list(reach.values()))]
                ok_need = all((c in hand) or (reach.get(c, 0) and c in top[:reach[c]]) for c in (need or []))
                if target in hand and ok_need and len(mana) >= cost and req <= have:
                    on[t] += 1
        # --- hindsight（上限）---
        for t in turns:
            seen_n = 5 + (t - 1 if first_player else t)
            seen = d[:seen_n]
            if target not in seen:
                continue
            rest = list(seen)
            rest.remove(target)
            ok_need = True
            top = d[seen_n:seen_n + max([0] + list(reach.values()))]
            for c in (need or []):
                if c in rest:
                    rest.remove(c)
                elif not (reach.get(c, 0) and c in top[:reach[c]]):
                    ok_need = False
            if ok_need and t >= cost and _can_charge_ok(rules, rest, req, t if t >= cost else cost):
                hs[t] += 1
    return {"hindsight": {t: hs[t] / n for t in turns}, "online": {t: on[t] / n for t in turns}}
