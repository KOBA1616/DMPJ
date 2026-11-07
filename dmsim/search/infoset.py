"""観測と決定化。

viewer から見えないカード = 山札・盾（両者）と相手の手札。ただし known（効果で公開・確認済みの cid）と
表向き（face_up）のカードは見える。見えない位置の「中身」を、持ち主ごとに多重集合から並べ直す。
真の順序・中身に依存しないので、同じ観測なら同じ決定化の分布になる（漏れの検出テスト用）。
"""
from __future__ import annotations

import random
from collections.abc import Iterable

from ..state import GameState

HIDDEN_ZONES = ("deck", "shield")   # 手札は相手のものだけ（viewer 自身の手札は見える）


def hidden_cids(s: GameState, viewer: int, known: Iterable[int] = ()) -> dict[int, list[int]]:
    """持ち主 -> 見えない位置の cid 一覧（ゾーン順・先頭が上）。"""
    kn = set(known)
    out: dict[int, list[int]] = {0: [], 1: []}
    for owner in (0, 1):
        zones = list(HIDDEN_ZONES) + (["hand"] if owner != viewer else [])
        for z in zones:
            for cid in s.zones[z][owner]:
                c = s.cards[cid]
                if cid in kn or c.face_up:
                    continue
                out[owner].append(cid)
    return out


def determinize(s: GameState, viewer: int, seed: int, known: Iterable[int] = ()) -> GameState:
    """s の複製を返す。見えない位置の中身を持ち主ごとに多重集合から並べ直す。
    乱数は state.rng ではなく seed から作る（真の乱数状態も観測外なので、複製側も seed で振り直す）。"""
    n = s.clone()
    rnd = random.Random(seed)
    for owner, cids in hidden_cids(n, viewer, known).items():
        pool = [n.cards[c].defn for c in cids]
        rnd.shuffle(pool)
        for c, d in zip(cids, pool):
            n.cards[c].defn = d
    n.rng = rnd.getrandbits(64)
    return n
