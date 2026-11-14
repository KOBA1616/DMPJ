"""ループの後にアクセスできる札（S3、設計書 §25）。

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


def access(eng, loop: dict, me: int = 0) -> dict:
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
    return {"dug": dug, "deck_left": n, "via": via, "expected": {i: round(k * frac, 3) for i, k in comp.items()},
            "usable": usable}


def reachable(eng, loop: dict, ids, me: int = 0, need: float = 0.5) -> list[str]:
    """ids（勝ち手段など）のうち、ループで期待枚数 need 以上を掘れて、経由するゾーンから使える札。山札以外の手元にある札も含める。"""
    s = eng.s
    have = {s.cards[c].defn for z in ("hand", "bz", "graveyard") for c in s.zones[z][me]}
    a = access(eng, loop, me)
    return [i for i in ids if i in have or (a["expected"].get(i, 0) >= need and i in a["usable"])]
