"""仕込み済み開始局面を、コンボの部品表（known_combos の core 部品）とデッキから自動で作る。
LoopSpec も手書きの局面も無いコンボ用。手書きの値は使わない: 重い部品（heavy_ids）のうちデッキにある最初の1枚を手札に、
重い部品の文明をそろえるマナ5枚（デッキ内の重い部品以外から貪欲に選ぶ）を置く。残りの部品は山札に残り、
候補デッキの差し替えは spec_with_deck が山札側で行う。"""
from __future__ import annotations

from collections import Counter

from ..search.leaf_parts import heavy_ids

MANA_N = 5
HAND_N = 5
FILLER = "T001"


def parts_setup(rules, combo: dict, deck: list[str]) -> dict | None:
    heavy = [i for i in heavy_ids(combo) if i in deck]
    if not heavy:
        return None
    hold = heavy[0]
    need = {c for i in heavy if i in rules.cards for c in rules.cards[i].civs}
    left = Counter(deck)
    left[hold] -= 1
    pool = sorted((i for i in left.elements() if i not in heavy and i in rules.cards))
    mana: list[str] = []
    covered: set[str] = set()
    while len(mana) < MANA_N and pool:
        best = max(pool, key=lambda i: len((set(rules.cards[i].civs) & need) - covered))
        mana.append(best)
        pool.remove(best)
        covered |= set(rules.cards[best].civs)
    if len(mana) < MANA_N:
        return None
    return {"p0": {"hand": [hold] + [FILLER] * (HAND_N - 1), "mana": mana, "graveyard": []}, "p1": {},
            "deck_size": 0, "shuffle_deck": True}
