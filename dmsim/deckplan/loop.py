"""改善ループの枠: 提案 → 評価 → 採否 → 記録。提案側は登録式、採否は evaluate.decide のみ。
自動改善（探索・学習）は PROPOSERS に足すだけで接続できる。ここはエンジンもカードデータも変更しない。"""
from __future__ import annotations

import random

from . import change as C
from dmsim.eval.deckeval import AcceptRule, Scorer, decide, record
from .spec import DeckProposal, Resolver, check


def ids_of(deck: DeckProposal, resolver: Resolver) -> list[str]:
    out = []
    for e in deck.entries:
        cid, _ = resolver(e)
        if cid is None:
            raise ValueError(f"{e.name} の ID が未確定")
        out += [cid] * e.count
    return out


def improve(base: DeckProposal, scorer: Scorer, resolver: Resolver, pool: list[str], ledger,
            kinds=("swap",), rounds: int = 1, seed: int = 0, rule: AcceptRule = AcceptRule(), **kw) -> DeckProposal:
    rng = random.Random(seed)
    cur = base
    for _ in range(rounds):
        base_score = scorer(ids_of(cur, resolver))
        for k in kinds:
            for ch in C.PROPOSERS[k](cur, rng, pool, **kw):
                cand = C.apply(cur, ch)
                st = check(cand, resolver)
                res = decide(base_score, scorer(ids_of(cand, resolver)), rule, st["unverified"]) if not st["issues"] else {"verdict": "invalid", "why": st["issues"]}
                record(ledger, {"base": cur.plan_id(), "cand": cand.plan_id(), "change": ch.ops, "reason": ch.reason, **res})
                if res["verdict"] == "accept":
                    cur = cand
                    break
    return cur
