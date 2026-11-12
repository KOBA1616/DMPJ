"""診断→改善候補→対比較→採否→記録。採否は FAIR の同一シード対比較の有意差のみ。

守る規則: 検証専用(holdout)は調整に使わない／未変換カードを含むデッキは自動採用しない（候補に出すだけ）／
価値Vは足切りに使わない（順位付けの重みだけ動かす）／公平探索の評価のみ（CHEATは使わない）。"""
from __future__ import annotations

from dataclasses import dataclass, replace

from ..deckplan.evaluate import record
from ..eval.stats import paired_diff
from .diagnose import diagnose


@dataclass(frozen=True)
class Knobs:
    coef: float = 10.0          # 部品表の倍率（leaf_parts）
    gy_mult: float = 1.0        # 墓地の部品の重み倍率
    budget: int = 100           # 探索予算
    finish_mult: float = 0.0    # 締めの束（部品の同時そろい）の倍率。0 は無効
    n_det: int = 4              # 公平探索の決定化数
    lookahead: int = 0          # 複数ターン探索の先読み（dmsim/search/multiturn）
    prep_bonus: float = 0.0     # 準備札が墓地に行く加点（dmsim/search/prep）。0 は無効
    learned_mult: float = 0.0   # 経験ログから学習した価値の加点の倍率（dmsim/autofix/valuelearn）。0 は無効・順位付けのみ


@dataclass(frozen=True)
class Rule:
    version: str = "v0"
    turn: int = 4
    alpha: float = 0.05
    coef_max: float = 100.0
    budget_max: int = 1600
    n_det_max: int = 16
    lookahead_max: int = 2


def propose(stage: str, k: Knobs, rule: Rule = Rule(), hints: tuple = ()) -> list[tuple[Knobs, str]]:
    """診断の段階に応じた候補。cards（デッキ側）は自動採用しないので候補に出さない（deck_hint として報告）。"""
    out = []
    if "prep_unused" in hints and stage != "ok" and k.prep_bonus * 2 <= 80:
        nb = k.prep_bonus * 2 if k.prep_bonus else 10.0
        out.append((replace(k, prep_bonus=nb), "準備札を撃つ加点を足す" if not k.prep_bonus else "準備札の加点を2倍"))
    if stage == "board":
        if k.coef * 2 <= rule.coef_max:
            out.append((replace(k, coef=k.coef * 2), "部品倍率を2倍"))
        if k.gy_mult * 2 <= 8:
            out.append((replace(k, gy_mult=k.gy_mult * 2), "墓地の部品の重みを2倍"))
    elif stage == "finish":
        if k.finish_mult == 0.0:
            out.append((replace(k, finish_mult=1.0), "締めの束（同時そろい）を加える"))
        elif k.finish_mult * 2 <= 8:
            out.append((replace(k, finish_mult=k.finish_mult * 2), "締めの束の重みを2倍"))
        if k.budget * 2 <= rule.budget_max:
            out.append((replace(k, budget=k.budget * 2), "探索予算を2倍"))
        if k.lookahead + 1 <= rule.lookahead_max:
            out.append((replace(k, lookahead=k.lookahead + 1), "先読み(lookahead)を+1"))
        if k.n_det * 2 <= rule.n_det_max:
            out.append((replace(k, n_det=k.n_det * 2), "決定化数を2倍"))
        if k.coef * 2 <= rule.coef_max:
            out.append((replace(k, coef=k.coef * 2), "部品倍率を2倍"))
    return out


_CAP = 99


def _metric(m: dict, stage: str, rule: Rule) -> list[float]:
    """高いほど良い値のベクトル。段階ごとの指標（到達ターンは早いほど良い）。"""
    key = {"cards": "cards", "board": "board"}.get(stage, "kill")
    xs = m[key]
    return [-(float(rule.turn + 1) if x is None else float(x)) for x in xs]


def autofix(measure, k0: Knobs, combo: dict | None = None, rule: Rule = Rule(), rounds: int = 3,
            ledger: str | None = None, unverified_deck: bool = False) -> tuple[Knobs, list[dict]]:
    """measure(Knobs)->{"kill","board","cards"}（同じシード順）。採用した Knobs と履歴を返す。"""
    if combo is not None and combo.get("split") == "holdout":
        raise ValueError("検証専用(holdout)のコンボは調整に使えない")
    cur, hist = k0, []
    base = measure(cur)
    for rd in range(rounds):
        info = getattr(measure, "info", None) or {}              # 測定器が付ける補足（例: cards_ceiling=デッキだけで決まる到達率の理論上限）
        d = diagnose(base, rule.turn, ceiling=info.get("cards_ceiling") if info.get("tier") == "cold" else None)
        ent = {"round": rd, "knobs": cur.__dict__, "stage": d.stage, "cause": d.cause, "rates": d.rates, "rule": rule.version, "hints": list(d.hints), "combo": (combo or {}).get("id"), **info}
        if info.get("cards_ceiling") is not None and info.get("tier") == "exec":
            # 分解: 推定キル率 ≈ 到達層(デッキの素引き確率) × 実行層(仕込み済みからのキル率)。小さい方が律速（効く対策の置き場）
            ent["est_kill"] = round(info["cards_ceiling"] * d.rates["kill"], 4)
            ent["bottleneck"] = "ai" if d.rates["kill"] < info["cards_ceiling"] else "deck"
        if d.stage in ("cards", "deck_limited"):
            ent["deck_hint"] = {"proposer": "add_parts", "note": "デッキ側の改善が必要。deckplan.improve(kinds=(\"add_parts\", \"add_prep\"), pool=コンボのcore名) で候補を評価する。自動採用はしない"}
        cands = propose(d.stage, cur, rule, d.hints)       # cards でも準備札の加点(prep_bonus)は探索側の設定なので試す
        if d.stage == "ok" or not cands:
            hist.append(ent)
            record(ledger, ent) if ledger else None
            break
        accepted = False
        ent["tries"] = []
        for cand, why in cands:
            m = measure(cand)
            r = paired_diff(_metric(m, d.stage, rule), _metric(base, d.stage, rule), alpha=rule.alpha)
            if unverified_deck:
                verdict = "hold_unverified"
            elif r["significant"] and r["diff"] > 0:
                verdict = "accept"
            else:
                verdict = "reject" if r["significant"] else "inconclusive"
            ent["tries"].append({"change": why, "knobs": cand.__dict__, "verdict": verdict, "diff": r["diff"], "ci": r["ci"]})
            if verdict == "accept":
                cur, base, accepted = cand, m, True
                break
        hist.append(ent)
        record(ledger, ent) if ledger else None
        if not accepted:
            break
    return cur, hist


def harness_measure(rules, deck, opp_deck, seeds, spec=None, prog=None, parts_spec=None, max_turn=4, prep_ids=(), workers: int = 1, value_model=None):
    """実エンジンの測定（FAIR のみ）。workers>1 なら seeds を分けて fork で並列に回す（結果は seeds の順に連結。Claude のトークンは増えない）。parts_spec は dmsim.search.leaf_parts.PartsSpec。"""
    from ..eval.api import Candidate, EvalSettings, run_eval
    from ..search.leaf_parts import Part, PartsSpec, make_value_fn

    def measure_seeds(k: Knobs, seeds) -> dict:
        n_det = k.n_det
        vfn = None
        if parts_spec is not None:
            ps = replace(parts_spec, parts=tuple(replace(p, weight=p.weight * k.gy_mult) if p.zone == "graveyard" else p for p in parts_spec.parts), coef=k.coef)
            if k.finish_mult > 0:
                ps = replace(ps, bundles=parts_spec.bundles).with_finish(k.finish_mult) if parts_spec.finish else ps
            vfn = make_value_fn(ps)
            if k.prep_bonus > 0 and prep_ids:
                from ..search.prep import with_prep_bonus
                vfn = with_prep_bonus(vfn, prep_ids, k.prep_bonus)
            if k.learned_mult > 0 and value_model and vfn is not None:
                from .valuelearn import with_learned
                vfn = with_learned(vfn, value_model, ps, k.learned_mult)
        st = EvalSettings(opp_deck=tuple(opp_deck), progress=prog, n_det=n_det, value_fn=vfn, base_budget=k.budget, max_turn=max_turn,
                          register_fair=True, fair_lookahead=k.lookahead)
        r = run_eval(rules, Candidate(deck=tuple(deck), start_spec=spec), st, seeds)
        c = r.report["cells"][r.cell_key]
        pp = c.get("per_game_progress", [])
        out = {"kill": [g[2] for g in c["per_game"]], "board": [p[0] for p in pp], "cards": [p[1] for p in pp]}
        out["curves"] = c.get("per_game_curves", [])
        out["final"] = [(p[2] or {}).get("defs") or {} for p in pp]       # 各局の最終局面（ゾーン→{定義ID: 枚数}）。部品の自動発見用
        out["opp_deck"] = [(p[2] or {}).get("opp_deck") for p in pp]      # 各局の最終の相手の残り山札（連続指標用）
        out["opp_shield"] = [(p[2] or {}).get("opp_shield") for p in pp]  # 各局の最終の相手の残り盾（少ないほど前進。勝ちが無い時の代用指標）
        if prep_ids:                      # 各局の最終局面で墓地に行った準備札の枚数（診断の prep_unused 用）
            out["prep"] = [sum(n for d, n in ((p[2] or {}).get("gy_defs") or {}).items() if d in prep_ids) for p in pp]
        return out

    def measure(k: Knobs) -> dict:
        if workers <= 1 or len(seeds) < workers * 2:
            return measure_seeds(k, seeds)
        import multiprocessing as mp
        global _JOB
        chunks = [seeds[i::workers] for i in range(workers)]       # 飛び飛びに割ると重い局が偏らない
        _JOB = (measure_seeds, k, chunks)
        with mp.get_context("fork").Pool(workers) as pool:
            parts = pool.map(_run_chunk, range(workers))
        return _merge(parts)       # 分け方は毎回同じなので、測定間の対比較は同じ順で対応する
    return measure


_JOB = None


def _run_chunk(i):
    fn, k, chunks = _JOB
    return fn(k, chunks[i])


def _merge(parts):
    """chunk ごとの結果を chunk 順に連結する（同じ分け方なら測定間で局の対応が保たれる）。"""
    return {key: [v for part in parts for v in part[key]] for key in parts[0]}
