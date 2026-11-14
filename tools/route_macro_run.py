"""通常開幕から「揃う」（新旧の数え方）・経路の段・入口・段2・3〜4T勝ちを測る（測定だけ。既定の挙動は変えない）。
  python tools/route_macro_run.py saga --deck data/decks/basebuild_saga.yaml --route saga_v2 --keep --games 40 --out x.json
  --control: 中核（tools/basebuild.core_of）を4枚ずつ、残りを基盤選びのチャージ札（効果なしのクリーチャー）で埋めた対照。
  --macro on/off: 登録簿の手（既定は search.macro の既定）。--route を渡すと部分点・減点（away=40）つきの目標で回す。
  --keep: 経路に要る札をマナ・捨て札で後回し（search.route_goal.keep_hand、§21）。--log ROUTE: 段の到達の記録だけ。
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


def summarize(rows):
    n = len(rows)

    def cnt(f):
        return sum(1 for r in rows if f(r))
    return {"games": n,
            "cards_le4": cnt(lambda r: r["cards_turn"] is not None and r["cards_turn"] <= 4),
            "cards_any_le4": cnt(lambda r: r["cards_turn_any"] is not None and r["cards_turn_any"] <= 4),
            "cards": cnt(lambda r: r["cards_turn"] is not None), "cards_any": cnt(lambda r: r["cards_turn_any"] is not None),
            "stages": dict(sorted(Counter(int(k) for r in rows for k in r["stage_turn"]).items())),
            "entry": cnt(lambda r: r["entry_turn"] is not None),
            "stage2": cnt(lambda r: r["stage2"]),
            "kill_3_4": cnt(lambda r: r["kill"] and r["win_turn"] is not None and r["win_turn"] <= 4),
            "beat": cnt(lambda r: r["beat"]),
            "wins": dict(Counter(f"{r['kind']}@{r['win_turn']}" for r in rows if r["kill"]).most_common()),
            "errors": cnt(lambda r: r["error"])}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("entry")
    ap.add_argument("--deck")
    ap.add_argument("--route")
    ap.add_argument("--log")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--macro", choices=["on", "off"])
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--away", type=float, default=40.0)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    from dmsim import load_rules
    from dmsim.eval import loop_entry as L
    from dmsim.eval.api import measure_assembly
    from dmsim.discovery import basebuild as B
    from dmsim.search import macro
    from basebuild import core_of
    rules = load_rules()
    ls = L.load(a.entry)
    deck = yaml.safe_load(Path(a.deck).read_text(encoding="utf-8"))["deck"] if a.deck else L.deck_of(ls)
    if a.control:
        core = core_of(a.entry.split("_")[0])
        deck = B.base_deck(core, B.fillers(rules, core))
    if a.macro:
        macro.enable(a.macro == "on")
    opts = {"partial": True, "away": a.away, "keep_hand": a.keep} if a.route else None
    rows = []
    for s in range(a.start, a.start + a.games):
        r = measure_assembly(rules, a.entry, deck, [s], route=a.route, route_log=a.log, route_opts=opts)[0]
        rows.append(r)
        print(json.dumps(r, ensure_ascii=False, default=str), flush=True)
    out = {"entry": a.entry, "deck": a.deck, "route": a.route, "keep": a.keep, "macro": a.macro, "control": a.control,
           "deck_list": deck, "summary": summarize(rows), "rows": rows}
    if a.out:
        Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out["summary"], ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
