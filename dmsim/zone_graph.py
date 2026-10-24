"""ゾーン変換グラフ: 実カードの効果から「どのゾーンからどのゾーンへカードが動くか」を静的に取り出し、
互いに補完し合って循環する（ループになりうる）カードの組を列挙する。

人間のデッキビルダーが「手札→盤面と盤面→手札のように、ゾーンの変換を相互にするカードの組が見つかると、
大体ループになる」と見るのと同じ観点を機械でやる。結果はループ候補（部品の組）で、実際にループするかは
シミュレーション（dmsim.loop / dmsim.loop_first）で確かめる。

- バンドル: 1つの誘発能力（または呪文）。前提（どのゾーンに何が入った時か）と、効果の中のゾーン移動の一覧。
- バンドル A の移動が B の前提を満たす（A がカードを B の前提ゾーンへ動かし、B の主語に合うカードである）時、A → B。
- この有向グラフの閉路がループ候補。閉路に含まれる移動の合計がゾーンごとの収支（差分）になる。
  動的な検出（dmsim.loop）が出す差分と一致する（サガ: 山札-1・墓地+1）。
- 条件つき（if / may の中）の移動は conditional として印をつける。数えるときは「起きる」前提で足す。

  python -m dmsim.zone_graph --max-cards 2 --top 20
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

CHILD_KEYS = ("then", "else", "body")


@dataclass
class Move:
    src: str                  # 動かす前のゾーン（"bz" "graveyard" "hand" "deck" ...）
    dst: str
    ref_self: bool = False    # 自分自身を動かす
    flt: dict = field(default_factory=dict)
    conditional: bool = False
    owner: str = "you"


@dataclass
class Bundle:
    card: str                 # カードID
    name: str
    premise: str | None       # 前提: "enter:bz" など。None なら自分から起動するもの（手札から唱える等）
    subject_self: bool        # 前提の主語が自分自身か
    moves: list[Move]
    origin: str = "trigger"   # trigger / spell


def _walk(ops, cond=False):
    for op in ops:
        o = op.get("op")
        if o in ("move", "draw", "play_free", "put_under"):
            yield op, cond
        for k in CHILD_KEYS:
            if k in op:
                yield from _walk(op[k], cond or o in ("if", "may"))


def _moves_of(ops) -> list[Move]:
    out = []
    for op, cond in _walk(ops):
        o = op["op"]
        if o == "draw":
            out.append(Move("deck", "hand", conditional=cond))
        elif o == "move":
            sel = op["select"]
            ref_self = sel.get("ref") == "self"
            src = "bz" if ref_self else sel.get("zone", "?")
            out.append(Move(src, op["to"], ref_self, dict(sel.get("filter", {})), cond, sel.get("owner", "you")))
        elif o == "play_free":
            sel = op["select"]
            out.append(Move(sel.get("zone", "hand"), "bz", False, dict(sel.get("filter", {})), cond, sel.get("owner", "you")))
    return out


def bundles_of(rules) -> list[Bundle]:
    out = []
    for cd in rules.cards.values():
        faces = cd.faces or [cd]
        for f in faces:
            if f.free_if and f.is_creature():   # G・ゼロ: 手札にある間、コストなしでバトルゾーンへ（手札に入ったことが前提）
                out.append(Bundle(cd.id, cd.name, "enter:hand", True, [Move("hand", "bz", True)], origin="free"))
            for ab in f.abilities:
                w = ab.get("when") or {}
                if ab.get("kind") != "trigger":
                    continue
                subj = w.get("subject")
                if w.get("event") == "summon":   # 「出した時」（召喚・踏み倒し）はバトルゾーンに入ったこと
                    premise = "enter:bz"
                elif w.get("event") == "move" and "to" in w:
                    premise = f"enter:{w['to']}"
                else:
                    continue
                ms = _moves_of(ab.get("effect", []))
                if ms:
                    out.append(Bundle(cd.id, cd.name, premise, subj == "self", ms))
            if f.spell:
                ms = _moves_of(f.spell)
                if ms:
                    out.append(Bundle(cd.id, cd.name, None, True, ms, origin="spell"))
    return out


def _match(flt: dict, cd) -> bool:
    """移動の絞り込みが、そのカードに当てはまりうるか（式や未知の条件は通す）。"""
    if "types" in flt and not set(flt["types"]) & set(cd.types):
        return False
    if "races" in flt and not set(flt["races"]) & set(cd.races):
        return False
    if "race_has" in flt and not any(flt["race_has"] in r for r in cd.races):
        return False
    if isinstance(flt.get("cost_le"), int) and cd.cost > flt["cost_le"]:
        return False
    if "civs" in flt and not set(flt["civs"]) & set(cd.civs):
        return False
    return True


def feeds(a: Bundle, b: Bundle, rules) -> bool:
    """a の移動が b の前提を満たしうるか。"""
    if b.premise is None or not b.premise.startswith("enter:"):
        return False
    zone = b.premise.split(":", 1)[1]
    bcd = rules.cards[b.card]
    for m in a.moves:
        if m.dst != zone:
            continue
        if m.ref_self:
            if not b.subject_self or a.card == b.card:
                return True
            continue
        if not b.subject_self or _match(m.flt, bcd):
            return True
    return False


@dataclass
class Cycle:
    bundles: list[Bundle]

    @property
    def cards(self) -> list[str]:
        return sorted({b.card for b in self.bundles})

    def delta(self) -> dict[str, int]:
        d: dict[str, int] = {}
        for b in self.bundles:
            for m in b.moves:
                if m.owner == "opp":
                    continue
                d[m.src] = d.get(m.src, 0) - 1
                d[m.dst] = d.get(m.dst, 0) + 1
        return {k: v for k, v in d.items() if v}

    def conditional(self) -> bool:
        return any(m.conditional for b in self.bundles for m in b.moves)


def find_cycles(rules, max_cards: int = 2, max_len: int = 4) -> list[Cycle]:
    bs = bundles_of(rules)
    succ = {i: [j for j, b in enumerate(bs) if feeds(bs[i], b, rules)] for i in range(len(bs))}
    seen, out = set(), []

    def dfs(start, path):
        i = path[-1]
        for j in succ[i]:
            if j == start:
                key = tuple(sorted(path))
                if key not in seen:
                    seen.add(key)
                    out.append(Cycle([bs[k] for k in path]))
            elif j > start and j not in path and len(path) < max_len:
                if len({bs[k].card for k in path + [j]}) <= max_cards:
                    dfs(start, path + [j])

    for s in range(len(bs)):
        dfs(s, [s])
    out.sort(key=lambda c: (len(c.cards), len(c.bundles)))
    return out


def main(argv=None):
    import argparse

    from .defs import load_rules
    ap = argparse.ArgumentParser(description="ゾーン変換の循環（ループ候補）を列挙する")
    ap.add_argument("--max-cards", type=int, default=2)
    ap.add_argument("--max-len", type=int, default=4)
    ap.add_argument("--top", type=int, default=30)
    a = ap.parse_args(argv)
    rules = load_rules()
    cyc = find_cycles(rules, a.max_cards, a.max_len)
    for c in cyc[:a.top]:
        print(f"{' + '.join(rules.cards[x].name for x in c.cards)}  差分={c.delta()}  {'条件つき' if c.conditional() else ''}")
    print(f"{len(cyc)} 件")


if __name__ == "__main__":
    main()
