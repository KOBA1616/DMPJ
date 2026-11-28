"""既知ループに足す1枚の発見（S5、2026-11-17）。

既知ループ（サガ・アカシック）の現行レシピに1種4枚を差し込み、同一シードの局で
入口に max_turn ターン以内に届く局が増える札を探す。2枚組の相乗分（synergy_hunt）とは別に、
「既知の中核に足すと入口到達が早まる基盤」を拾う。

候補:
- basebuild.candidates と同じ役割×文明×コスト4以下の札（1役割あたり per 枚まで）
- synergy_hunt.links で中核の札を直接指す札（踏み倒し・軽減・付与・誘発、コスト4以下、中核の文明内）
差し込む先: 基盤（中核以外）の各種類を、文明が合う飾りなし札に替えた局（抜き取り）を先に測り、
抜いても入口到達が最も減らない種類を差し替え先にする。
測定は eval.api.measure_assembly（通常開幕・公平探索）。結果は data/registry/addon_hunt.yaml（入口ごと）。
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import yaml

from ..base.registry import load_known_combos
from . import basebuild as B
from . import synergy_hunt as SH

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "registry" / "addon_hunt.yaml"   # candidates.yaml の synergy_hunt 欄は末尾を書き直すので別ファイル


def core_of(entry: str) -> dict[str, int]:
    """data/known_combos/combos.yaml の中核（role: core）の id → 4。"""
    for c in load_known_combos():
        if isinstance(c, dict) and c.get("id") == entry:
            return {p["id"]: B.COPIES for p in c.get("parts") or [] if p.get("role") == "core"}
    raise KeyError(entry)


def pick(rules, deck: list[str], core: dict, *, per: int = 6, linked: int = 8) -> list[dict]:
    """候補札 [{id, name, why}]。デッキに既にある札・中核と同名の札は除く。"""
    raw = B._raw_cards(rules)
    civs = B.core_civs(rules, core)
    have = set(deck)
    names = {rules.cards[i].name for i in have}
    out, seen = [], set()

    def add(i, why):
        c = rules.cards[i]
        if i in have or c.name in names or c.name in seen:
            return
        seen.add(c.name)
        out.append({"id": i, "name": c.name, "why": why})
    old = B.PER_ROLE
    try:
        B.PER_ROLE = per
        for r, ids in B.candidates(rules, core, raw).items():
            for i in ids:
                add(i, r)
    finally:
        B.PER_ROLE = old
    n = 0
    for i in sorted(raw, key=lambda i: (rules.cards[i].cost or 0, i)):
        if n >= linked:
            break
        c = rules.cards[i]
        if B._test(i) or B.missing_effect(c) or not c.cost or c.cost > B.MAX_COST or c.evolve_from:
            continue
        if not set(c.civs) - {"zero"} or not set(c.civs) <= civs:
            continue
        hit = [(k, j) for k, f in SH.links(c) if SH.specific(f) for j in core if SH.admits(f, rules.cards[j])]
        if hit:
            before = len(out)
            add(i, f"{hit[0][0]}:{rules.cards[hit[0][1]].name}")
            n += len(out) > before
    return out


def swap(deck: list[str], old: str, new: str) -> list[str]:
    return [new if x == old else x for x in deck]


def stats(rows: list[dict], turn: int) -> dict:
    n = len(rows)
    e = sum(1 for r in rows if r["entry_turn"] is not None and r["entry_turn"] <= turn)
    return {"games": n, "entry": e, "stage2": sum(1 for r in rows if r["stage2"]),
            "kill_3_4": sum(1 for r in rows if r.get("kill") and r.get("win_turn") is not None and r["win_turn"] <= 4)}


def paired(base: list[dict], new: list[dict], turn: int) -> dict:
    """同一シードの差（入口 turn 以内に届いたかの 0/1）。平均と 95% 区間。"""
    b = {r["seed"]: r for r in base}
    ds = []
    for r in new:
        if r["seed"] in b:
            f = lambda x: 1 if x["entry_turn"] is not None and x["entry_turn"] <= turn else 0  # noqa: E731
            ds.append(f(r) - f(b[r["seed"]]))
    n = len(ds)
    if not n:
        return {"n": 0, "mean": 0.0, "lo": 0.0, "hi": 0.0}
    m = sum(ds) / n
    sd = math.sqrt(sum((d - m) ** 2 for d in ds) / (n - 1)) if n > 1 else 0.0
    h = 1.96 * sd / math.sqrt(n)
    return {"n": n, "mean": round(m, 3), "lo": round(m - h, 3), "hi": round(m + h, 3),
            "up": sum(1 for d in ds if d > 0), "down": sum(1 for d in ds if d < 0)}


def run(rules, entry: str, deck_file: str, *, seeds: int = 40, turn: int = 4, opp: int = 1, budget: int = 200,
        workers: int = 4, per: int = 6, linked: int = 8, ckpt: Path | None = None, log=print, slot: str | None = None) -> dict:
    from ..eval.api import measure_assembly
    deck = yaml.safe_load(Path(deck_file).read_text(encoding="utf-8"))["deck"]
    core = core_of(entry)
    raw = B._raw_cards(rules)
    fill = B.fillers(rules, core, raw)
    sd = list(range(1, seeds + 1))
    done = json.loads(ckpt.read_text()) if ckpt and ckpt.exists() else {}

    def meas(key, d):
        """workers 局ずつ測って途中を書く（環境の再起動で長い測定が切れても続きから）。"""
        part = done.setdefault("_part", {}).get(key, []) if key not in done else None
        if part is not None:
            got = {r["seed"] for r in part}
            todo = [x for x in sd if x not in got]
            for i in range(0, len(todo), max(1, workers)):
                rows = measure_assembly(rules, entry, d, todo[i:i + max(1, workers)], max_turn=turn, budget=budget,
                                        opp_level=opp, workers=workers)
                part += [{k: r[k] for k in ("seed", "entry_turn", "stage2", "kill", "win_turn")} for r in rows]
                done["_part"][key] = part
                if ckpt:
                    ckpt.write_text(json.dumps(done))
            done[key] = sorted(part, key=lambda r: r["seed"])
            done["_part"].pop(key, None)
            if ckpt:
                ckpt.write_text(json.dumps(done))
            log(key, stats(done[key], turn))
        return done[key]

    base = meas("base", deck)
    bases = [i for i in dict.fromkeys(deck) if i not in core]
    drop = {}
    for i in (bases if slot is None else []):   # slot を渡すと抜き取りの測定を省く
        v = next((f for f in fill if set(rules.cards[f].civs) & set(rules.cards[i].civs)), fill[0])
        drop[i] = paired(base, meas(f"drop:{i}", swap(deck, i, v)), turn)
    slot = slot or max(bases, key=lambda i: (drop[i]["mean"], i))
    res = []
    for c in pick(rules, deck, core, per=per, linked=linked):
        rows = meas(f"add:{c['id']}", swap(deck, slot, c["id"]))
        res.append(dict(c, **stats(rows, turn), diff=paired(base, rows, turn)))
    res.sort(key=lambda x: (-x["diff"]["mean"], x["id"]))
    return {"entry": entry, "deck": deck_file, "turn": turn, "opp": opp, "seeds": seeds, "base": stats(base, turn),
            "slot": {"id": slot, "name": rules.cards[slot].name},
            "drop": {i: dict(name=rules.cards[i].name, **drop[i]) for i in drop}, "candidates": res}


def record(result: dict, path: Path = OUT, note: str = "") -> int:
    """addon_hunt.yaml の入口の欄を書き換える（他の入口には触れない）。区間の下限が 0 を超えた札の数を返す。"""
    y = (yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None) or {}
    y[result["entry"]] = dict(result, note=note)
    path.write_text(yaml.safe_dump(y, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return sum(1 for c in result["candidates"] if c["diff"]["lo"] > 0)


def hunt_hook(rules, entry: str = "saga", deck_file: str = "data/decks/basebuild_saga_v3.yaml", **kw) -> dict:
    """hunt から呼ぶ口: 測って記録し、結果を返す。"""
    r = run(rules, entry, str(ROOT / deck_file) if not Path(deck_file).is_absolute() else deck_file, **kw)
    record(r)
    return r


__all__ = ["core_of", "pick", "swap", "stats", "paired", "run", "record", "hunt_hook"]
