"""ベースライン分散と隠れ情報コストの測定。 python tools/eval_baseline.py [--seeds 10] [--budget 100] [--n-det 4] [--out logs/baseline.json]
default_decks(prefix) の1番目のデッキを、同一シードで FAIR と CHEAT で回し、対比較を出す。"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.defs import load_rules  # noqa: E402
from dmsim.eval import fair_runner  # noqa: E402
from dmsim.opponent import PRESETS  # noqa: E402
from dmsim.eval.harness import EvalConfig, hidden_info_cost, run_eval  # noqa: E402
from dmsim.play import default_decks  # noqa: E402
from dmsim.solitaire import load_deck  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--budget", type=int, default=100)
    ap.add_argument("--n-det", type=int, default=4)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--prefix", default="dm")
    ap.add_argument("--deck", nargs="*", help="デッキYAML(load_deck形式)。複数可。省略時は default_decks の1番目")
    ap.add_argument("--setup", help="scenario YAML（キル手前の局面から始める。例 tests/saga_setup.yaml）")
    ap.add_argument("--opp", nargs="+", default=["none"], help="相手モデル(dmsim.opponent.PRESETS)。複数で比較")
    ap.add_argument("--opp-deck", help="相手のデッキYAML。省略時は T001×40（bz/blockers/strigger を効かせるには実デッキを指定）")
    ap.add_argument("--need", nargs="*", default=[], help="必要カード DEFN[:枚数]（山札・盾以外にそろう最初のターンを測る）")
    ap.add_argument("--board", nargs="*", default=[], help="最小盤面 ゾーン:DEFN[:枚数]（例 graveyard:dm22ex2-021:1）")
    ap.add_argument("--cheat-mult", type=float, default=1.0, help="ずるい側の予算倍率（公平の決定化数に合わせると探索量がそろう）")
    ap.add_argument("--seed-from", type=int, default=1, help="開始シード（シードを分けて並列実行するため）")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    rules = load_rules()
    fair_runner.register(a.n_det)
    decks = {Path(p).stem: load_deck(p) for p in a.deck} if a.deck else {"default0": default_decks(rules, a.prefix)[0]}
    import yaml
    spec = yaml.safe_load(Path(a.setup).read_text(encoding="utf-8")) if a.setup else None
    from dmsim.eval.progress import ProgressSpec
    cards = {x.split(":")[0]: int(x.split(":")[1]) if ":" in x else 1 for x in a.need}
    board: dict = {}
    for x in a.board:
        z, d, *n = x.split(":")
        board.setdefault(z, {})[d] = int(n[0]) if n else 1
    prog = ProgressSpec(board=board, cards=cards) if (cards or board) else None
    from dmsim.eval.infolevel import InfoLevel
    cfg = EvalConfig(level_mult={InfoLevel.CHEAT: a.cheat_mult}, progress=prog, n_det=a.n_det, start_spec=spec, decks=decks, opp_deck=load_deck(a.opp_deck) if a.opp_deck else ["T001"] * 40, opps={n: PRESETS[n] for n in a.opp}, seeds=list(range(a.seed_from, a.seed_from + a.seeds)),
                     base_budget=a.budget, max_turn=a.turns)
    rep = run_eval(rules, cfg)
    rep["hidden_info_cost"] = {f"{d}|opp={o}": {t: hidden_info_cost(rep, d, t, opp=o) for t in range(1, a.turns + 1)}
                              for d in decks for o in a.opp}
    for k, c in rep["cells"].items():
        print(k, {t: [round(v["rate"], 2), [round(x, 2) for x in v["ci95"]]] for t, v in c["kill_rate_by_turn"].items()},
              f"nodes={c['mean_nodes']:.0f} sec={c['seconds']:.0f}")
    for d, ts in rep["hidden_info_cost"].items():
        for t, v in ts.items():
            print("cost", d, "turn", t, round(v["diff"], 3), [round(x, 3) for x in v["ci"]], "sig" if v["significant"] else "")
    if prog:
        from dmsim.eval.harness import hidden_info_cost_progress
        for k, c in rep["cells"].items():
            pr = c["progress"]
            print("progress", k, {m: [round(pr[m]["reach_rate"], 2), round(pr[m]["mean_turn_capped"], 2)] for m in ("board_turn", "cards_turn")},
                  "opp_shield@end", round(pr["curve_mean"][max(pr["curve_mean"])]["opp_shield"], 2))
        rep["hidden_info_cost_progress"] = {}
        for d in decks:
            for o in a.opp:
                for m in ("board_turn", "cards_turn", "opp_shield", "opp_deck"):
                    v = hidden_info_cost_progress(rep, d, m, opp=o)
                    rep["hidden_info_cost_progress"][f"{d}|opp={o}|{m}"] = v
                    print("cost_progress", d, o, m, round(v["diff"], 3), [round(x, 3) for x in v["ci"]], "sig" if v["significant"] else "")
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
