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


@proposer("cut_unused")
def cut_unused(deck: DeckProposal, rng: random.Random, pool: list[str] | None = None, n: int = 5, unused: list[str] | None = None,
               protect: set | None = None, adds: list[str] | None = None, **_) -> list[Change]:
    """使われにくい札（usage 監査の unused 名）を1枚抜き、adds（部品・準備札）の別札を1枚入れる。
    unused / adds は呼び出し側が与える。コア（protect）は抜かない。"""
    have = {e.name: e.count for e in deck.entries}
    outs = [u for u in (unused or []) if have.get(u, 0) > 0 and u not in (protect or ())]
    ins = [a for a in (adds or []) if have.get(a, 0) < 4]
    if not outs or not ins:
        return []
    return [Change("cut_unused", [(a, -1), (b, 1)], f"使われにくい札を入れ替え: {a} → {b}")
            for a, b in ((rng.choice(outs), rng.choice(ins)) for _ in range(n)) if a != b]


@proposer("trim_parts")
def trim_parts(deck: DeckProposal, rng: random.Random, pool: list[str], n: int = 5, protect: set | None = None, **_) -> list[Change]:
    """部品（pool）の枚数調整: 3枚以上ある部品を1枚減らし、部品でない既存札を1枚増やす（部品が多すぎて事故る場合の減らす案）。"""
    have = {e.name: e.count for e in deck.entries}
    heavy = [p for p in pool if have.get(p, 0) >= 3]
    fill = [e.name for e in deck.entries if e.name not in pool and e.count < 4]
    if not heavy or not fill:
        return []
    return [Change("trim_parts", [(a, -1), (b, 1)], f"部品を減らす: {a} → {b}")
            for a, b in ((rng.choice(heavy), rng.choice(fill)) for _ in range(n))]


@proposer("add_support")
def add_support(deck: DeckProposal, rng: random.Random, pool: list[str] | None = None, n: int = 5, support: dict | None = None,
                protect: set | None = None, unused: list[str] | None = None, **_) -> list[Change]:
    """加速・ドロー・サーチ札（deckplan.pool がカード全体から自動分類。support={役割: [名前]}）を役割ごとに順番に1枚足し、
    使われにくい札を優先して（無ければ保護外の札から）1枚抜く。採否は evaluate.decide だけが行う。"""
    have = {e.name: e.count for e in deck.entries}
    roles = [r for r, v in (support or {}).items() if any(have.get(x, 0) < 4 for x in v)]
    keep = set(protect or ())
    outs = [u for u in (unused or []) if have.get(u, 0) > 0 and u not in keep] or [e.name for e in deck.entries if e.name not in keep]
    if not roles or not outs:
        return []
    out = []
    for i in range(n):
        role = roles[i % len(roles)]
        ins = [x for x in support[role] if have.get(x, 0) < 4]
        a, b = rng.choice(outs), (ins[min(len(ins) - 1, int(rng.random() ** 2 * len(ins)))])   # 軽い札寄りに選ぶ
        if a != b:
            out.append(Change("add_support", [(a, -1), (b, 1)], f"{role}札を追加: {a} → {b}"))
    return out
