"""対戦の実行・再生と、簡単な方策（エージェント）。"""
from __future__ import annotations

import random

from .engine import Engine


def random_policy(rng: random.Random):
    def pol(eng: Engine, d: dict) -> list[int]:
        n = len(d["options"])
        k = rng.randint(d["min"], d["max"])
        return rng.sample(range(n), k)
    return pol


def passive_policy(eng: Engine, d: dict) -> list[int]:
    """1人回しの相手役: 何もしない（ブロックしない・S・トリガーを使わない・最小限の選択）。"""
    keys = [o["key"] for o in d["options"]]
    for k in ("pass", "no_block", "no", "decline"):
        if k in keys:
            return [keys.index(k)]
    return list(range(d["min"]))


def run(eng: Engine, policies, max_decisions: int = 100000) -> dict:
    """policies[p](eng, decision) -> 選択した添字のリスト。"""
    for _ in range(max_decisions):
        d = eng.advance()
        if d is None:
            return eng.s.result
        eng.answer(policies[d["player"]](eng, d))
    raise RuntimeError("decision limit")


def replay(rules, decks, seed, log, first_player=0) -> Engine:
    """シード＋選択ログから同じ対戦を再現する。"""
    eng = Engine.new_game(rules, decks, seed, first_player)
    for entry in log:
        d = eng.advance()
        if d is None or d["kind"] != entry["kind"] or d["player"] != entry["p"]:
            raise RuntimeError(f"replay diverged at {len(eng.log)}: {d and d['kind']} vs {entry}")
        eng.answer(entry["choice"])
    eng.advance()
    return eng
