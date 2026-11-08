"""デッキ側の自動改善: 診断（cards 段階 = 部品が揃わない）から候補デッキ（部品の追加・準備札の追加と入れ替え）を作り、
同一シード・同一先後の対比較（FAIR・N ターンキル率）で有意に良いものだけを採用する。エンジン・カードデータは読むだけ。
未変換カードを含む候補は自動採用しない（evaluate.decide が hold_unverified にする）。コアの部品は抜かない。"""
from __future__ import annotations

import time
from collections import Counter
from pathlib import Path

from . import change as C
from .evaluate import AcceptRule, decide, harness_scorer, record
from .loop import ids_of, improve
import random
from .spec import check
from .spec import CONFIRMED, UNCONVERTED, DeckProposal, Entry, save


def proposal_from_ids(rules, ids: list[str], name: str = "deck") -> DeckProposal:
    cnt = Counter(ids)
    return DeckProposal(name, [Entry(rules.cards[i].name if i in rules.cards else i, n, i) for i, n in cnt.items()],
                        source="auto")


def make_resolver(rules):
    """Entry -> (ID, 状態)。card_id があればそれ、無ければ名前から（同名は先に見つかった版）。rules.cards に無い札は UNCONVERTED。"""
    by_name: dict[str, str] = {}
    for cid, d in rules.cards.items():
        by_name.setdefault(d.name, cid)

    def resolve(e: Entry):
        cid = e.card_id or by_name.get(e.name)
        if cid is None:
            return None, UNCONVERTED
        return cid, (CONFIRMED if cid in rules.cards else UNCONVERTED)
    return resolve


def core_names(combo: dict) -> list[str]:
    return [p["name"] for p in combo["parts"] if p.get("role") == "core" and p.get("name")]


def auto_improve(rules, deck_ids: list[str], opp_ids: list[str], combo: dict, seeds: list[int], ledger,
                 rounds: int = 2, seed: int = 0, turn: int = 4, setup: dict | None = None, kinds=("add_parts", "add_prep"), n: int = 4,
                 out_dir: str | Path | None = "data/deckplans/auto", **cfg_kw) -> dict:
    """戻り値: {base, final, adopted(bool), verdicts}。採用時のみ out_dir に候補を保存する（rejected/inconclusive は保存しない）。"""
    rule = AcceptRule(turn=turn)
    base = proposal_from_ids(rules, deck_ids, f"{combo['id']}_base")
    pool = core_names(combo)
    resolver = make_resolver(rules)
    scorer = harness_scorer(rules, opp_ids, seeds, rule, setup=setup, **cfg_kw)
    t0 = time.time()
    final = base
    for k in kinds:     # 種類ごとに順に（add_prep は pool 空 = 全候補から。add_parts は core 名から）
        final = improve(final, scorer, resolver, pool if k == "add_parts" else [], ledger, kinds=(k,), rounds=rounds,
                        seed=seed, rule=rule, n=n, protect=set(pool))
    adopted = final.plan_id() != base.plan_id()
    path = None
    if adopted and out_dir:
        final.name = f"{combo['id']}_auto_{final.plan_id()}"
        final.status, final.source = "adopted", "deckplan.auto"
        final.notes = f"同一シード比較(FAIR, {turn}ターンキル率, seeds={len(seeds)})で有意に改善"
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        path = Path(out_dir) / f"{final.name}.yaml"
        save(final, path)
    return {"base": base.plan_id(), "final": final.plan_id(), "adopted": adopted, "path": str(path) if path else None,
            "sec": round(time.time() - t0, 1)}


def _rate(d: dict, turn: int) -> float:
    return sum(1.0 for v in d.values() if v is not None and v <= turn) / max(1, len(d))


def two_stage(rules, deck_ids: list[str], opp_ids: list[str], combo: dict, seeds: list[int], ledger,
              seed: int = 0, turn: int = 4, setup: dict | None = None, kinds=("add_parts", "add_prep", "cut_unused", "trim_parts"), n: int = 4,
              unused: list[str] | None = None, adds: list[str] | None = None, coarse_budget: int = 40, top_k: int = 2, workers: int = 1, out_dir: str | Path | None = "data/deckplans/auto") -> dict:
    """2段階: ①低い base_budget で全候補を同一シードで粗く比較 → ②粗い差が正の上位 top_k 件だけ通常予算で再比較し、
    有意に良ければ採用（採否は evaluate.decide のみ）。未変換カードを含む候補は粗比較にも回さない。"""
    rule = AcceptRule(turn=turn)
    base = proposal_from_ids(rules, deck_ids, f"{combo['id']}_base")
    pool, resolver, rng = core_names(combo), make_resolver(rules), random.Random(seed)
    mk = lambda **kw: harness_scorer(rules, opp_ids, seeds, rule, setup=setup, workers=workers, **kw)
    coarse, fine = mk(base_budget=coarse_budget), mk()
    cands = []
    for k in kinds:
        for ch in C.PROPOSERS[k](base, rng, pool if k in ("add_parts", "trim_parts") else [], n=n, protect=set(pool),
                                 unused=unused, adds=adds):
            try:
                cand = C.apply(base, ch)
            except ValueError:
                continue
            st = check(cand, resolver)
            if st["issues"] or st["unverified"]:
                record(ledger, {"stage": "skip", "cand": cand.plan_id(), "change": ch.ops, "why": st["issues"] or "unverified"})
                continue
            cands.append((ch, cand))
    t0 = time.time()
    cbase = coarse(ids_of(base, resolver))
    ranked = []
    for ch, cand in cands:
        diff = _rate(coarse(ids_of(cand, resolver)), turn) - _rate(cbase, turn)
        record(ledger, {"stage": "coarse", "cand": cand.plan_id(), "change": ch.ops, "reason": ch.reason, "diff": diff, "budget": coarse_budget})
        if diff > 0:
            ranked.append((diff, ch, cand))
    ranked.sort(key=lambda x: -x[0])
    final, best = base, None
    if ranked:
        fbase = fine(ids_of(base, resolver))
        for _, ch, cand in ranked[:top_k]:
            res = decide(fbase, fine(ids_of(cand, resolver)), rule, False)
            record(ledger, {"stage": "fine", "base": base.plan_id(), "cand": cand.plan_id(), "change": ch.ops, "reason": ch.reason, **res})
            if res["verdict"] == "accept":
                final, best = cand, res
                break
    path = None
    if final is not base and out_dir:
        final.name, final.status, final.source = f"{combo['id']}_auto_{final.plan_id()}", "adopted", "deckplan.auto.two_stage"
        final.notes = f"粗比較(budget={coarse_budget})→通常予算で再比較し有意に改善 (FAIR, {turn}ターンキル率, seeds={len(seeds)})"
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        path = Path(out_dir) / f"{final.name}.yaml"
        save(final, path)
    return {"base": base.plan_id(), "final": final.plan_id(), "adopted": final is not base, "path": str(path) if path else None,
            "candidates": len(cands), "passed_coarse": len(ranked), "sec": round(time.time() - t0, 1)}


def unused_names(rules, deck_ids: list[str], opp_ids: list[str], seeds: list[int], turns: int = 3, budget: int = 60) -> list[str]:
    """usage 監査（dmsim.autofix.usage）で使われにくい札の名前。抜く候補に使う。"""
    from ..autofix.usage import collect_usage, unused_cards
    u = collect_usage(rules, deck_ids, opp_ids, seeds, max_turn=turns, budget=budget)
    return [rules.cards[r["id"]].name for r in unused_cards(u) if r["id"] in rules.cards]


def add_candidates(combo: dict, max_cost: int = 4) -> list[str]:
    """入れる側の候補: コンボの core 部品＋墓地への準備札（tools/suggest_prep）。"""
    from tools.suggest_prep import scan
    return core_names(combo) + [r["name"] for r in scan() if isinstance(r["cost"], int) and r["cost"] <= max_cost]
