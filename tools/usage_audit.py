"""全デッキ（または指定）で「撃てるのに撃たれない札」を検出する。診断と候補生成のみ（knobs.yaml は触らない）。
python tools/usage_audit.py [--deck data/decks/*.yaml ...] [--seeds 20] [--turns 3] [--fair] [--out logs/usage.json]
結果の ids は autofix の prep 加点の対象（combos.yaml の prep_ids が無いコンボの代わり）に使える。"""
import argparse
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.eval.usage import collect_usage, unused_cards  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.search.leaf_parts import load_specs, make_value_fn, parts_id_for_decks  # noqa: E402
from dmsim.eval.measure import load_deck  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", nargs="*", default=sorted(glob.glob("data/decks/*.yaml")))
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--turns", type=int, default=3)
    ap.add_argument("--budget", type=int, default=100)
    ap.add_argument("--fair", action="store_true", help="公平探索の使用率も測り、ずるいとの差(fair_gap)も見る（遅い）")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    rules, specs, report = load_rules(), load_specs(), {}
    seeds = list(range(1, a.seeds + 1))
    for p in a.deck:
        pid = parts_id_for_decks([p], "auto")
        vfn = make_value_fn(specs[pid]) if pid else None
        try:
            deck = load_deck(p)
            Engine.new_game(rules, [deck, ["T001"] * 40], 1, 0)
        except Exception as ex:                      # 未変換カードを含む等。飛ばして報告する
            report[Path(p).stem] = {"skipped": f"{type(ex).__name__}: {ex}"}
            print(Path(p).stem, "skipped:", ex)
            continue
        cheat = collect_usage(rules, deck, ["T001"] * 40, seeds, False, a.turns, a.budget, value_fn=vfn)
        fair = collect_usage(rules, deck, ["T001"] * 40, seeds, True, a.turns, a.budget, value_fn=vfn) if a.fair else cheat
        found = unused_cards(fair, cheat if a.fair else None)
        report[Path(p).stem] = {"parts": pid, "candidates": found}
        print(Path(p).stem, "parts=" + str(pid), [(x["id"], x["reason"], x["fair_rate"]) for x in found])
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
