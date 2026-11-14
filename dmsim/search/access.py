"""ループの後にアクセスできる札（S3、設計書 §26）。

ループの記録（1周の増減 delta と周数 laps / limit）から、自分の山札をどこまで掘れるか（dug）と、掘った札がどのゾーンを経由して
手に入るか（via）を導き、山札の中身（デッキの構成。並びは見ない公平な見積もり）から「ループ後に使える札」の期待枚数を出す。
カード名は見ない。蓄積の種類（引く・山札から墓地・山札からマナ）は delta の向きから、そのゾーンの札が使えるかは効果データから決める。
- 手札: 常に使える（払える・唱えられる・捨てられる）。
- 墓地: その札自身が墓地から使える（墓地進化 grave_evo）か、自分の札（場・手札・山札・墓地）に「自分の墓地から場・手札へ」の効果があれば使える。
- マナ: マナとしてだけ使える（usable には入れない）。
"""
from __future__ import annotations

import json
from collections import Counter

VIA_ZONES = ("hand", "graveyard", "mana")


def _per_lap(loop: dict, me: int) -> dict[str, int]:
    out = {}
    for k, v in (loop.get("delta") or {}).items():
        z, _, who = str(k).partition(":")
        if who == str(me) and v:
            out[z] = out.get(z, 0) + int(v)
    return out


def dug_count(loop: dict, deck_left: int, me: int = 0) -> int:
    """ループで掘れる自分の山札の枚数（無限なら山札全部、有限なら 周数 × 1周の減り）。"""
    d = _per_lap(loop, me).get("deck", 0)
    if d >= 0:
        return 0
    if str(loop.get("limit")) == "inf":
        return deck_left
    laps = int(loop.get("laps", loop.get("stocked", 0)) or 0)
    return min(deck_left, laps * -d)


def via_zones(loop: dict, me: int = 0, eng=None) -> list[str]:
    """掘った札が経由するゾーン。増えたゾーン（墓地・マナ・手札）。どれも増えなければ手札を通る。
    ループの手順（eng.log の log_start〜log_end）に自分の手札から選ぶ決定（引いて捨てる）があれば、掘った札は手札も通る
    （捨てる札を選べるので、引いた札を手札に残せる）。"""
    pl = _per_lap(loop, me)
    zs = [z for z in VIA_ZONES if pl.get(z, 0) > 0]
    a, b = loop.get("log_start"), loop.get("log_end")
    if eng is not None and a is not None and b is not None and "hand" not in zs:
        if any(x.get("p") == me and x.get("kind") == "choose_cards" and any(str(k).startswith("hand:") for k in x.get("keys", ()))
               for x in eng.log[a:b]):
            zs.append("hand")
    return zs or ["hand"]


def _grave_users(rules, ids) -> list[dict]:
    """自分の墓地から場・手札へ出す・戻す効果の select（filter つき）を集める。"""
    out = []
    for i in set(ids):
        d = rules.cards.get(i)
        if d is None:
            continue
        for f in (d.faces or [d]):
            for blob in (f.abilities or [], f.spell or []):
                stack = [blob]
                while stack:
                    x = stack.pop()
                    if isinstance(x, dict):
                        sel = x.get("select") if isinstance(x.get("select"), dict) else None
                        if sel and sel.get("zone") == "graveyard" and sel.get("owner", "you") in ("you", "self") \
                                and x.get("to") in ("bz", "hand"):
                            out.append(sel)
                        stack.extend(x.values())
                    elif isinstance(x, list):
                        stack.extend(x)
    return out


def _fits(rules, cid: str, sel: dict) -> bool:
    d = rules.cards[cid]
    f = sel.get("filter") or {}
    if "types" in f and not set(f["types"]) & set(d.types):
        return False
    if "not_types" in f and set(f["not_types"]) & set(d.types):
        return False
    if "races" in f and not set(f["races"]) & set(d.races):
        return False
    if "cost_le" in f and (d.cost or 0) > f["cost_le"]:
        return False
    if "civs" in f and not set(f["civs"]) & set(d.civs):
        return False
    for k in ("cost_max", "max_cost"):
        if k in f and (d.cost or 0) > f[k]:
            return False
    if "cost" in f and isinstance(f["cost"], dict) and "<=" in f["cost"] and (d.cost or 0) > f["cost"]["<="]:
        return False
    return True


def usable_from(rules, cid: str, zone: str, users: list[dict]) -> bool:
    if zone == "hand":
        return True
    if zone == "graveyard":
        d = rules.cards[cid]
        return bool(d.grave_evo) or any(_fits(rules, cid, s) for s in users)
    return False


def access(eng, loop: dict, me: int = 0, win_ids=()) -> dict:
    """ループの後にアクセスできる札の見積もり。戻り値:
    {"dug": 掘れる枚数, "deck_left": 山札の枚数, "via": [ゾーン], "expected": {ID: 期待枚数}, "usable": {ID: [使えるゾーン]}}。
    山札の並びは見ない（中身の構成 × dug / deck_left）。"""
    s, rules = eng.s, eng.rules
    deck = [s.cards[c].defn for c in s.zones["deck"][me]]
    n = len(deck)
    dug = dug_count(loop, n, me)
    via = via_zones(loop, me, eng)
    mine = [s.cards[c].defn for z in ("bz", "hand", "graveyard", "deck") for c in s.zones[z][me]]
    users = _grave_users(rules, mine)
    comp = Counter(deck)
    frac = dug / n if n else 0.0
    usable = {}
    for i in comp:
        zs = [z for z in via if usable_from(rules, i, z, users)]
        if zs:
            usable[i] = zs
    out = {"dug": dug, "deck_left": n, "via": via, "expected": {i: round(k * frac, 3) for i, k in comp.items()},
           "usable": usable}
    dw = {i: drawout(eng, i, me) for i in win_ids if draw_win(rules, i)}
    if dw:
        out["drawout"] = dw  # ドロー置換の勝ち手段: 出す前に掘る枚数 / 出した後に引く枚数（§26.2）
    return out


def reachable(eng, loop: dict, ids, me: int = 0, need: float = 0.5) -> list[str]:
    """ids（勝ち手段など）のうち、ループで期待枚数 need 以上を掘れて、経由するゾーンから使える札。山札以外の手元にある札も含める。"""
    s = eng.s
    have = {s.cards[c].defn for z in ("hand", "bz", "graveyard") for c in s.zones[z][me]}
    a = access(eng, loop, me)
    return [i for i in ids if i in have or (a["expected"].get(i, 0) >= need and i in a["usable"])]


# --- ドロー置換の勝ち手段（設計書 §26.2）。カード名は見ず、効果データの形で読む。
def _walk(effect):
    for op in effect or []:
        yield op
        for k in ("body", "then", "else", "instead"):
            if isinstance(op.get(k), list):
                yield from _walk(op[k])


def draw_win(rules, cid: str) -> dict | None:
    """「自分が引く時、山札が k 枚なら代わりに勝つ」置換を持つ札の形。無ければ None。
    戻り値 {"k": 山札の枚数条件, "refill": [出た時に山札へ加えるゾーン], "scheduled": 相手のターンのはじめに引く枚数}。"""
    d = rules.cards.get(cid) if hasattr(rules, "cards") else None
    if d is None:
        return None
    abil = d.get("abilities", []) if isinstance(d, dict) else getattr(d, "abilities", [])
    k = None
    refill, sched = [], 0
    for a in abil:
        w = a.get("when", {})
        if a.get("kind") == "replace" and w.get("event") == "draw" and any(o.get("op") == "win" for o in _walk(a.get("instead"))):
            c = (a.get("if") or {}).get("cmp")
            k = c[2] if c and isinstance(c[0], dict) and c[0].get("count", {}).get("zone") == "deck" else 0
        elif a.get("kind") == "trigger" and w.get("event") == "move" and w.get("to") == "bz" and w.get("subject") == "self":
            refill += [o["select"]["zone"] for o in _walk(a.get("effect")) if o.get("op") == "move" and o.get("to") == "deck"
                       and isinstance(o.get("select"), dict) and o["select"].get("owner") == "you"]
        elif a.get("kind") == "trigger" and w.get("event") == "turn_start" and w.get("player") == "opp":
            sched += sum(o.get("count", 0) for o in _walk(a.get("effect")) if o.get("op") == "draw" and o.get("player") == "you"
                         and isinstance(o.get("count"), int))
    return None if k is None else {"k": k, "refill": refill, "scheduled": sched}


def grave_draws(rules, cid: str) -> int:
    """その札が墓地に置かれた時に自分が引く枚数（「どこからでも墓地に置かれた時、引く」の形）。"""
    d = rules.cards.get(cid) if hasattr(rules, "cards") else None
    abil = (d.get("abilities", []) if isinstance(d, dict) else getattr(d, "abilities", [])) if d is not None else []
    n = 0
    for a in abil:
        w = a.get("when", {})
        if a.get("kind") == "trigger" and w.get("event") == "move" and w.get("to") == "graveyard" and w.get("subject") == "self":
            n += sum(o.get("count", 0) for o in _walk(a.get("effect")) if o.get("op") == "draw" and isinstance(o.get("count"), int))
    return n


def drawout(eng, win_id: str, me: int = 0, extra_draws: int = 0) -> dict | None:
    """ドロー置換の勝ち手段を今出したとき、勝つのに引く必要がある枚数と、引ける見込み。
    need = 出た後の山札（山札 + 出た時に戻るゾーン）− k + 1。
    own_turn = 自分のターン中の追加ドロー源（手札・場の「墓地に置かれた時に引く」札の枚数 + extra_draws）。
    ok_same_turn: 自分のターン中に引き切れる。ok_next: 相手のターンのはじめの分を足せば引き切れる。
    dig_before: 出す前に山札を何枚減らせば相手のターンのはじめに引き切れるか（refill で戻る分も減らす必要がある）。"""
    rules, s = eng.rules, eng.s
    f = draw_win(rules, win_id)
    if f is None:
        return None
    deck = len(s.zones["deck"][me])
    after = deck + sum(len(s.zones[z][me]) for z in f["refill"])
    need = max(0, after - f["k"] + 1)
    under_all = {u for c in s.zones["bz"][me] for u in s.cards[c].under}
    own = extra_draws + sum(grave_draws(rules, s.cards[c].defn) for z in ("hand", "bz") for c in s.zones[z][me]
                            if c not in under_all)   # 進化元（下の札）は数えない（墓地へ置く手段が別に要る）
    # 戻す前の線（§26.3）: 勝ち手段が出るのと同時に墓地へ置かれた札の「墓地に置かれた時に引く」誘発を、出た時の戻す効果より先に解決する
    # （同時に待機した自分の誘発の順は自分で選べる、エンジンの order_pending）。同時に置かれる札の候補は場の札の下（進化元）。
    under = sorted(under_all)
    pre = max((grave_draws(rules, s.cards[u].defn) for u in under), default=0)
    need_pre = max(0, deck - f["k"] + 1)
    dig_a = max(0, need - own - f["scheduled"])
    dig_b = max(0, need_pre - pre) if pre else None
    return {"need": need, "own_turn": own, "scheduled": f["scheduled"], "ok_same_turn": own >= need,
            "ok_next": own + f["scheduled"] >= need, "need_pre": need_pre, "pre": pre,
            "ok_pre": bool(pre) and pre >= need_pre,
            "dig_before": dig_a if dig_b is None else min(dig_a, dig_b)}


def remaining(eng, win_id: str, me: int = 0) -> int | None:
    """勝ちに必要な残り（§30）。勝ち手段を出す前の今の局面で、二つの線のうち近い方の「あと何枚山札を減らせばよいか」。
    - 引き切りの線: dig_before（出た時に戻るゾーンも数える）。
    - 戻す前の線: 「墓地に置かれた時に引く」札を、勝ち手段が出るのと同時に墓地へ置ける見込みがあれば（場の下・墓地・手札にある。
      墓地の札は墓地進化などで進化元に戻せる）、山札 − k + 1 − その枚数（1回に置くのは1枚とみなす）。
    勝ち手段でない札は None。"""
    d = drawout(eng, win_id, me)
    if d is None:
        return None
    rules, s = eng.rules, eng.s
    f = draw_win(rules, win_id)
    pool = [s.cards[c].defn for z in ("bz", "graveyard", "hand") for c in s.zones[z][me]]
    pool += [s.cards[u].defn for c in s.zones["bz"][me] for u in s.cards[c].under]
    pre = 1 if any(grave_draws(rules, i) for i in pool) else 0
    line_b = max(0, len(s.zones["deck"][me]) - f["k"] + 1 - pre) if pre else None
    return d["dig_before"] if line_b is None else min(d["dig_before"], line_b)
