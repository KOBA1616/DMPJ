"""カードプール／デッキの静的な見積もり指標（再現性と速度の当たりをつける）。

- dig: そのカードが1回の効果で山札から触れる（引く・見る・墓地へ送る・動かす）枚数の上限。式や不明な数は 1 とみなす。
- speed: 出す・唱えるのに必要な最小ターン（コストの数だけマナが要る前提で、1ターン目から1マナずつ）。
- dig_total(deck): デッキの各カードの dig の合計 = 「全部絡めば何枚掘れるか」の上限。山札の枚数を超えれば山を掘り切れる当たり。
  実際に絡むかは見ていない（動画の『山掘り切れるデッキになりそう』という当たりの付け方に相当する）。
"""
from __future__ import annotations

from ..engine.zone_graph import CHILD_KEYS


def _n(x) -> int:
    return x if isinstance(x, int) and x > 0 else 1


def _dig_ops(ops) -> int:
    total = 0
    for op in ops:
        o = op.get("op")
        mult = _n(op.get("times")) if o == "repeat" else 1
        if o == "draw":
            total += _n(op.get("count"))
        elif o == "move":
            sel = op["select"]
            if sel.get("zone") == "deck":
                total += _n(sel.get("from_top") or sel.get("count"))
        elif o in ("choose", "mana_put", "play_free"):
            sel = op.get("select", {})
            if sel.get("zone") == "deck":
                total += _n(sel.get("from_top") or sel.get("count"))
        sub = sum(_dig_ops(op[k]) for k in CHILD_KEYS if k in op)
        total += sub * mult
    return total


def dig(cd) -> int:
    faces = cd.faces or [cd]
    best = 0
    for f in faces:
        n = _dig_ops(f.spell) + sum(_dig_ops(ab.get("effect", [])) for ab in f.abilities if ab.get("kind") == "trigger")
        best = max(best, n)
    return best


def speed(cd) -> int:
    return max(1, min([cd.cost] + [f.cost for f in cd.faces]))


def dig_total(rules, deck: list[str]) -> int:
    return sum(dig(rules.cards[c]) for c in deck)


def table(rules) -> list[dict]:
    rows = [{"id": c.id, "name": c.name, "dig": dig(c), "speed": speed(c)} for c in rules.cards.values() if c.source]
    return sorted(rows, key=lambda r: (-r["dig"], r["speed"]))


def main(argv=None):
    import argparse

    from ..cards.defs import load_rules
    from .measure import load_deck
    ap = argparse.ArgumentParser(description="カードごとの dig / speed、デッキの dig_total")
    ap.add_argument("--deck")
    ap.add_argument("--top", type=int, default=15)
    a = ap.parse_args(argv)
    rules = load_rules()
    if a.deck:
        d = load_deck(a.deck)
        print(f"{len(d)}枚 dig_total={dig_total(rules, d)}")
    for r in table(rules)[:a.top]:
        print(f"dig={r['dig']:2d} speed={r['speed']:2d} {r['name']}")


if __name__ == "__main__":
    main()
