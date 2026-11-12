"""エンジン状態の読み取り専用アクセサ（疑似API v0.1 の `read` 系を Engine 直渡しで使うための薄い層）。

探索・評価・自動診断・発見は、GameState（eng.s）の中身を直接読まず、ここを通す。Rust 版エンジンへ差し替える時は、
この1ファイルの実装を差し替えるだけで済む（呼び出し側は変えない）。状態を変える操作はここに置かない（engine_api の apply / fork 等を使う）。
依存を持たない（循環 import を避けるため engine_api とは別ファイルにしてある。engine_api からも再公開する）。"""
from __future__ import annotations

from collections import Counter


def result_of(e):
    """終局なら {winner, reason, turn...}、そうでなければ None。"""
    return e.s.result


def active_of(e) -> int:
    return e.s.active


def turn_of(e) -> int:
    return e.s.turn


def pending_of(e) -> list:
    """待機中の誘発（読み取り専用として扱う）。"""
    return e.s.pending


def defn_of(e, cid) -> str:
    return e.s.cards[cid].defn


def tapped_of(e, cid) -> bool:
    return e.s.cards[cid].tapped


def zone_of(e, zone: str, p: int):
    """ゾーンの札 id の並び（読み取り専用として扱う。変更しない）。"""
    return e.s.zones[zone][p]


def defns_of(e, zone: str, p: int) -> list[str]:
    """ゾーンの札の定義 ID の並び。"""
    return [e.s.cards[c].defn for c in e.s.zones[zone][p]]


def digest_of(e) -> str:
    return e.s.digest()


def card_zone_of(e, cid) -> str:
    return e.s.cards[cid].zone


def under_of(e, cid):
    """この札の下に重ねられている札（進化元など）。"""
    return e.s.cards[cid].under


def zones_of(e) -> dict:
    """全ゾーン {zone: [[p0の札id...], [p1の札id...]]}（読み取り専用として扱う）。"""
    return e.s.zones


# ---- 状態を書き換える操作（疑似API v0.1 の追加。仕込み局面・決定化・因果記録のため。探索の熱い経路では使わない） ----

def shuffle_deck(e, p: int, rng) -> None:
    """p の山札を rng(random.Random 互換)で並べ替える。同じ rng 状態なら同じ並びになる。"""
    rng.shuffle(e.s.zones["deck"][p])


def order_zone(e, zone: str, p: int, key) -> None:
    """ゾーンの並びを key(札id) の昇順に並べ替える（安定ソート。仕込み局面の山札の並び固定用）。"""
    z = e.s.zones[zone][p]
    z[:] = sorted(z, key=key)


def state_of(e):
    """状態そのもの（不透明なハンドルとして扱う。determinize など状態を丸ごと作り直す処理に渡す）。"""
    return e.s


def inject_state(e, state) -> None:
    """状態を丸ごと差し替える（決定化した状態の注入）。"""
    e.s = state


def trace_on(e) -> None:
    e.s.trace = []


def trace_of(e):
    """誘発の因果の記録（trace_on 後に溜まる。無効なら None）。"""
    return e.s.trace


def force_hand(e, p: int, defns: list[str]) -> bool:
    """p の手札に defns の札がそろうよう、山札の同じ定義の札と入れ替える（既に手札にあるものは動かさない）。
    測定の「強制3枚開始」用。そろえられなければ False（山札に足りない）。入れ替えで手札の枚数・山札の枚数は変わらない。"""
    need = list(defns)
    hand = list(e.s.zones["hand"][p])
    keep = []
    for c in hand:
        d = e.s.cards[c].defn
        if d in need:
            need.remove(d)
            keep.append(c)
    spare = [c for c in hand if c not in keep]
    for d in need:
        src = next((c for c in e.s.zones["deck"][p] if e.s.cards[c].defn == d), None)
        if src is None or not spare:
            return False
        out = spare.pop()
        e._raw_move(out, "deck")
        e._raw_move(src, "hand")
    return True


# ---- 盤面を数える読み取り（もとは eval/stage。探索 S3 と評価 S4 の両方が使うので S2 に置く）----
# 山札・盾の中身は公開情報ではないので VISIBLE_ZONES に含めない。
VISIBLE_ZONES = ("hand", "bz", "mana", "graveyard", "shield_bz")


def zone_counts(eng, me: int, zone: str) -> Counter:
    return Counter(defn_of(eng, c) for c in eng.zlist(zone, me))


def count_matching(eng, me: int, zone: str, ids=()) -> int:
    n = 0
    for cid in eng.zlist(zone, me):
        if (ids and defn_of(eng, cid) in ids) or (not ids and "creature" in eng.chars(cid)["types"]):
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
