"""複数の対象（コンボ×デッキ）に自動診断→改善を回す。検証専用(holdout)は自動で除外し、結果を一覧にする。"""
from __future__ import annotations

from pathlib import Path

import yaml

from .loop import Knobs, Rule, autofix


def run_targets(targets: list[dict], combos: dict, make_measure, rule: Rule = Rule(), rounds: int = 3,
                ledger: str | None = None, store: str | None = None) -> list[dict]:
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
        k, hist = autofix(make_measure(t), k0, c, rule, rounds, ledger)
        if store and k != k0:
            saved[t["combo"]] = dict(k.__dict__)
            Path(store).write_text(yaml.safe_dump(saved, allow_unicode=True), encoding="utf-8")
        out.append({"target": t, "final": k.__dict__, "stage": hist[-1]["stage"], "rates": hist[-1]["rates"]})
    return out


def default_board(combo: dict, min_weight: float = 1.5) -> dict:
    """最小盤面Mを部品表から作る: 重みが min_weight 以上で ID 指定の部品を、ゾーンごとに全部そろえる。
    一部の部品だけを見ると診断が甘くなる（盤面が揃った＝仕込み完了と誤判定する）ので、指定がなければ全部品で見る。"""
    from ..search.leaf_parts import spec_from_combo
    board: dict = {}
    for p in spec_from_combo(combo).parts:
        if p.ids and p.weight >= min_weight:
            for i in p.ids:
                board.setdefault(p.zone, {})[i] = max(board.get(p.zone, {}).get(i, 0), p.need)
    return board


def default_need(combo: dict, min_weight: float = 1.5) -> dict:
    """cards 段階（部品が見える所にそろう）の必要カード。leaf_parts の重い部品（重み min_weight 以上・ID指定）の和集合。
    それが無い時は core 部品すべて（厳しい。天門のように core が多いコンボは cards で止まりやすい）。"""
    from ..search.leaf_parts import spec_from_combo
    need: dict = {}
    for p in spec_from_combo(combo).parts:
        if p.ids and p.weight >= min_weight:
            for i in p.ids:
                need[i] = max(need.get(i, 0), p.need)
    return need or {p["id"]: 1 for p in combo["parts"] if p.get("role") == "core" and p.get("id")}
