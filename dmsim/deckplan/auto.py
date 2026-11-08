"""デッキ側の自動改善: 診断（cards 段階 = 部品が揃わない）から候補デッキ（部品の追加・準備札の追加と入れ替え）を作り、
同一シード・同一先後の対比較（FAIR・N ターンキル率）で有意に良いものだけを採用する。エンジン・カードデータは読むだけ。
未変換カードを含む候補は自動採用しない（evaluate.decide が hold_unverified にする）。コアの部品は抜かない。"""
from __future__ import annotations

import time
from collections import Counter
from pathlib import Path

from . import change as C
from .evaluate import AcceptRule, harness_scorer
from .loop import improve
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
