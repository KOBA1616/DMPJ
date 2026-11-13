"""「揃うのに入口に届かない」局の解剖（S4 の測定を観測するだけ。既定の挙動は変えない）。

通常開幕・FAIR で eval.assemble.run_one を回し、自分の各ターン終了時に入口の述語の未達・中核札の居場所・マナ枚数・
墓地のクリーチャー数を記録する。揃ったのに入口に届かなかった局を、いちばん入口に近かったターンで分類する。
  python tools/entry_miss.py saga --deck data/decks/basebuild_saga.yaml --games 40
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

ZONES = ("hand", "graveyard", "bz", "mana", "deck", "shield")


def where(eng, me, cid_name):
    s, out = eng.s, {}
    for z in ZONES:
        k = sum(1 for c in s.zones[z][me] if cid_name in (s.cards[c].defn, eng.rules.cards[s.cards[c].defn].id))
        if k:
            out[z] = k
    return out


def classify(snap, names):
    """いちばん入口に近いターンの記録から理由を1つ決める（上から順に判定）。"""
    un = snap["unmet"]
    if all(u.startswith("bz:") for u in un):
        return "場のシャコガイルだけ未達"
    for u in un:
        nm = next((n for n in names if n in u), None)
        if nm:
            w = snap["where"][nm]
            zone = u.split(":")[0]
            if w.get("mana") and not any(w.get(z) for z in ("hand", "graveyard", "bz") if z != zone):
                if not any(w.get(z) for z in ("deck", "shield")) or zone in ("hand", "graveyard"):
                    return f"中核がマナ（{nm}）"
    if any("creature" in u or "civs" in u for u in un) and all(("creature" in u or "civs" in u or u.startswith("bz:")) for u in un):
        return "墓地・マナの枚数不足"
    return "必要札が山札・盾（引けていない）"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("entry")
    ap.add_argument("--deck")
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--by", type=int, default=4, help="揃ったターンの上限（これ以内に揃った局を分類）")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    from dmsim import load_rules
    from dmsim.eval import assemble as A
    from dmsim.eval import loop_entry as L
    rules = load_rules()
    ls = L.load(a.entry)
    deck = yaml.safe_load(Path(a.deck).read_text(encoding="utf-8"))["deck"] if a.deck else None
    names = sorted({p.match["name"] for p in ls.minimal if "name" in p.match} | {"dm22ex1-007"})
    rows, reasons = [], Counter()
    for seed in range(1, a.games + 1):
        snaps = []

        def tr(e, t):
            snaps.append({"turn": t, "unmet": [f"{q.zone or '/'.join(q.zones)}:{json.dumps(q.match, ensure_ascii=False)}>={q.n}"
                                               for q in L.unmet(e, ls)],
                          "mana": len(e.s.zones["mana"][0]), "where": {n: where(e, 0, n) for n in names}})
        r = A.run_one(rules, ls, seed, deck=deck, trace=tr)
        row = {"seed": seed, "cards_turn": r["cards_turn"], "entry_turn": r["entry_turn"], "kind": r["res"].kind,
               "win_turn": r["verdict"].stage2.win_turn, "error": r["res"].error}
        if r["cards_turn"] is not None and r["cards_turn"] <= a.by and r["entry_turn"] is None:
            best = min((s for s in snaps if s["turn"] >= r["cards_turn"]), key=lambda s: (len(s["unmet"]), -s["turn"]))
            row["best"] = best
            row["reason"] = classify(best, names)
            reasons[row["reason"]] += 1
        rows.append(row)
        print(seed, row.get("reason"), row.get("best", {}).get("unmet"), flush=True)
    out = {"entry": a.entry, "deck": a.deck, "games": a.games, "reasons": dict(reasons), "rows": rows}
    if a.out:
        Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out["reasons"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
