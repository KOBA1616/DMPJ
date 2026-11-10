"""ノブの自動チューニング（(1+λ)進化戦略＋同一シード対比較＋新規シードでの再確認）。LLM・課金なし。

autofix.loop は「診断が指す1つのノブを2倍にする」貪欲法。こちらは診断に頼らず、複数ノブを同時に
乱択変異して探る。守る規則は loop.py と同じ（FAIRのみ・Vは足切りに使わない・holdout不使用）。
過学習を避けるため、調整用シードで有意に良い候補だけを、別シード（confirm）で再測定して有意差が
再現した時だけ採用する。測定は measure(Knobs, seeds)->dict で渡す（seeds ごとに結果が決まること）。"""
from __future__ import annotations

import random
from dataclasses import replace

from ..eval.stats import paired_diff
from .loop import Knobs, Rule

# (下限, 上限, 対数刻みか, 整数か)
SPACE = {
    "coef": (2.0, 100.0, True, False),
    "gy_mult": (0.5, 8.0, True, False),
    "budget": (50, 1600, True, True),
    "finish_mult": (0.0, 8.0, False, False),
    "n_det": (2, 16, True, True),
    "lookahead": (0, 2, False, True),
    "prep_bonus": (0.0, 80.0, False, False),
}


def mutate(k: Knobs, rng: random.Random, n_change: int = 2, space: dict = SPACE) -> Knobs:
    """ノブを n_change 個だけ動かす。対数刻みは±倍、線形は範囲の±20%。範囲内に丸める。"""
    ch = {}
    for name in rng.sample(sorted(space), min(n_change, len(space))):
        lo, hi, log, integer = space[name]
        v = float(getattr(k, name))
        if log:
            v = max(v, lo) * (2.0 ** rng.uniform(-1.0, 1.0))
        else:
            v += (hi - lo) * rng.uniform(-0.2, 0.2)
        v = min(hi, max(lo, v))
        ch[name] = int(round(v)) if integer else round(v, 3)
    return replace(k, **ch)


def _vec(xs, rule: Rule):
    return [-(float(rule.turn + 1) if x is None else float(x)) for x in xs]


def _remaining(shield, deck):
    """相手があと何割で負けるか（0=負け確定、1=手つかず）。勝ち筋（盾を割る／山札切れ）の近い方で測る。"""
    if shield is None or deck is None:
        return None
    return min(1.0, min(shield / 5.0, deck / 30.0))


def _score(m: dict, rule: Rule, w_board: float = 0.3, w_cards: float = 0.1, w_prog: float = 0.4) -> list[float]:
    """局ごとの滑らかな点（高いほど良い）。キルの早さが主で、盤面・部品の到達の早さを小さく加える
    （キルが出ない間も改善が見えるようにするため。段階指標は順位付けの補助で、足切りには使わない）。"""
    s = _vec(m["kill"], rule)
    for key, w in (("board", w_board), ("cards", w_cards)):
        if m.get(key) and len(m[key]) == len(s):
            s = [a + w * b for a, b in zip(s, _vec(m[key], rule))]
    if m.get("opp_shield") and m.get("opp_deck") and len(m["opp_shield"]) == len(s):
        # 連続の進捗（0/1に潰れた指標でも差が出るように）。最大でも w_prog ターン分。キルの早さが常に主。
        rem = [_remaining(a, b) for a, b in zip(m["opp_shield"], m["opp_deck"])]
        s = [x + w_prog * (1.0 - (r if r is not None else 1.0)) for x, r in zip(s, rem)]
    return s


def evolve(measure, g0, mutate_fn, to_dict, tune_seeds, confirm_seeds, rule: Rule = Rule(), generations: int = 5,
           lam: int = 4, seed: int = 0, ledger=None):
    """汎用の (1+λ) 進化戦略。g は任意の遺伝子（Knobs・部品の重みベクトル等）。measure(g, seeds)->{"kill",...}。
    採用は、調整用シードで有意に改善 → 別の再確認シードでも有意に改善した時だけ。履歴を返す。"""
    if set(tune_seeds) & set(confirm_seeds):
        raise ValueError("調整用と再確認用のシードは分ける")
    rng = random.Random(seed)
    cur, hist = g0, []
    base_t = measure(cur, tune_seeds)
    base_c = None
    for g in range(generations):
        best = None
        for _ in range(lam):
            cand = mutate_fn(cur, rng)
            if cand == cur:
                continue
            r = paired_diff(_score(measure(cand, tune_seeds), rule), _score(base_t, rule), alpha=rule.alpha)
            if r["significant"] and r["diff"] > 0 and (best is None or r["diff"] > best[1]["diff"]):
                best = (cand, r)
        ent = {"gen": g, "from": to_dict(cur), "rule": rule.version}
        if best is None:
            ent["verdict"] = "no_candidate"
            hist.append(ent)
            _rec(ledger, ent)
            continue
        cand, r = best
        if base_c is None:
            base_c = measure(cur, confirm_seeds)
        mc = measure(cand, confirm_seeds)
        rc = paired_diff(_score(mc, rule), _score(base_c, rule), alpha=rule.alpha)
        ok = rc["significant"] and rc["diff"] > 0
        ent.update(cand=to_dict(cand), tune_diff=r["diff"], confirm_diff=rc["diff"], confirm_ci=rc["ci"],
                   verdict="accept" if ok else "reject_not_reproduced")
        hist.append(ent)
        _rec(ledger, ent)
        if ok:
            cur, base_t, base_c = cand, measure(cand, tune_seeds), mc
    return cur, hist


def tune(measure, k0: Knobs, tune_seeds, confirm_seeds, rule: Rule = Rule(), generations: int = 5,
         lam: int = 4, seed: int = 0, ledger=None) -> tuple[Knobs, list[dict]]:
    """ノブの進化。measure(Knobs, seeds)->{"kill":[...]}。"""
    return evolve(measure, k0, mutate, lambda k: k.__dict__, tune_seeds, confirm_seeds, rule, generations, lam, seed, ledger)


def _rec(ledger, ent):
    if ledger:
        from ..deckplan.evaluate import record
        record(ledger, ent)
