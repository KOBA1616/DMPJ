"""合成手: 起点（攻撃など）から、そのターン内の自分の選択（誘発順・モード・置換・対象）を全列挙し、
次に自分が攻撃などを選べる局面までを「1手」にまとめる。盤面が起点と同じ形に戻る手は回帰（ループ候補）。

骨格は2つに分ける。戻る部分は場の札の名前（タップ・出たターンは見ない。復活した札は未タップで戻るため）。
進む部分は各ゾーンの枚数で、差分Δとして記録する。"""
from __future__ import annotations
from collections import Counter

END_KINDS = ("attack", "main", "charge")


def core(eng, p: int = 0) -> tuple:
    s = eng.s
    return tuple(sorted(s.cards[c].defn for c in eng.bz_tops() if s.cards[c].controller == p))


def counts(eng, p: int = 0) -> dict[str, int]:
    return {z: len(eng.zlist(z, p)) for z in ("deck", "graveyard", "hand", "mana", "shield")}


def _pick_default(d):
    return [i for i in range(max(d["min"], 0))]


def enumerate_moves(eng, origin_key: str, *, player: int = 0, max_nodes: int = 3000, max_depth: int = 60):
    """eng は player の attack 選択で待機中。origin_key の攻撃から始めて枝を全列挙する。
    戻り値: (moves, nodes)。move = {keys, core, counts, eng, end, again}。
    again は終わりの局面で同じ攻撃をもう一度選べること（回帰の必要条件。タップ・攻撃可否を見る）。"""
    moves, nodes = [], [0]
    start = eng.clone()
    d0 = start.advance()
    keys0 = [o["key"] for o in d0["options"]]
    start.answer([keys0.index(origin_key)])

    def rec(e, keys, depth):
        if nodes[0] >= max_nodes:
            return
        nodes[0] += 1
        d = e.advance()
        if d is None or e.s.result:
            moves.append({"keys": keys, "end": "result", "eng": e, "core": core(e, player), "counts": counts(e, player)})
            return
        if d["player"] != player:
            e.answer([0]); rec(e, keys, depth + 1); return
        if d["kind"] in END_KINDS or depth >= max_depth:
            again = d["kind"] == "attack" and origin_key in [o["key"] for o in d["options"]]
            moves.append({"keys": keys, "end": d["kind"], "again": again, "eng": e,
                          "core": core(e, player), "counts": counts(e, player)})
            return
        n = len(d["options"]); k = max(d["min"], 0)
        if d["min"] == d["max"] and d["min"] >= n:
            ans = [list(range(n))]
        elif d["min"] == d["max"] == 1:
            ans = [[i] for i in range(n)]
        elif d["min"] == 0 and d["max"] <= 1:
            ans = [[]] + [[i] for i in range(n)]
        else:
            ans = [list(range(k))]   # 複数枚選ぶ点は先頭から（未展開）
        for a in ans:
            c = e.clone()
            c.answer(a)
            rec(c, keys + [(d["kind"], [d["options"][i]["key"] for i in a])], depth + 1)

    rec(start, [], 0)
    return moves, nodes[0]
