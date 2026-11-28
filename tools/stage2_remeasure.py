"""段1に届いた組の段2を、新しい定義で測り直す（2026-11-14）。

定義（ユーザー 2026-11-14）: 入口はループの最小パーツだけ。勝ち手段（フィニッシュ）はデッキにある前提で、ループ中・ループ後に引き込んで勝つ（段2）。
- 入口: 最小パーツ（場に要る札・手札に要る札）だけを置き、手札の残り・盾・マナはデッキの残りから配る。マナはそのターンの通常の枚数（T ターン目なら T 枚）。
- 入口のターン T = 2, 3, 4。自分の4ターン目の終わりまで対局する（目標は3〜4Tキル）。
- 勝ち手段: tools/gain_index.py の索引で、ループ1周の増減から引く。物差しの段2に数えられる勝ち方（特殊勝利、相手の山札を減らす）の札だけ。
- 基盤: dmsim.discovery.basebuild.build（中核＝最小パーツ＋勝ち手段を固定し、基盤を貪欲に選ぶ）。
- 対照: 勝ち手段をランダムな札（同じ枚数）にしたデッキ。
使い方: python tools/stage2_remeasure.py --out out.json [--seeds 8] [--no-basebuild]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gain_index as G  # noqa: E402
import loop_cond as C  # noqa: E402
from dmsim.base.loopspec import LoopSpec, Pred  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.discovery import basebuild as B  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from dmsim.eval.lockcheck import lock_probe  # noqa: E402
from dmsim.eval.ruler import judge  # noqa: E402
from dmsim.play_api import play_cheat as play_game  # noqa: E402

# 段1に届いた組（2026-11-14 の確認後）。spell は「つなぎの呪文」の役で、効果データから最も軽い呪文を選ぶ（名前は見ない）。
GROUPS = {
    "mathieu_berlin": {"bz": ["dm23bd6-041", "dmex13-049"], "hand_spell": True,
                       "gains": {("you", "mana"): 1, ("you", "deck"): -1}},
}


def loop_win_card(d) -> bool:
    """物差しの段2に数えられる勝ち方を持つ札: 自分の特殊勝利、または相手の山札を動かす（削る・引かせる）。"""
    if C.win_paths(d):
        return True
    for f in (getattr(d, "faces", None) or [d]):
        ops = [ab.get("effect") or [] for ab in (f.abilities or [])] + [getattr(f, "spell", None) or []]
        for eff in ops:
            for op, _ in C._all_ops_with_conds(eff):
                sel = op.get("select") or {}
                if op.get("op") == "move" and sel.get("owner") == "opp" and sel.get("zone") == "deck":
                    return True
                if op.get("op") == "draw" and op.get("player") == "opp":
                    return True
    return False


def cheapest_spell(rules, civs, raw) -> str:
    best = None
    for i, d in sorted(rules.cards.items()):
        if B._test(i) or "spell" not in d.types or "creature" in d.types or not isinstance(d.cost, int):
            continue
        if not set(d.civs) <= set(civs) or (i in raw and B.missing_effect(rules.cards[i])):
            continue
        if best is None or d.cost < rules.cards[best].cost:
            best = i
    return best


def spec_of(name, parts_bz, parts_hand) -> LoopSpec:
    minimal = [Pred(0, {"name": i}, 1, ">=", "bz") for i in parts_bz] + [Pred(0, {"name": i}, 1, ">=", "hand") for i in parts_hand]
    return LoopSpec(name=name, kind="deterministic", minimal=minimal, source={"note": "最小パーツの入口（stage2_remeasure）"})


def entry_board(rules, deck, parts_bz, parts_hand, T, seed):
    rng = random.Random(seed * 7919 + T)
    rest = list(deck)
    for i in parts_bz + parts_hand:
        rest.remove(i)
    rng.shuffle(rest)
    need = set()
    for i in parts_bz + parts_hand:
        need |= set(rules.cards[i].civs)
    mana = []
    for c in sorted(need):                         # マナはそのターンの通常の枚数。まず中核の文明を1枚ずつ
        for i in rest:
            if c in rules.cards[i].civs and len(mana) < T:
                mana.append(i)
                rest.remove(i)
                break
    while len(mana) < T:
        mana.append(rest.pop())
    hand = list(parts_hand)
    while len(hand) < 5:
        hand.append(rest.pop())
    shield = [rest.pop() for _ in range(5)]
    p0 = {"bz": list(parts_bz), "hand": hand, "mana": mana, "shield": shield, "graveyard": [], "deck": sorted(rest)}
    return {"p0": p0, "p1": {"hand": ["T001"] * 5, "mana": ["T001"] * max(0, T - 1)}, "deck_size": 40,
            "deck_exact": [True, False], "deck_left": [None, 40 - 10 - max(0, T - 1)], "seed": seed}


def measure(rules, deck, parts_bz, parts_hand, T, seeds, budget):
    rows = []
    for sd in seeds:
        spec = entry_board(rules, deck, parts_bz, parts_hand, T, sd)
        try:
            e = scenario.build(rules, spec, first_player=0)
            res, eng = play_game(rules, deck, [], sd, first_player=0, max_turn=5 - T, budget=budget, start=e, lock_judge=lock_probe)
            v = judge(res, eng)
            rows.append({"seed": sd, "stage1": v.stage1.ok, "stage2": v.stage2.ok, "via": v.stage2.via, "kind": res.kind,
                         "win_turn": res.kill_turn, "laps": v.stage1.n, "error": res.error})
        except Exception as ex:
            rows.append({"seed": sd, "stage1": False, "stage2": False, "via": None, "kind": None, "win_turn": None, "laps": 0,
                         "error": f"{type(ex).__name__}: {ex}"[:200]})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--budget", type=int, default=1500)
    ap.add_argument("--finishers", type=int, default=3)
    ap.add_argument("--no-basebuild", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    rules = load_rules()
    raw = B._raw_cards(rules)
    idx = G.build(rules)
    out = {}
    for name, g in GROUPS.items():
        civs = set()
        for i in g["bz"]:
            civs |= set(rules.cards[i].civs)
        hand = [cheapest_spell(rules, civs, raw)] if g.get("hand_spell") else []
        hits = [h for h in G.lookup(idx, g["gains"], rules, top=0) if loop_win_card(rules.cards[h["id"]])
                and not (h["id"] in raw and B.missing_effect(rules.cards[h["id"]]))]
        fin = [h["id"] for h in hits[:a.finishers]]
        rng = random.Random(20261114)
        pool = sorted(i for i, d in rules.cards.items() if not B._test(i) and isinstance(d.cost, int) and i not in fin
                      and i not in g["bz"] + hand and not (i in raw and B.missing_effect(rules.cards[i])))
        rnd = rng.sample(pool, len(fin))
        ls = spec_of(name, g["bz"], hand)
        res = {"bz": g["bz"], "hand": hand, "finishers": [{"id": i, "name": rules.cards[i].name, "why": h["why"]}
                                                           for i, h in zip(fin, hits)],
               "random": [{"id": i, "name": rules.cards[i].name} for i in rnd], "decks": {}, "rows": {}}
        for label, extra in (("index", fin), ("random", rnd)):
            core = {i: B.COPIES for i in g["bz"] + hand + extra}
            if a.no_basebuild:
                deck = B.base_deck(core, B.fillers(rules, core, raw))
                added = []
            else:
                b = B.build(rules, core, ls, log=lambda m: print(m, flush=True))
                deck, added = b.deck, b.added
            res["decks"][label] = {"deck": deck, "added": added}
            for T in (2, 3, 4):
                rows = measure(rules, deck, g["bz"], hand, T, range(1, a.seeds + 1), a.budget)
                res["rows"][f"{label}:T{T}"] = rows
                print(f"{name} {label} T{T}: 段1 {sum(r['stage1'] for r in rows)}/{len(rows)} 段2 {sum(r['stage2'] for r in rows)}/{len(rows)} "
                      f"勝ち方 {dict(Counter(r['via'] for r in rows if r['via']))} 誤り {sum(1 for r in rows if r['error'])} {time.time()-t0:.0f}s", flush=True)
        out[name] = res
    Path(a.out).write_text(json.dumps({"groups": out, "seconds": round(time.time() - t0)}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
