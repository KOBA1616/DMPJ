"""蓄積から勝ち手段を引く索引（2026-11-14）。

ループ1周で増える（減る）もの、例えば {("you","mana"): +1, ("opp","bz"): -1, ("you","deck"): -1} を入力に、
それを勝ちに変えられる札を効果データから引く。カード名は見ない。
索引の鍵（owner, zone, 向き）と、札がその鍵を使う理由:
- ("you","mana","+") 増えたマナで払う大きな効果: コスト6以上で、相手の山札か盾を動かす・自分の特殊勝利を持つ札
- ("opp","bz","-") 相手の場が空であることを使う攻撃: スピードアタッカーで2枚以上ブレイクする札、相手の場の数を条件にする勝ち・打点
- ("you","deck","-") 自分の山札切れを勝ちに変える効果: 自分の山札の枚数を条件にする特殊勝利
- 一般: 特殊勝利や相手の山札・盾を動かす効果の条件が count {zone, owner} を読むなら、その向きの鍵（>= なら +、<= / == なら -）
使い方: python -m dmsim.discovery.gain_index --gain you:mana:+ --gain opp:bz:- --gain you:deck:- [--top 20]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict

from . import loop_cond as C

BREAKS = {"double_breaker": 2, "triple_breaker": 3, "quad_breaker": 4, "world_breaker": 5, "powered_breaker": 2}


def _faces(d):
    return list(getattr(d, "faces", None) or []) or [d]


def _hits_opp(ops) -> bool:
    for op, _ in C._all_ops_with_conds(ops or []):
        if op.get("op") == "move":
            sel = op.get("select") or {}
            if sel.get("owner") == "opp" and sel.get("zone") in ("deck", "shield"):
                return True
        if op.get("op") == "draw" and op.get("player") == "opp":
            return True
    return False


def _count_keys(cond, out, why):
    if not isinstance(cond, dict):
        return
    for k in ("all", "any"):
        for x in cond.get(k) or []:
            _count_keys(x, out, why)
    if "not" in cond:
        _count_keys(cond["not"], out, why)
    if "cmp" in cond:
        a, op, n = cond["cmp"]
        if isinstance(a, dict) and isinstance(a.get("count"), dict):
            sp = a["count"]
            z = sp.get("zone")
            if isinstance(z, str):
                sign = "+" if op in (">=", ">") else "-"
                out.add(((sp.get("owner", "you"), z, sign), why))


def keys_of(d) -> set:
    """札が勝ちに変えられる蓄積の鍵の集合 {((owner, zone, sign), 理由)}。"""
    out = set()
    wins = C.win_paths(d)
    for p in wins:
        for c in p["conds"]:
            _count_keys(c, out, "特殊勝利の条件")
    hits = False
    for f in _faces(d):
        for ab in f.abilities or []:
            eff = ab.get("effect") or []
            if _hits_opp(eff):
                hits = True
                for op, conds in C._all_ops_with_conds(eff):
                    for c in conds + ((ab.get("if"),) if ab.get("if") else ()):
                        _count_keys(c, out, "相手の山札・盾を動かす効果の条件")
        if _hits_opp(getattr(f, "spell", None)):
            hits = True
    cost = min((f.cost for f in _faces(d) if isinstance(f.cost, int)), default=None)
    if cost is not None and cost >= 6 and (hits or wins):
        out.add((("you", "mana", "+"), f"コスト{cost}の勝ち筋（増えたマナで払う）"))
    kws = {ab.get("keyword") for f in _faces(d) for ab in (f.abilities or [])}
    br = max([BREAKS.get(k, 1) for k in kws if k] or [1])
    if "speed_attacker" in kws and br >= 2 and "cannot_attack_player" not in kws and "cannot_attack" not in kws:
        out.add((("opp", "bz", "-"), f"スピードアタッカー・{br}枚ブレイク（相手の場が空なら通る）"))
    return out


def build(rules) -> dict:
    idx = defaultdict(list)
    for cid, d in rules.cards.items():
        if cid.startswith("T") or d.id != cid and d.id in rules.cards:
            continue
        for key, why in keys_of(d):
            idx[key].append((cid, why))
    return idx


def lookup(idx, gains: dict, rules, top: int = 20) -> list[dict]:
    """gains: {(owner, zone): 1周の増減}。増える鍵は "+"、減る鍵は "-" で引く。複数の鍵に当たる札を先に、次にコストの低い札。"""
    hit = defaultdict(list)
    for (owner, zone), v in gains.items():
        if not v:
            continue
        for cid, why in idx.get((owner, zone, "+" if v > 0 else "-"), []):
            hit[cid].append(f"{owner}:{zone}:{'+' if v > 0 else '-'} {why}")
    rows = [{"id": c, "name": rules.cards[c].name, "cost": rules.cards[c].cost, "why": w} for c, w in hit.items()]
    rows.sort(key=lambda r: (-len(r["why"]), r["cost"] if isinstance(r["cost"], int) else 99, r["id"]))
    return rows[:top] if top else rows


def main():
    from dmsim.cards.defs import load_rules
    ap = argparse.ArgumentParser()
    ap.add_argument("--gain", action="append", default=[], help="owner:zone:+ / -")
    ap.add_argument("--top", type=int, default=20)
    a = ap.parse_args()
    rules = load_rules()
    idx = build(rules)
    gains = {}
    for g in a.gain:
        o, z, s = g.split(":")
        gains[(o, z)] = 1 if s == "+" else -1
    print(json.dumps({"sizes": {":".join(k): len(v) for k, v in sorted(idx.items())},
                      "hits": lookup(idx, gains, rules, a.top)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
