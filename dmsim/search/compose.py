"""合成手: 起点（攻撃など）から、そのターン内の自分の選択（誘発順・モード・置換・対象）を全列挙し、
次に自分が攻撃などを選べる局面までを「1手」にまとめる。盤面が起点と同じ形に戻る手は回帰（ループ候補）。

骨格は2つに分ける。戻る部分は場の札の名前（タップ・出たターンは見ない。復活した札は未タップで戻るため）。
進む部分は各ゾーンの枚数で、差分Δとして記録する。"""
from __future__ import annotations
from collections import Counter
from itertools import combinations

END_KINDS = ("attack", "main", "charge")


def core(eng, p: int = 0) -> tuple:
    s = eng.s
    return tuple(sorted(s.cards[c].defn for c in eng.bz_tops() if s.cards[c].controller == p))


def kinds(eng, z: str, p: int = 0) -> frozenset:
    """ゾーンにある札の種類の集合（枚数は見ない）。墓地・手札に必要な札が残っているかの判定に使う。"""
    return frozenset(eng.s.cards[c].defn for c in eng.zlist(z, p))


def counts(eng, p: int = 0) -> dict[str, int]:
    return {z: len(eng.zlist(z, p)) for z in ("deck", "graveyard", "hand", "mana", "shield")}


def _pick_default(d):
    return [i for i in range(max(d["min"], 0))]


def _subsets(options: list, k: int, cap: int) -> list[list[int]]:
    """複数枚を選ぶ点の候補。選ぶ札の名前の多重集合が同じ選び方は1つにまとめる（同名の札や、結果が同じ選び方を区別しない）。
    それでも cap を超える時は等間隔に間引く。札の名前や効果の名前はコードに書かない（key の札名部分だけを見る）。"""
    names = [o["key"].rsplit(":", 1)[0] for o in options]
    seen, out = set(), []
    for c in combinations(range(len(options)), k):
        sig = tuple(sorted(names[i] for i in c))
        if sig not in seen:
            seen.add(sig)
            out.append(list(c))
    if len(out) <= cap:
        return out
    step = len(out) / cap
    return [out[int(i * step)] for i in range(cap)]


def enumerate_moves(eng, origin_key: str, *, player: int = 0, max_nodes: int = 3000, max_depth: int = 60,
                    max_subsets: int = 12):
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
        elif d["min"] == d["max"] and 1 < d["min"] < n:
            ans = _subsets(d["options"], d["min"], max_subsets)   # 複数枚を選ぶ点は、名前の多重集合ごとに1つへまとめて展開
        else:
            ans = [list(range(k))]
        for a in ans:
            c = e.clone()
            c.answer(a)
            rec(c, keys + [(d["kind"], [d["options"][i]["key"] for i in a])], depth + 1)

    rec(start, [], 0)
    return moves, nodes[0]


def replay(eng, origin_key: str, keys: list, *, player: int = 0):
    """記録した選択列を、選択肢の key で同じ順に再生する。途中で key が無ければ None。成功なら（終わりの局面, 終了種別）。"""
    e = eng.clone()
    d = e.advance()
    ks = [o["key"] for o in d["options"]]
    if d["kind"] != "attack" or origin_key not in ks:
        return None
    e.answer([ks.index(origin_key)])
    i = 0
    while True:
        d = e.advance()
        if d is None or e.s.result:
            return e, "result"
        if d["player"] != player:
            e.answer([0]); continue
        if d["kind"] in END_KINDS:
            return (e, d["kind"]) if i == len(keys) else None
        if i >= len(keys):
            return None
        kind, want = keys[i]
        have = [o["key"] for o in d["options"]]
        if kind != d["kind"] or any(w not in have for w in want):
            return None
        e.answer([have.index(w) for w in want]); i += 1


def laps(eng, origin_key: str, keys: list, *, player: int = 0, limit: int = 40):
    """同じ手を繰り返し再生して、何周できるか数える。各周の枚数も返す。"""
    seq, cur = [], eng
    for _ in range(limit):
        r = replay(cur, origin_key, keys, player=player)
        if r is None or r[1] != "attack":
            break
        cur = r[0]
        seq.append(counts(cur, player))
    return len(seq), seq


def chain(eng, origin_key: str, *, player: int = 0, laps_max: int = 8, max_nodes: int = 1500, tries: int = 6):
    """周ごとに合成手を作り直して回帰を続ける（深さ優先。ある周の候補から次の周が作れなければ、同じ周の別の候補に戻る）。
    各周は「場の札の名前が起点と同じ・墓地に起点の札の種類が残る・同じ攻撃をもう一度選べる」手。
    候補は枚数の組（山札, 墓地）ごとに1つ、山札が多く残る順に最大 tries 個試す。戻り: 最も長く続いた周ごとの (山札, 墓地, 手の長さ)。"""
    c0, g0 = core(eng, player), kinds(eng, "graveyard", player)
    best: list = []

    def rec(cur, hist):
        nonlocal best
        if len(hist) > len(best):
            best = list(hist)
        if len(hist) >= laps_max:
            return True
        mv, _n = enumerate_moves(cur, origin_key, player=player, max_nodes=max_nodes)
        good = [m for m in mv if m.get("again") and m["core"] == c0 and kinds(m["eng"], "graveyard", player) >= g0]
        seen, cands = set(), []
        for m in sorted(good, key=lambda m: (-m["counts"]["deck"], len(m["keys"]))):
            sig = (m["counts"]["deck"], m["counts"]["graveyard"])
            if sig not in seen:
                seen.add(sig); cands.append(m)
        for m in cands[:tries]:
            if rec(m["eng"], hist + [(m["counts"]["deck"], m["counts"]["graveyard"], len(m["keys"]))]):
                return True
        return False

    rec(eng, [])
    return best


def find_loop(eng, origin_key: str, *, player: int = 0, laps_max: int = 6, max_nodes: int = 2500, tries: int = 6) -> dict:
    """合成手の連鎖でループを探し、判定をまとめて返す。
    kind: none（1周も回帰しない） / finite（山札が毎周減る。見積り周回数つき） / infinite（山札が減らない周が続く）。
    1周でも回帰が見つかれば none にはしない（有限ループも検出する）。"""
    d0 = counts(eng, player)["deck"]
    hist = chain(eng, origin_key, player=player, laps_max=laps_max, max_nodes=max_nodes, tries=tries)
    if not hist:
        return {"kind": "none", "laps": 0, "deltas": [], "deck_start": d0}
    decks = [d0] + [h[0] for h in hist]
    deltas = [b - a for a, b in zip(decks, decks[1:])]
    tail = deltas[1:] or deltas      # 1周目は準備の分岐が混ざるので、2周目以降の差分で見積もる
    loss = -min(tail)
    if all(x >= 0 for x in tail) and len(hist) >= 2:
        kind, est = "infinite", None
    elif loss > 0:
        kind, est = "finite", len(hist) + max(0, decks[-1] // loss)
    else:
        kind, est = "finite", len(hist)
    return {"kind": kind, "laps": len(hist), "deltas": deltas, "deck_start": d0, "est_laps": est,
            "decks": decks, "last": hist[-1]}
