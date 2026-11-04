"""デッキ単位の再現性: 狙うカードを、必要な文明がそろった状態で、指定ターンまでにプレイできる確率。

多色のカードをプレイするには、必要な各文明のカードがマナゾーンに最低1枚ずつ要る（マナの合計もコスト以上）。
方策: 手札と引いたカードからターンごとに1枚チャージする。足りない文明を持つカードを優先し、狙うカード自体はチャージしない。
モンテカルロ（デッキをシャッフル）で、ターン t の自分の本番までに「手札にそのカードがあり、マナが cost 以上で、文明がそろう」割合を返す。
"""
from __future__ import annotations

import random


def _civs(rules, cid: str) -> set:
    cd = rules.cards[cid]
    return set(getattr(cd, "civs", None) or cd.face(None).civs)


def _cost(rules, cid: str) -> int:
    cd = rules.cards[cid]
    return cd.face(None).cost if hasattr(cd, "face") else cd.cost


def play_ready_prob(rules, deck: list[str], target: str, turns=(2, 3, 4, 5, 6), first_player: bool = True, n: int = 2000,
                    seed: int = 1, need: list[str] | None = None) -> dict:
    """need: 同時に手札にそろえる必要のあるカード（コンボの相手）。省略すれば target だけ。"""
    tgt = [target] + list(need or [])
    req = set().union(*[_civs(rules, c) - {"zero"} for c in tgt])
    cost = max(_cost(rules, c) for c in tgt)
    rng = random.Random(seed)
    hits = {t: 0 for t in turns}
    for _ in range(n):
        d = list(deck)
        rng.shuffle(d)
        hand, mana, pos = d[:5], [], 5
        for t in range(1, max(turns) + 1):
            if not (t == 1 and first_player):
                hand.append(d[pos])
                pos += 1
            need_cards = list(tgt)
            held = [c for c in hand if c not in need_cards] + []
            # 狙うカードの枚数分は手札に残す
            keep = []
            rest = list(hand)
            for c in need_cards:
                if c in rest:
                    rest.remove(c)
                    keep.append(c)
            have = set().union(*[_civs(rules, c) for c in mana]) if mana else set()
            if rest:
                rest.sort(key=lambda c: -len((_civs(rules, c) & req) - have))
                mana.append(rest.pop(0))
            hand = keep + rest
            if t in hits:
                have = set().union(*[_civs(rules, c) for c in mana]) if mana else set()
                if len(keep) == len(tgt) and len(mana) >= cost and req <= (have | {"zero"}):
                    hits[t] += 1
    return {t: hits[t] / n for t in turns}
