"""速さの上限（dmsim/eval/speed_bound.py）を候補の集まりに当てる（2026-11-13）。
- 登録簿の候補 data/registry/candidates.yaml（holdout は除く）
- 発見の層の2枚組の候補 discovery.candidates.candidate_pairs（real.yaml の全札。以前の 462 組の一覧は残っていないので作り直す）
使い方: python tools/speed_screen.py [--pairs-top N] [--measure K] > out.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dmsim.base.registry import load_candidates  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.discovery.candidates import candidate_pairs  # noqa: E402
from dmsim.eval import speed_bound as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FILLER = "T022"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs-top", type=int, default=0, help="2枚組の上位だけ（0=全部）")
    ap.add_argument("--measure", type=int, default=0, help="4T以内に届きうる組の上位K件に実測の上限を当てる")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--budget", type=int, default=500)
    a = ap.parse_args()
    rules = load_rules()
    out = {"registry": [], "pairs": {}}
    for c in load_candidates():
        if c.get("split") == "holdout":
            continue
        core = [p["id"] for p in c["core"]]
        bz = S.bz_need_of_entry(json.loads((ROOT / c["entry"]).read_text(encoding="utf-8"))["minimal"]) if c.get("entry") else None
        out["registry"].append({"id": c["id"], **S.static_bound(rules, core, bz)})
    from dmsim.discovery.candidates import card_io
    ids, broken = [], 0
    for cid in sorted(rules.cards):
        if cid.startswith("T") or rules.cards[cid].cost is None:
            continue
        try:
            card_io(rules, cid)
            ids.append(cid)
        except Exception:      # 効果データの形が card_io の想定外の札（変換済みの一部）は数えない
            broken += 1
    pairs = candidate_pairs(rules, ids, top=a.pairs_top or None)
    dist, fast = Counter(), []
    for p in pairs:
        b = S.static_bound(rules, [p["a"], p["b"]])
        t = b["turn"]
        dist["unknown" if t is None else (t if t <= 6 else ">6")] += 1
        if t is not None and t <= 4:
            fast.append({**p, "turn": t, "costs": b.get("costs")})
    out["pairs"] = {"cards": len(ids), "skipped_cards": broken, "pairs": len(pairs), "turn_dist": {str(k): v for k, v in sorted(dist.items(), key=str)},
                    "le4": len(fast), "le4_top": fast[:50]}
    if a.measure:
        meas = []
        for p in fast[:a.measure]:
            deck = [p["a"]] * 4 + [p["b"]] * 4 + [FILLER] * 32
            m = S.measured_bound(rules, deck, range(a.seeds), budget=a.budget, max_turn=4)
            meas.append({"a": p["a"], "b": p["b"], "static": p["turn"], "best_turn": m["best_turn"], "kills": m["kills"],
                         "games": m["games"], "origins": dict(Counter(r["origin"] for r in m["rows"] if r["kill_turn"]))})
        out["measured"] = meas
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
