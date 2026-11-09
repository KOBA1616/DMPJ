"""deck_fix の時間予算の自動配分（トークンを使わない純Python）。
全体の時間上限（例 日次実行の7200秒）を、対象デッキごとの候補数と粗比較の局数に振り分ける。
- 前回途中で終わった／未実行のデッキを先に回す（その次は最後に回してから日の古い順）
- 重いデッキは前回の「1候補×1局あたりの所要秒」から見積もり、枠に収まるまで粗比較の局数→候補数の順に縮める
履歴は data/autofix/deckfix_times.yaml（{combo: {sec, cands, coarse_seeds, complete, last_run}}）。"""
from __future__ import annotations

from pathlib import Path

import yaml

DEFAULT_UNIT_SEC = 3.0     # 履歴が無いデッキの 1候補×1局あたりの所要秒（保守的な初期値）
MIN_SLOT_SEC = 120         # これ未満の枠しか残っていなければそのデッキは次回へ回す
SAFETY = 0.8               # 見積もりに使う枠の割合（粗比較の締め切りはこの割合の時点）


def load_history(path) -> dict:
    p = Path(path)
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}


def save_history(path, hist: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(yaml.safe_dump(hist, allow_unicode=True, sort_keys=True), encoding="utf-8")


def order_targets(names: list[str], hist: dict) -> list[str]:
    """未実行・前回途中で終わったものが先、あとは last_run の古い順。"""
    def key(n):
        h = hist.get(n)
        if not h:
            return (0, 0.0)
        return (1 if h.get("complete") else 0, float(h.get("last_run", 0.0)))
    return sorted(names, key=key)


FINE_FACTOR = 1.5          # 通常予算(200)の1局は粗比較(40)の何倍かかるかの目安（実測が少ないので控えめ）
REF_BUDGET = 40            # unit（1候補×1局あたりの秒）は粗比較の base_budget=40 に換算した値で持つ（所要時間は探索予算にほぼ比例）
MIN_BUDGET = 10


def unit_sec(h: dict | None) -> float | None:
    """履歴から 1候補×1局あたりの所要秒（REF_BUDGET 換算）。履歴が無ければ None。"""
    if h and h.get("cands") and h.get("coarse_seeds") and h.get("sec"):
        return max(0.05, h["sec"] / (h["cands"] * h["coarse_seeds"]) * REF_BUDGET / max(1, h.get("coarse_budget", REF_BUDGET)))
    return None


def probe_unit(rules, deck, opp, setup, workers: int = 1, budget: int = REF_BUDGET, n_det: int = 4) -> float:
    """1シード（先後で2局）を実測して、1候補×1局あたりの所要秒（REF_BUDGET 換算、並列を考慮）を返す。
    重いデッキ（例 knight_dmc は1局が約30秒）を履歴なしでも先に見つけるための実測。"""
    import time

    from ..eval import fair_runner
    from ..eval.harness import EvalConfig, run_eval
    from ..eval.infolevel import InfoLevel
    from .evaluate import spec_with_deck
    fair_runner.register(n_det, 0)
    kw = {"start_spec": spec_with_deck(setup, deck)} if setup else {}
    t = time.time()
    run_eval(rules, EvalConfig(decks={"d": deck}, opp_deck=opp, seeds=[1], levels=(InfoLevel.FAIR,), max_turn=4, base_budget=budget, n_det=n_det, **kw))
    return max(0.05, (time.time() - t) / max(1, workers) * REF_BUDGET / max(1, budget))


def allocate(h: dict | None, slot_sec: float, max_cands: int, max_cs: int, min_cands: int = 3, min_cs: int = 8, kinds: int = 4,
             probe: float | None = None, max_budget: int = REF_BUDGET, seeds: int = 30, top_k: int = 2, fine_budget: int = 200) -> tuple[int, int, int, int]:
    """枠 slot_sec に収まる (種類ごとの候補数, 粗比較の局数, 粗比較の探索予算, 通常予算で再比較する件数)。
    粗比較だけでなく、通常予算（既定200）の再比較（base＋上位 top_k 件 × seeds 局）の時間も先に確保する（重いデッキでは再比較が支配的）。
    重いデッキほど、まず再比較の件数、次に粗比較の局数、最後に候補数を縮める（探索予算は実測で時間にほぼ効かないので縮めない）。
    単価は 履歴と実測(probe)の大きい方（履歴なしで実測もなければ既定値）。cands は評価した候補の総数なので kinds 倍で数える。"""
    cands_u = [x for x in (unit_sec(h), probe) if x is not None]
    u1 = max(cands_u) if cands_u else DEFAULT_UNIT_SEC
    total = slot_sec * SAFETY
    fine_one = u1 * seeds * FINE_FACTOR                              # 通常予算で1デッキを seeds 局測る時間（予算にほぼ比例しないので固定倍率）
    k = top_k
    while k > 1 and (k + 1) * fine_one > total * 0.5:               # 再比較に枠の半分までしか使わない（まず件数を減らす）
        k -= 1
    budget = total - (k + 1) * fine_one
    if budget < total * 0.3:                                          # それでも粗比較の枠が足りない（極端に重い）なら再比較は次回へ回す
        k, budget = 0, total
    u = u1 * kinds
    cands, cs, b = max_cands, max_cs, max_budget
    cost = lambda: u * cands * cs                                    # 実測: base_budget を 40→10 にしても1局の時間はほとんど縮まない（knight_dmc）。予算は縮めず局数・候補数で調整する
    while cs > min_cs and cost() > budget:
        cs -= 1
    while cands > min_cands and cost() > budget:
        cands -= 1
    return cands, cs, b, k


def update(hist: dict, name: str, res: dict, cands: int, cs: int, now: float, coarse_budget: int = REF_BUDGET) -> None:
    """two_stage の結果で履歴を更新する。途中で終わった時は complete=False のままにして次回優先にする。"""
    hist[name] = {"sec": float(res.get("sec", 0.0)), "cands": int(res.get("evaluated", cands)) or cands, "coarse_seeds": cs,
                  "complete": bool(res.get("complete", True)), "last_run": now, "coarse_budget": coarse_budget}
