"""通常開幕から「揃う」（新旧の数え方）・経路の段・入口・段2・3〜4T勝ちを測る（測定だけ。既定の挙動は変えない）。
  python tools/route_macro_run.py saga --deck data/decks/basebuild_saga.yaml --route saga_v2 --keep --games 40 --out x.json
  --control: 中核（tools/basebuild.core_of）を4枚ずつ、残りを基盤選びのチャージ札（効果なしのクリーチャー）で埋めた対照。
  --macro on/off: 登録簿の手（既定は search.macro の既定）。--route を渡すと部分点・減点（away=40）つきの目標で回す。
  --keep: 経路に要る札をマナ・捨て札で後回し（search.route_goal.keep_hand、§21）。--log ROUTE: 段の到達の記録だけ。
"""
from __future__ import annotations

import argparse
import os

# 経路つきの測定では、勝ち手段の引き切り点（§30）と予算切れ後の先読み（§31）を既定で有効にする（0 を渡せば無効）。
# 日次の数字や経路を使わない測定（陽性対照・登録簿）には効かない
os.environ.setdefault("DMSIM_DRAWOUT", "1")
os.environ.setdefault("DMSIM_ROLLOUT_LOOKAHEAD", "1")
import json
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))


DEFAULT_DECK = {"saga": "data/decks/saga_user_v1.yaml"}   # --deck を省いたときのデッキ（ユーザー指定のレシピ）


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
    ap.add_argument("--opp-level", type=int, default=0, help="相手の抵抗の段階（1=S・トリガー入りの相手）")
    a = ap.parse_args(argv)
    from dmsim import load_rules
    from dmsim.eval import loop_entry as L
    from dmsim.eval.api import measure_assembly
    from dmsim.discovery import basebuild as B
    from dmsim.search import macro
    from basebuild import core_of
    rules = load_rules()
    ls = L.load(a.entry)
    if not a.deck and a.entry.split("_")[0] == "saga":
        a.deck = DEFAULT_DECK["saga"]   # サガの測定の既定はユーザー指定のレシピ（2026-11-16）
    deck = yaml.safe_load(Path(a.deck).read_text(encoding="utf-8"))["deck"] if a.deck else L.deck_of(ls)
    if a.control:
        core = core_of(a.entry.split("_")[0])
        deck = B.base_deck(core, B.fillers(rules, core))
    if a.macro:
        macro.enable(a.macro == "on")
    from dmsim.search.route_goal import drawout_on
    opts = {"partial": True, "away": a.away, "keep_hand": a.keep, "ratchet": drawout_on()} if a.route else None
    rows = []
    why = None
    if os.environ.get("DMSIM_WHY") == "1":     # 診断用（tools/why_hook.py）。見るだけで結果は変えない
        import why_hook as why
        from collections import Counter
        why.install([c for c, n in Counter(deck).items() if n >= 4])
    for s in range(a.start, a.start + a.games):
        if why:
            why.reset()
        r = measure_assembly(rules, a.entry, deck, [s], route=a.route, route_log=a.log, route_opts=opts, opp_level=a.opp_level)[0]
        if why:
            r["why"] = why.result()
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
