"""「部品がそろう確率」と「そろった局面から勝てるか」を切り分ける診断。
  python tools/eval_reach.py reach --need A:2:1 F:2:1 N:2:1 O:2:2 W:4:1 --turns 4 5 6 8
      ラベル:デッキ内の枚数:必要枚数。山札の最初の5枚=盾、次の5枚=手札、以後1ターン1枚。先攻（--second で後攻）。
      「全部そろう」確率の上限（マナ・色・順序は無視）。これが小さければ、探索が正しくてもキルは出ない。
  python tools/eval_reach.py start SPEC.yaml [--budget 3000] [--seeds 4] [--turns 1]
      dmsim.scenario の局面から1人回しし、キル・ループ・相手の山札の残りを出す（調整用の局面で使う）。"""
import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def reach(parts, turns, second=False, trials=40000, deck_size=40, seed=1):
    rng = random.Random(seed)
    deck = [lab for lab, n, _ in parts for _ in range(n)]
    deck += ["-"] * (deck_size - len(deck))
    need = {lab: k for lab, _, k in parts}
    out = {}
    for t in turns:
        seen = 5 + (t if second else t - 1)          # 手札5 + ドロー（先攻は1ターン目に引かない）
        hit = 0
        for _ in range(trials):
            rng.shuffle(deck)
            h = deck[5:5 + seen]                    # 先頭5枚は盾
            hit += all(h.count(lab) >= k for lab, k in need.items())
        out[t] = hit / trials
    return out


def start(spec_path, budget, seeds, turns):
    import yaml
    from dmsim.cards.defs import load_rules
    from dmsim.engine.scenario import build
    from dmsim.search.game import play_game
    rules = load_rules()
    spec = yaml.safe_load(Path(spec_path).read_text(encoding="utf-8"))
    for seed in range(1, seeds + 1):
        spec["seed"] = seed
        res, eng = play_game(rules, [], [], seed, start=build(rules, spec), max_turn=turns, budget=budget, lock_rounds=0)
        z = lambda n, p: len(eng.zlist(n, p))
        print(f"seed={seed} kind={res.kind} kill_turn={res.kill_turn} loops={[l['kind'] for l in res.loops]} nodes={res.nodes} "
              f"opp_deck={z('deck', 1)} opp_shield={z('shield', 1)} my_mana={z('mana', 0)} my_deck={z('deck', 0)}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("reach")
    r.add_argument("--need", nargs="+", required=True)
    r.add_argument("--turns", type=int, nargs="+", default=[4, 5, 6, 8])
    r.add_argument("--second", action="store_true")
    s = sub.add_parser("start")
    s.add_argument("spec")
    s.add_argument("--budget", type=int, default=3000)
    s.add_argument("--seeds", type=int, default=4)
    s.add_argument("--turns", type=int, default=1)
    a = ap.parse_args(argv)
    if a.cmd == "reach":
        parts = [(x.split(":")[0], int(x.split(":")[1]), int(x.split(":")[2])) for x in a.need]
        for t, p in reach(parts, a.turns, a.second).items():
            print(f"T{t}: {p:.4f}")
    else:
        start(a.spec, a.budget, a.seeds, a.turns)


if __name__ == "__main__":
    main()
