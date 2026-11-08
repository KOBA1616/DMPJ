"""複数の対象（コンボ×デッキ）に自動診断→改善を回す。検証専用(holdout)は自動で除外し、結果を一覧にする。"""
from __future__ import annotations

from .loop import Knobs, Rule, autofix


def run_targets(targets: list[dict], combos: dict, make_measure, rule: Rule = Rule(), rounds: int = 3,
                ledger: str | None = None) -> list[dict]:
    """targets: [{combo, deck, ...}]。make_measure(target)->measure。戻り値は対象ごとの {target, final, stage, skipped}。"""
    out = []
    for t in targets:
        c = combos.get(t["combo"])
        if c is None:
            out.append({"target": t, "skipped": "未知のコンボ"})
            continue
        if c.get("split") == "holdout":
            out.append({"target": t, "skipped": "検証専用(holdout)は調整に使わない"})
            continue
        k, hist = autofix(make_measure(t), Knobs(), c, rule, rounds, ledger)
        out.append({"target": t, "final": k.__dict__, "stage": hist[-1]["stage"], "rates": hist[-1]["rates"]})
    return out
