"""経路の目標（部分点・減点）＋登録簿の手で、通常開幕から入口・段2・3〜4T勝ちを測る（測定だけ。既定の挙動は変えない）。
  python tools/route_macro_run.py saga --deck data/decks/basebuild_saga.yaml --route saga_v2 --games 40 --out x.json
  --control: デッキの中核（登録簿/known_combos の core）を4枚ずつ、残りを基盤選びのチャージ札（効果なしの札）で埋めた対照。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("entry")
    ap.add_argument("--deck")
    ap.add_argument("--route")
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--away", type=float, default=40.0)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    from dmsim import load_rules
    from dmsim.eval import assemble as A
    from dmsim.eval import loop_entry as L
    from dmsim.discovery import basebuild as B
    from basebuild import core_of
    rules = load_rules()
    ls = L.load(a.entry)
    deck = yaml.safe_load(Path(a.deck).read_text(encoding="utf-8"))["deck"] if a.deck else L.deck_of(ls)
    if a.control:
        core = {i: B.COPIES for i in core_of(a.entry.split("_")[0])}
        deck = B.base_deck(core, B.fillers(rules, core))
    rows = []
    for s in range(a.start, a.start + a.games):
        r = A.run_one(rules, ls, s, deck=list(deck), route=a.route,
                      route_opts={"partial": True, "away": a.away} if a.route else None)
        v = r["verdict"]
        row = {"seed": s, "entry_turn": r["entry_turn"], "cards_turn": r["cards_turn"], "stage_turn": r["stage_turn"],
               "stage1": bool(v.stage1.ok), "stage2": bool(v.stage2.ok), "via": v.stage2.via, "kill": bool(v.stage2.kill),
               "win_turn": v.stage2.win_turn, "kind": r["res"].kind, "error": r["res"].error,
               "macro_hits": getattr(r["res"], "stats", {}).get("macro_hits") if isinstance(getattr(r["res"], "stats", None), dict) else None}
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    n = len(rows)
    summ = {"games": n, "entry": sum(r["entry_turn"] is not None for r in rows),
            "entry_le4": sum(r["entry_turn"] is not None and r["entry_turn"] <= 4 for r in rows),
            "stage2": sum(r["stage2"] for r in rows),
            "kill_3_4": sum(r["kill"] and r["win_turn"] is not None and r["win_turn"] <= 4 for r in rows),
            "kill_3_4_loop": sum(r["kill"] and r["win_turn"] is not None and r["win_turn"] <= 4 and r["via"] == "loop" for r in rows),
            "wins": dict(Counter(f"{r['kind']}@{r['win_turn']}" for r in rows if r["kill"]).most_common()),
            "stage_reached": dict(Counter(k for r in rows for k in r["stage_turn"]))}
    out = {"entry": a.entry, "deck": a.deck, "route": a.route, "control": a.control, "deck_list": deck, "summary": summ, "rows": rows}
    if a.out:
        Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summ, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
