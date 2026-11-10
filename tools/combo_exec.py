"""実行層の選別: 候補カード（1〜4枚）を手札に置き、実際に出せるマナ（ターン相当）だけ置いた局面から数ターン回し、
キル・相手の山札切れに運べるかを見る。進化元・コスト・色は実エンジンが課す（手札に直接置いても、出せない札は出ない）。
陰性対照（ランダムな札）がほぼ0で、陽性対照（既知コンボの中核）が0より大きいことを先に確かめる。
  PYTHONPATH=. python tools/combo_exec.py --control [--n 200]
"""
import argparse
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.defs import load_rules  # noqa: E402
from dmsim.scenario import build  # noqa: E402
from dmsim.solitaire import play_game  # noqa: E402


def mana_for(rules, cards, n):
    mono = {}
    for cd in rules.cards.values():
        if len(cd.civs) == 1 and cd.mana == 1 and cd.source:
            mono.setdefault(cd.civs[0], cd.id)
    civs = []
    for c in cards:
        for v in rules.cards[c].civs:
            if v in mono and v not in civs:
                civs.append(v)
    civs = civs or [next(iter(mono))]
    return [mono[civs[i % len(civs)]] for i in range(n)]


BLOCKERS = ["dm01-076", "dm01-076"]       # 蒼天の守護者ラ・ウラ・ギガ（ブロッカー）を相手の場に2体


def exec_trial(rules, cards, seed=1, mana_n=6, turns=3, budget=60, opp_deck=30, blockers=True):
    from dmsim.opponent import OppModel
    opp = OppModel(name="blockers", bz=tuple(BLOCKERS), block=True, strigger=True, play="blockers") if blockers else None
    spec = {"p0": {"hand": list(cards), "mana": mana_for(rules, cards, mana_n)},
            "p1": {"mana": ["T001"] * 6, "deck": list(BLOCKERS) if blockers else []},
            "deck_size": opp_deck, "shuffle_deck": True, "seed": seed}
    st = build(rules, spec)
    d0 = len(st.s.zones["deck"][1])
    res, eng = play_game(rules, [], [], seed, max_turn=turns, budget=budget, start=st, opp=opp)
    z = eng.s.zones
    return {"kill": res.kill_turn is not None, "opp_deck_out": d0 - len(z["deck"][1]), "opp_mana": 6 - len(z["mana"][1]),
            "kind": res.kind}


def rate(rules, cards, seeds=(1, 2, 3), **kw):
    rs = []
    for sd in seeds:
        try:
            rs.append(exec_trial(rules, cards, sd, **kw))
        except Exception:
            pass
    n = max(len(rs), 1)
    return {"kill": sum(r["kill"] for r in rs) / n, "opp_mana": sum(r["opp_mana"] for r in rs) / n, "n": len(rs)}


def control(rules, n=150, k=2, seed=1, **kw):
    ids = [i for i in rules.cards if not i.startswith(("T", "R", "L"))]
    rng = random.Random(seed)
    t0 = time.time()
    kills = 0
    for _ in range(n):
        kills += rate(rules, rng.sample(ids, k), seeds=(1,), **kw)["kill"]
    print(f"陰性対照 {n}組 (k={k}): キル率 {kills / n:.3f}  ({time.time() - t0:.0f}s)")
    return kills / n


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--mana", type=int, default=6)
    ap.add_argument("--turns", type=int, default=3)
    ap.add_argument("--cards", help="カンマ区切りID")
    a = ap.parse_args(argv)
    rules = load_rules()
    if a.control:
        control(rules, a.n, mana_n=a.mana, turns=a.turns)
    if a.cards:
        print(rate(rules, a.cards.split(","), seeds=range(1, 11), mana_n=a.mana, turns=a.turns))


if __name__ == "__main__":
    main()
