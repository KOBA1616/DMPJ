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
from ..base.loopspec import LoopSpec, Pred
from ..engine_view import result_of
from ..base import store

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
    eval_seeds: int = 8                  # デッキ版: 1つのデッキを何シードで試すか
    max_turn: int = 8                    # デッキ版: 通しターン数（先手の1ターン目=1、相手のターンも数える）
    opp_card: str = "T001"               # デッキ版: 相手は40枚すべてこのカード（マナチャージだけする）
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
    won_by = result_of(result.engine) or {}
    ls.goal = [Pred(0, {"types": ["creature", "spell"]}, 1, ">=", zone="bz")] if ls.kind == "reroll" else []
    if ls.kind == "reroll" and not ls.goal:
        raise AssertionError
    ls.source = {"board": sk.spec, "steps": [[k, list(keys), list(idx)] for k, keys, idx in steps], "win_rate": rate,
                 "win_reason": won_by.get("reason"), "win_turn": won_by.get("turn"),
                 "search": {"kind": "beam", "width": cfg.width, "nodes": result.nodes}, "auto": True,
                 "note": "手順が通る盤面の下限(1-極小)。シャッフルに運が絡むと最小化はシード依存。win_rate は同じ手順が通るシードの割合"}
    store.write_text(path, ls.to_json() + "\n")
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


# ---- デッキ版: 通常の開幕（40枚・シャッフル・先手後手ランダム・手札5枚・盾5枚・マナ0・1ターン目）から勝てるデッキを探す ----

def deck_from_counts(counts: dict, filler: str, size: int = 40) -> list[str]:
    deck = [c for c, n in counts.items() for _ in range(n)]
    return deck + [filler] * (size - len(deck))


def build_game(rules, board: dict):
    """board = {"deck": [...], "opp_deck": [...], "seed": n, "first_player": 0/1}。通常の開幕から始まる。"""
    from ..engine import Engine
    return Engine.new_game(rules, [board["deck"], board["opp_deck"]], board["seed"], first_player=board["first_player"])


def first_player_of(seed: int) -> int:
    return random.Random(seed * 7919).randint(0, 1)      # 先手後手はシードから決める（再現できるランダム）


def mutate_deck(deck: list[str], cfg: AutoConfig, rng: random.Random) -> list[str]:
    d = list(deck)
    for _ in range(rng.choice((1, 1, 2, 3))):
        for _try in range(20):       # 同名4枚の制限を守る置き換えだけ採る
            i = rng.randrange(len(d))
            new = rng.choice(cfg.pool + [cfg.filler])
            cand = d[:i] + [new] + d[i + 1:]
            if not deck_violations(cand, cfg.filler):
                d = cand
                break
    return d


def deck_violations(deck: list[str], filler: str, limit: int = 4) -> list[tuple[str, int]]:
    cnt: dict[str, int] = {}
    for c in deck:
        cnt[c] = cnt.get(c, 0) + 1
    return [(c, n) for c, n in sorted(cnt.items()) if n > limit and c != filler and not c.startswith("T")]


def evaluate_deck(rules, cfg: AutoConfig, deck: list[str], opp_deck: list[str]):
    """複数シードで、そのデッキが max_turn ターンまでに勝てるかを探索する。(勝ち数, 平均評価, 最初の勝ち) を返す。"""
    wins, score, first_win = 0, 0.0, None
    for sd in range(1, cfg.eval_seeds + 1):
        board = {"deck": deck, "opp_deck": opp_deck, "seed": sd, "first_player": first_player_of(sd)}
        r = bestfirst.beam(build_game(rules, board), 0, cfg.width, cfg.max_depth, max_turn=cfg.max_turn)
        if r.won:
            wins += 1
            if first_win is None:
                first_win = (board, r)
        else:
            score += bestfirst.priority(r.engine, 0, Weights())
    return wins, score / cfg.eval_seeds, first_win


PLAIN_REASONS = {"direct_attack", "deck_out"}


def classify_win(reason) -> str:
    """勝ち方の自動分類。直接攻撃・山札切れ以外（状態勝ちなど）はコンボ候補として扱う。"""
    return "plain" if reason in PLAIN_REASONS else "combo"


def save_deck_win(rules, cfg: AutoConfig, deck: list[str], opp_deck: list[str], wins: int, board: dict, result, name: str):
    steps = replay.steps_of(result.engine)
    if not replay.replay_test(rules, steps, build=build_game)(board):
        return "", None, {"error": "手順を再生しても勝てない（再生のずれ）"}
    used = sorted({k.split(":")[1] for _, keys, _ in steps for k in keys if ":" in k and k.split(":")[1] in rules.cards and k.split(":")[1] != cfg.filler
                   and not k.split(":")[1].startswith("T")})
    sig = hashlib.blake2b(json.dumps(used, ensure_ascii=False).encode(), digest_size=6).hexdigest()
    path = cfg.out_dir / f"{sig}.json"
    rate = wins / cfg.eval_seeds
    reason = (result_of(result.engine) or {}).get("reason")
    cls = classify_win(reason)
    info = {"signature": sig, "win_rate": rate, "log": len(steps), "cards": used, "reason": reason, "class": cls}
    if path.exists():
        return sig, None, info
    ls = LoopSpec(name=name, kind="deterministic" if rate >= 0.99 else "reroll",
                  minimal=[Pred(0, {"name": c}, 1, ">=", zone="deck") for c in used],
                  goal=[Pred(0, {"name": used[0]}, 1, ">=", zone="deck")] if used else [],
                  source={"board": board, "steps": [[k, list(keys), list(idx)] for k, keys, idx in steps], "win_rate": rate,
                          "win_turn": (result_of(result.engine) or {}).get("turn"), "auto": True, "mode": "deck", "class": cls, "win_reason": reason,
                          "search": {"kind": "beam", "width": cfg.width, "max_turn": cfg.max_turn, "seeds": cfg.eval_seeds},
                          "note": "通常の開幕(40枚・先手後手ランダム)から勝てたデッキ。cards は手順で使われたカード。win_rate は探索した全シードのうち勝てた割合"})
    store.write_text(path, ls.to_json() + "\n")
    return sig, path, info


def run_decks(rules, cfg: AutoConfig, log=print) -> dict:
    rng = random.Random(cfg.rng_seed)
    opp = [cfg.opp_card] * 40
    for sd in cfg.seeds:
        deck = sd["deck"] if "deck" in sd else deck_from_counts(sd["deck_counts"], cfg.filler)
        if len(deck) != 40 or deck_violations(deck, cfg.filler):
            raise ValueError(f"種デッキが40枚でない、または同名4枚の制限を超えている: {len(deck)} {deck_violations(deck, cfg.filler)}")
    archive = []
    stats = {"decks": 0, "winning_decks": 0, "saved": [], "dups": 0, "illegal": 0}
    seen: set = set()
    t0 = time.time()
    i = 0
    seeds = [sd["deck"] if "deck" in sd else deck_from_counts(sd["deck_counts"], cfg.filler) for sd in cfg.seeds]
    while time.time() - t0 < cfg.seconds:
        i += 1
        if i <= len(seeds):
            deck = seeds[i - 1]
        else:
            deck = mutate_deck(rng.choice(archive[: max(3, len(archive) // 2)])[2], cfg, rng)
        key = tuple(sorted(deck))
        if key in seen:
            continue
        seen.add(key)
        if deck_violations(deck, cfg.filler):
            stats["illegal"] += 1
            continue
        try:
            wins, score, fw = evaluate_deck(rules, cfg, deck, opp)
        except Exception as ex:
            log(f"skip deck: {type(ex).__name__}: {ex}")
            continue
        stats["decks"] += 1
        bonus = 5e5 if fw and classify_win((result_of(fw[1].engine) or {}).get("reason")) == "combo" else 0
        archive.append((wins * 1e6 + bonus + score, i, deck))
        archive.sort(key=lambda x: -x[0])
        del archive[30:]
        if fw:
            stats["winning_decks"] += 1
            if classify_win((result_of(fw[1].engine) or {}).get("reason")) == "combo":
                stats["combo_wins"] = stats.get("combo_wins", 0) + 1
            sig, path, info = save_deck_win(rules, cfg, deck, opp, wins, fw[0], fw[1], f"自動発見(デッキ) {len(stats['saved']) + 1}")
            if path:
                stats["saved"].append(str(path))
                log(f"WIN new {sig} {info}")
            elif sig:
                stats["dups"] += 1
                log(f"WIN dup {sig} {info}")
            else:
                log(f"WIN but {info}")
    stats["seconds"] = round(time.time() - t0)
    return stats
