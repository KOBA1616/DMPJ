"""デッキの変更案（提案側）。変更の種類は登録式（engine/registry.py と同じ流儀）。

提案側は自由に足せるが、採否は evaluate.decide だけが行う。"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable

from .spec import DeckProposal, Entry

PROPOSERS: dict[str, Callable] = {}


@dataclass
class Change:
    kind: str
    ops: list[tuple[str, int]]            # [(カード名, 増減枚数)]。合計は 0（枚数を保つ）
    reason: str = ""                       # 理由（人が読む用）
    meta: dict = field(default_factory=dict)


def proposer(kind: str):
    """@proposer("swap") def f(deck, rng, pool, **kw) -> list[Change]"""
    def deco(fn):
        if kind in PROPOSERS:
            raise ValueError(f"proposer '{kind}' already registered")
        PROPOSERS[kind] = fn
        return fn
    return deco


def apply(deck: DeckProposal, ch: Change, name: str | None = None, copy_limit: int = 4) -> DeckProposal:
    counts = {e.name: e for e in deck.entries}
    ents = [Entry(e.name, e.count, e.card_id) for e in deck.entries]
    by = {e.name: e for e in ents}
    for n, d in ch.ops:
        if n in by:
            by[n].count += d
        elif d > 0:
            ents.append(Entry(n, d)); by[n] = ents[-1]
        else:
            raise ValueError(f"{n} は入っていない")
    ents = [e for e in ents if e.count > 0]
    if any(e.count > copy_limit or e.count < 0 for e in by.values()):
        raise ValueError("枚数の上限を超える変更")
    return DeckProposal(name or f"{deck.name}+{ch.kind}", ents, list(deck.tags), deck.source, deck.notes, "proposed", deck.schema_version, dict(deck.extra))


@proposer("swap")
def swap(deck: DeckProposal, rng: random.Random, pool: list[str], n: int = 5, **_) -> list[Change]:
    """1枚抜いて pool の別カードを1枚入れる（pool は呼び出し側が与える。ここでカードを選ぶ基準は持たない）。"""
    out = []
    for _ in range(n):
        a = rng.choice(deck.entries).name
        b = rng.choice(pool)
        if a != b:
            out.append(Change("swap", [(a, -1), (b, 1)], f"{a} → {b}"))
    return out


@proposer("add_parts")
def add_parts(deck: DeckProposal, rng: random.Random, pool: list[str], n: int = 5, want: int = 3, protect: set | None = None, **_) -> list[Change]:
    """cards 段階の診断用: 部品（pool＝既知コンボの core 名）が want 枚未満なら、部品でない札を1枚抜いて部品を1枚足す。
    自動診断（dmsim.autofix）から呼ぶ。採否は evaluate.decide だけが行う。"""
    have = {e.name: e.count for e in deck.entries}
    lacking = [p for p in pool if have.get(p, 0) < min(want, 4)]
    others = [e.name for e in deck.entries if e.name not in pool and e.name not in (protect or ())]
    if not lacking or not others:
        return []
    out = []
    for _ in range(n):
        a, b = rng.choice(others), rng.choice(lacking)
        out.append(Change("add_parts", [(a, -1), (b, 1)], f"部品不足: {a} → {b}"))
    return out


@proposer("add_prep")
def add_prep(deck: DeckProposal, rng: random.Random, pool: list[str] | None = None, n: int = 5, max_cost: int = 4, protect: set | None = None, **_) -> list[Change]:
    """墓地への仕込み手段（tools/suggest_prep の静的列挙）を1枚足し、仕込みでない札を1枚抜く。
    pool を渡せばその名前に限る。採否は evaluate.decide だけが行う。"""
    from tools.suggest_prep import scan
    have = {e.name for e in deck.entries}
    cands = [r["name"] for r in scan()
             if r["name"] not in have and (not pool or r["name"] in pool)
             and isinstance(r["cost"], int) and r["cost"] <= max_cost]
    others = [e.name for e in deck.entries if e.name not in (protect or ())]
    if not cands or not others:
        return []
    return [Change("add_prep", [(a, -1), (b, 1)], f"仕込み手段: {a} → {b}")
            for a, b in ((rng.choice(others), rng.choice(cands)) for _ in range(n))]
