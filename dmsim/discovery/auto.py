"""自立発見ランナー: 盤面を変異させながら探索し、勝てる盤面を検証・縮約して LoopSpec として保存する。LLM は使わない（課金なし）。

1周の流れ:
  1. アーカイブ（初期は種盤面）から盤面を選び、変異させる（カードの追加・削除・差し替え・ゾーン移動、シード変更）。
     同名カードは4枚まで（scenario.deck_limit_violations）。T番台と filler は数えない。
  2. ビーム探索（bestfirst.beam）で、その盤面で勝てるかを調べる。
  3. 勝てたら: 手順を再生して、同じ手順が通るシードの割合（win_rate）を測り、決定的(>=0.99)か運しだい(reroll)かを分類する。
     手順が通る盤面の下限まで縮約し、LoopSpec にして data/loops/auto/<署名>.json に保存する。同じ署名は保存しない。
  4. 勝てなかった盤面も、評価（priority）が高ければ次の変異の元としてアーカイブに残す。
再現できるよう、乱数は seed から決める。"""
from __future__ import annotations

import copy
import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

from .. import scenario
from . import bestfirst, replay, shrink
from .bestfirst import Weights
from .loopspec import LoopSpec, Pred

MUT_ZONES = ("hand", "mana", "bz", "graveyard", "shield", "deck")


@dataclass
class AutoConfig:
    pool: list[str]                      # 盤面に足してよいカードID
    seeds: list[dict]                    # 種盤面（scenario の spec）
    filler: str = "T013"
    width: int = 300                     # ビーム幅（広いほど深く探すが遅い）
    max_depth: int = 80
    rate_seeds: int = 50                 # win_rate を測るシード数
    seconds: float = 300.0               # 全体の時間予算
    rng_seed: int = 1
    out_dir: Path = Path("data/loops/auto")
    max_zone: dict = field(default_factory=lambda: {"hand": 12, "mana": 14, "bz": 5, "graveyard": 6, "shield": 8, "deck": 14})


def mutate(spec: dict, cfg: AutoConfig, rng: random.Random, rules) -> dict:
    s = copy.deepcopy(spec)
    p0 = s.setdefault("p0", {})
    for _ in range(rng.choice((1, 1, 2, 3))):
        op = rng.choice(("add", "add", "remove", "swap", "move", "seed"))
        zones = [z for z in MUT_ZONES]
        if op == "add":
            z = rng.choice(zones)
            if len(p0.get(z, [])) < cfg.max_zone[z]:
                p0.setdefault(z, []).append(rng.choice(cfg.pool + [cfg.filler]))
        elif op == "remove":
            z = rng.choice([z for z in zones if p0.get(z)] or [None])
            if z:
                del p0[z][rng.randrange(len(p0[z]))]
                if not p0[z]:
                    del p0[z]
        elif op == "swap":
            z = rng.choice([z for z in zones if p0.get(z)] or [None])
            if z:
                p0[z][rng.randrange(len(p0[z]))] = rng.choice(cfg.pool + [cfg.filler])
        elif op == "move":
            z = rng.choice([z for z in zones if p0.get(z)] or [None])
            if z:
                n = p0[z].pop(rng.randrange(len(p0[z])))
                if not p0[z]:
                    del p0[z]
                to = rng.choice(zones)
                if len(p0.get(to, [])) < cfg.max_zone[to]:
                    p0.setdefault(to, []).append(n)
                else:
                    p0.setdefault(z, []).append(n)
        else:
            s["seed"] = rng.randint(1, 9)
    return s


def signature(spec: dict, filler: str) -> str:
    """縮約した盤面の署名: 非 filler のカードの多重集合（ゾーンとシードは見ない）。"""
    names = sorted(n for _, _, _, n in shrink.entries(spec) if n != filler)
    return hashlib.blake2b(json.dumps(names, ensure_ascii=False).encode(), digest_size=6).hexdigest()


def win_rate(rules, steps, spec: dict, n: int, prepare=None) -> float:
    return sum(replay.replay_test(rules, steps, prepare)(dict(spec, seed=sd)) for sd in range(1, n + 1)) / n


def save_win(rules, cfg: AutoConfig, spec: dict, result, name: str) -> tuple[str, Path | None, dict]:
    """勝てた盤面を検証・縮約して保存する。(署名, 保存先 or None(既存), 概要) を返す。"""
    steps = replay.steps_of(result.engine)
    test = replay.replay_test(rules, steps)
    if not test(spec):
        return "", None, {"error": "手順を再生しても勝てない（再生のずれ）"}
    sk = shrink.shrink(spec, test, order=("hand", "mana", "bz", "graveyard", "shield", "deck"))
    sig = signature(sk.spec, cfg.filler)
    path = cfg.out_dir / f"{sig}.json"
    rate = win_rate(rules, steps, sk.spec, cfg.rate_seeds)
    info = {"signature": sig, "win_rate": rate, "log": len(steps), "kept": sum(1 for _ in shrink.entries(sk.spec))}
    if path.exists():
        return sig, None, info
    ls = shrink.to_loopspec(rules, name, sk, delta={}, source={})
    ls.kind = "deterministic" if rate >= 0.99 else "reroll"
    won_by = result.engine.s.result or {}
    ls.goal = [Pred(0, {"types": ["creature", "spell"]}, 1, ">=", zone="bz")] if ls.kind == "reroll" else []
    if ls.kind == "reroll" and not ls.goal:
        raise AssertionError
    ls.source = {"board": sk.spec, "steps": [[k, list(keys), list(idx)] for k, keys, idx in steps], "win_rate": rate,
                 "win_reason": won_by.get("reason"), "win_turn": won_by.get("turn"),
                 "search": {"kind": "beam", "width": cfg.width, "nodes": result.nodes}, "auto": True,
                 "note": "手順が通る盤面の下限(1-極小)。シャッフルに運が絡むと最小化はシード依存。win_rate は同じ手順が通るシードの割合"}
    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(ls.to_json() + "\n")
    return sig, path, info


def run(rules, cfg: AutoConfig, log=print) -> dict:
    rng = random.Random(cfg.rng_seed)
    for sp in cfg.seeds:
        bad = scenario.deck_limit_violations(rules, sp)
        if bad:
            raise ValueError(f"種盤面が同名4枚の制限を超えている: {bad}")
    t0 = time.time()
    archive = [(0.0, copy.deepcopy(s)) for s in cfg.seeds]
    stats = {"boards": 0, "wins": 0, "saved": [], "dups": 0, "illegal": 0}
    seen: set[str] = set()
    i = 0
    while time.time() - t0 < cfg.seconds:
        i += 1
        base = archive[0][1] if i <= len(cfg.seeds) else rng.choice(archive[: max(3, len(archive) // 2)])[1]
        spec = base if i <= len(cfg.seeds) else mutate(base, cfg, rng, rules)
        key = json.dumps(spec, sort_keys=True, ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        if scenario.deck_limit_violations(rules, spec):
            stats["illegal"] += 1
            continue
        try:
            e = scenario.build(rules, spec)
            r = bestfirst.beam(e, 0, cfg.width, cfg.max_depth)
        except Exception as ex:   # 変異で壊れた盤面は捨てる
            log(f"skip board: {type(ex).__name__}: {ex}")
            continue
        stats["boards"] += 1
        if r.won:
            stats["wins"] += 1
            sig, path, info = save_win(rules, cfg, spec, r, f"自動発見 {len(stats['saved']) + 1}")
            if path:
                stats["saved"].append(str(path))
                log(f"WIN new {sig} {info}")
            elif sig:
                stats["dups"] += 1
                log(f"WIN dup {sig} {info}")
            else:
                log(f"WIN but {info}")
        else:
            score = bestfirst.priority(r.engine, 0, Weights())
            archive.append((score, spec))
            archive.sort(key=lambda x: -x[0])
            del archive[40:]
    stats["seconds"] = round(time.time() - t0)
    return stats
