"""陽性対照用の「ループの入口」の開始局面（docs/combo-ruler-design.md §6 タスク1）。

data/loops/entry/<コンボ名>.json の LoopSpec を読み、source.board から開始局面を作る。
既存の仕込み局面（tools/exec_tier.exec_spec）とは別物で、日次の経路はこれを使わない。

入口局面の条件（2026-11-13 指揮役）:
- 自分の40枚はすべて実デッキの札（ダミー札を打点に使わない。山札の水増しもしない）。
- 相手は実戦的な枚数（盾5・手札5・マナ3・山札27）。相手の札はダミーだが、相手はマナチャージしかしない。
- 入口 M（LoopSpec.minimal）を満たし、ループを使うのが最善になる形（殴りでは同じターンに勝てない）。
data/loops/ の直下に置かないのは、tools/deck_fix.auto_setup が <コンボ名>*.json を拾って日次の局面が変わるため。
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import yaml

from dmsim.base.loopspec import LoopSpec, Pred

ROOT = Path("data/loops/entry")


def names(root: Path = ROOT) -> list[str]:
    return sorted(f.stem for f in root.glob("*.json"))


def load(name: str, root: Path = ROOT) -> LoopSpec:
    return LoopSpec.from_json((root / f"{name}.json").read_text(encoding="utf-8"))


def core_groups(ls: LoopSpec) -> list[dict]:
    """中核の組（docs/combo-ruler-design.md §14）。各組は {"role", "any": [{ID: 枚数}, ...]} で、any のどれか1つが揃えばその役が揃う。
    source.core がなければ、minimal のうち札の名前で指した述語を1札1組（代わりなし）として作る（従来の決め方）。"""
    if ls.source.get("core"):
        return [{"role": g.get("role", ""), "any": [dict(o) for o in g["any"]]} for g in ls.source["core"]]
    need: Counter = Counter()
    for p in ls.minimal:
        if p.owner == 0 and "name" in p.match and p.op in (">=", "=="):
            need[p.match["name"]] += p.n
    return [{"role": i, "any": [{i: k}]} for i, k in need.items()]


def core_alternatives(ls: LoopSpec) -> list[dict]:
    """中核が揃ったとみなす札の組 {ID: 枚数} の一覧（組ごとに代わりを1つずつ選んだ全組み合わせ）。どれか1つが揃えばよい。"""
    from itertools import product
    out = []
    for pick in product(*[g["any"] for g in core_groups(ls)]):
        need: Counter = Counter()
        for o in pick:
            for i, k in o.items():
                need[i] = max(need[i], k)
        out.append(dict(need))
    return out


def core_ids(ls: LoopSpec) -> list[str]:
    """中核の組に出てくる札（代わりの札も含む）。"""
    return sorted({i for g in core_groups(ls) for o in g["any"] for i in o})


def required_ids(ls: LoopSpec) -> list[str]:
    """どの代わりを選んでも要る札（取り除き試験で、抜くと到達率が落ちるはずの札）。"""
    alts = core_alternatives(ls)
    return sorted(set.intersection(*[set(a) for a in alts])) if alts else []


def deck_of(ls: LoopSpec) -> list[str]:
    return yaml.safe_load(Path(ls.source["deck"]).read_text(encoding="utf-8"))["deck"]


def entry_spec(ls: LoopSpec, seed: int = 1) -> dict:
    """scenario.build に渡す spec。自分の山札は、デッキから置いた札を除いた残り全部（シードで並びが変わる）。"""
    b = ls.source["board"]
    left = Counter(deck_of(ls))
    for ids in b["p0"].values():
        for i in ids:
            left[i] -= 1
            if left[i] < 0:
                raise ValueError(f"{ls.name}: {i} がデッキの枚数を超える")
    p0 = dict(b["p0"], deck=sorted(left.elements()))
    return {"p0": p0, "p1": b["p1"], "deck_size": b["opp_deck_total"], "deck_exact": [True, False],
            "deck_left": [None, b["opp_deck"]], "seed": seed}


def count(eng, p: Pred) -> int:
    s, rules = eng.s, eng.rules
    zones = (p.zone,) if p.zone else p.zones
    n = 0
    for z in zones:
        for c in s.zones[z][p.owner]:
            defn = s.cards[c].defn
            d = rules.cards[defn]
            m = p.match
            if "name" in m and m["name"] not in (defn, d.id):
                continue
            if "types" in m and not set(m["types"]) & set(d.types):
                continue
            if "civs" in m and not set(m["civs"]) & set(d.civs):
                continue
            if "races" in m and not set(m["races"]) & set(d.races):
                continue
            n += 1
    return n


def unmet(eng, ls: LoopSpec) -> list[Pred]:
    """入口 M のうち満たしていない述語。"""
    def ok(p):
        k = count(eng, p)
        return k >= p.n if p.op == ">=" else k <= p.n if p.op == "<=" else k == p.n
    return [p for p in ls.minimal if not ok(p)]


def build(rules, ls: LoopSpec, seed: int = 1):
    from dmsim.engine import scenario
    return scenario.build(rules, entry_spec(ls, seed), first_player=0)


# 物差しの測定（陽性対照・登録簿の検証）の標準予算。物差しが測るのは札の組で探索の速さではないので、
# 入口局面ごとの budget がこれより小さくても、この値まで上げて測る（docs/combo-ruler-design.md §15、2026-11-13 指揮役決定）。
# 日次の経路（auto_fix の予算100 など）はこの値を使わない。
RULER_BUDGET = 1500


def measure_budget(ls, budget: int | None = None) -> int:
    """物差しの測定で使う予算。budget を明示すればそれ、なければ max(入口局面の budget, RULER_BUDGET)。"""
    if budget is not None:
        return budget
    return max(int(ls.source.get("budget", 0) or 0), RULER_BUDGET)


def measure(rules, name: str, seeds, max_turn: int = 2, budget: int | None = None) -> list[dict]:
    """入口局面から play_game（相手はマナチャージだけ）を回す。budget 省略時は LoopSpec.source の既定。"""
    from dmsim.eval.lockcheck import lock_probe
    from dmsim.search.game import play_game
    ls = load(name)
    deck = deck_of(ls)
    bud = measure_budget(ls, budget)
    rows = []
    for sd in seeds:
        e = build(rules, ls, sd)
        res, _ = play_game(rules, deck, [], sd, first_player=0, max_turn=max_turn, budget=bud, start=e, lock_judge=lock_probe)
        rows.append({"seed": sd, "kill_turn": res.kill_turn, "kind": res.kind, "origin": res.origin,
                     "loops": len(res.loops), "lost": res.lost, "error": res.error})
    return rows
