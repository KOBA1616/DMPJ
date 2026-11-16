"""複数の対象（コンボ×デッキ）に自動診断→改善を回す。検証専用(holdout)は自動で除外し、結果を一覧にする。"""
from __future__ import annotations

from pathlib import Path

import yaml

from .loop import Knobs, Rule, autofix


def run_targets(targets: list[dict], combos: dict, make_measure, rule: Rule = Rule(), rounds: int = 3,
                ledger: str | None = None, store: str | None = None, health: str | None = None) -> list[dict]:
    """targets: [{combo, deck, ...}]。make_measure(target)->measure。戻り値は対象ごとの {target, final, stage, skipped}。"""
    out = []
    saved = (yaml.safe_load(Path(store).read_text(encoding="utf-8")) or {}) if store and Path(store).exists() else {}
    for t in targets:
        c = combos.get(t["combo"])
        if c is None:
            out.append({"target": t, "skipped": "未知のコンボ"})
            continue
        if c.get("split") == "holdout":
            out.append({"target": t, "skipped": "検証専用(holdout)は調整に使わない"})
            continue
        k0 = Knobs(**{**Knobs().__dict__, **saved.get(t["combo"], {})})      # 前回採用した設定から続ける
        if health:                                           # 1対象の例外で他の対象を止めない（記録して続ける。連続失敗は隔離）
            from .selfheal import run_phase
            ok, res = run_phase(f"diagnose:{t['combo']}", lambda: autofix(make_measure(t), k0, c, rule, rounds, ledger), health)
            if not ok:
                out.append({"target": t, "skipped": "診断が失敗（selfheal に記録）"})
                continue
            k, hist = res
        else:
            k, hist = autofix(make_measure(t), k0, c, rule, rounds, ledger)
        if store and k != k0:
            saved[t["combo"]] = dict(k.__dict__)
            Path(store).write_text(yaml.safe_dump(saved, allow_unicode=True), encoding="utf-8")
        out.append({"target": t, "final": k.__dict__, "stage": hist[-1]["stage"], "rates": hist[-1]["rates"]})
    return out


from ..search.leaf_parts import default_board, default_need  # noqa: E402,F401  旧名の再公開（実体は search.leaf_parts）
