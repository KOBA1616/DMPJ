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


def known_from_pub(s: GameState, viewer: int) -> set[int]:
    """公開イベント記録（s.pub、T1 の Engine.note_public）から、viewer が中身を知っているカードの cid を求める。
    reveal/face_up は全員、look は viewers に含まれる場合のみ。カードが動いて gen が変わった、
    または記録後にその山札がシャッフルされた場合は無効（山札の位置知識は失われるが、中身を見たこと自体は
    cid 単位で残るため、山札に残るカードはシャッフル後も「その cid の中身」を知っているとして扱う）。"""
    out: set[int] = set()
    for r in getattr(s, "pub", []):
        if r.get("kind") not in ("reveal", "look", "face_up") or "cid" not in r:
            continue
        if viewer not in r.get("viewers", []):
            continue
        c = s.cards[r["cid"]]
        if c.gen == r["gen"]:
            out.add(r["cid"])
    return out


def hidden_cids(s: GameState, viewer: int, known: Iterable[int] = ()) -> dict[int, list[int]]:
    """持ち主 -> 見えない位置の cid 一覧（ゾーン順・先頭が上）。known に加え s.pub 由来の既知も除く。"""
    kn = set(known) | known_from_pub(s, viewer)
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
