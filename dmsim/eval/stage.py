"""段階指標の共通部品。探索葉の部品スコア（search/leaf_parts）と評価の段階指標（eval/progress）が同じ数え方を使う。

- zone_counts      : 自分側ゾーンの {定義ID: 枚数}
- count_matching   : ゾーン内で ids のどれか（空ならクリーチャー全般）に当たる枚数
- board_met        : 最小盤面 {zone: {id: n}} を全部満たすか
- cards_met        : 必要カード {id: n} が見えるゾーン（山札・盾以外）にそろったか
- parts_to_cards   : 部品表（zone/ids/need を持つ列）→ 必要カード {id: n}（評価側の cards に使える）
山札・盾の中身は公開情報ではないので VISIBLE_ZONES に含めない。
"""
from __future__ import annotations

from collections import Counter

VISIBLE_ZONES = ("hand", "bz", "mana", "graveyard", "shield_bz")


def zone_counts(eng, me: int, zone: str) -> Counter:
    s = eng.s
    return Counter(s.cards[c].defn for c in eng.zlist(zone, me))


def count_matching(eng, me: int, zone: str, ids=()) -> int:
    s = eng.s
    n = 0
    for cid in eng.zlist(zone, me):
        if (ids and s.cards[cid].defn in ids) or (not ids and "creature" in eng.chars(cid)["types"]):
            n += 1
    return n


def board_met(eng, me: int, board: dict) -> bool:
    return all(not (Counter(need) - zone_counts(eng, me, z)) for z, need in board.items())


def cards_met(eng, me: int, cards: dict) -> bool:
    if not cards:
        return False
    have: Counter = Counter()
    for z in VISIBLE_ZONES:
        try:
            have += zone_counts(eng, me, z)
        except KeyError:
            pass
    return not (Counter(cards) - have)


def parts_to_cards(parts) -> dict:
    """部品（zone, ids, need）の列 → {id: 必要枚数}。ids が空の部品（クリーチャー全般）は除く。同じ id は最大の need をとる。"""
    out: dict = {}
    for p in parts:
        for i in p.ids:
            out[i] = max(out.get(i, 0), p.need)
    return out
