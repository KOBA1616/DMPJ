"""直接つながる2枚組の発見（S5、docs/combo-ruler-design.md「直接参照の組」節、2026-11-16）。

流れ（run を1回呼ぶだけで回る。tools/synergy_hunt.py と、hunt から呼ぶ口 hunt_hook）:
1. 拾う（pick）: 効果データ上で、札 A の効果がもう1枚の札 B を直接指す組だけを静的に拾う。カード名は見ない（効果データのフィルタで照合）。
   - cheat   A の踏み倒し（play_free、手札・山札・墓地・マナ・盾から場へ出す move）のフィルタに B が合う
   - reduce  A の常在型のコスト軽減（affects が手札、mod.cost < 0）のフィルタに B が合う
   - grant   A の常在型の付与（affects が場、mod に grant / allow / breaks / power）のフィルタに B が合う
   - trigger A の誘発（攻撃・破壊・バトルに勝つ・出た時）の主語のフィルタに B が合う（B が動くたびに A が働く）
   フィルタは「特定的」なものだけ（種族・名前を含む、または文明とコストの範囲の両方）。どのクリーチャーにも合う広いフィルタは拾わない。
   A はコスト4以下、B は踏み倒しならコスト8以下・それ以外は4以下。速さの上限（speed_bound.static_bound）が4以下。
   単独の働きが大きい札（candidates.yaml の screened_attack で片方だけの寄与が --strong 以上だった札）を含む組は除く。
2. 測る（measure）: 4デッキ比較（両方あり・Aだけ・Bだけ・両方なし、抜いた札は同じコスト・文明のバニラ）を同じシードで測り、
   相乗分（eval.contrib.interaction）を出す。基準の相手は段階1、参考は 2b（ユーザー決定 2026-11-14）。
3. 記録する（record）: data/registry/candidates.yaml の synergy_hunt に、測った全組の値を書く（足切りしない、相乗分の順）。
未変換・効果の欠けた札は候補から外し、外した札の一覧を結果に残す（変換は別の担い手）。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

PUT_FROM = ("hand", "deck", "graveyard", "mana", "shield")
TRIG_EVENTS = ("attack", "destroy", "battle_win", "put", "enter", "summon")
VALUES = ("kill", "left", "broken", "board")


def _faces(d):
    return list(getattr(d, "faces", None) or []) or [d]


def _walk(ops):
    for op in ops or []:
        if not isinstance(op, dict):
            continue
        yield op
        for k in ("body", "then", "else", "ops", "options", "choices"):
            v = op.get(k)
            if isinstance(v, list):
                for x in v:
                    if isinstance(x, dict) and "op" in x:
                        yield from _walk([x])
                    elif isinstance(x, list):
                        yield from _walk(x)
                    elif isinstance(x, dict):
                        yield from _walk(x.get("body") or x.get("ops") or [])


def specific(flt: dict) -> bool:
    if not flt:
        return False
    if flt.get("races") or flt.get("race_has") or flt.get("name"):
        return True
    return bool(flt.get("civs")) and any(k in flt for k in ("cost_le", "cost_ge"))


KNOWN_KEYS = {"types", "not_types", "races", "race_has", "civs", "cost_le", "cost_ge", "name", "total_cost_le"}


def admits(flt: dict, x) -> bool:
    """静的に照合できるフィルタだけ照合する（知らない条件があれば合わないとみなす＝拾い過ぎない）。"""
    if set(flt) - KNOWN_KEYS:
        return False
    if "types" in flt and not set(flt["types"]) & set(x.types):
        return False
    if "not_types" in flt and set(flt["not_types"]) & set(x.types):
        return False
    if "races" in flt and not set(flt["races"]) & set(x.races or ()):
        return False
    if "race_has" in flt and not any(flt["race_has"] in r for r in (x.races or ())):
        return False
    if "civs" in flt and not set(flt["civs"]) & set(x.civs):
        return False
    c = x.cost if isinstance(x.cost, int) else None
    for k, ok in (("cost_le", lambda v: c is not None and c <= v), ("total_cost_le", lambda v: c is not None and c <= v),
                  ("cost_ge", lambda v: c is not None and c >= v)):
        if k in flt and not (isinstance(flt[k], int) and ok(flt[k])):
            return False
    if "name" in flt and flt["name"] not in (x.name, x.id):
        return False
    return True


def links(d) -> list[tuple[str, dict]]:
    """札 d が他の札を指すフィルタ [(種類, フィルタ)]。"""
    out = []
    for f in _faces(d):
        effs = [ab.get("effect") or [] for ab in (f.abilities or [])] + [getattr(f, "spell", None) or []]
        for eff in effs:
            for op in _walk(eff):
                sel = op.get("select") or {}
                z = sel.get("zone")
                zs = z if isinstance(z, list) else [z]
                if sel.get("owner", "you") in ("you", "self") and any(x in PUT_FROM for x in zs) and \
                        (op.get("op") == "play_free" or (op.get("op") == "move" and op.get("to") == "bz")):
                    out.append(("cheat", sel.get("filter") or {}))
        for ab in f.abilities or []:
            aff, mod = ab.get("affects"), ab.get("mod") or {}
            if ab.get("kind") == "static" and isinstance(aff, dict) and aff.get("owner", "you") in ("you", "self"):
                if aff.get("zone") == "hand" and isinstance(mod.get("cost"), int) and mod["cost"] < 0:
                    out.append(("reduce", aff.get("filter") or {}))
                elif aff.get("zone") in (None, "bz") and any(k in mod for k in ("grant", "allow", "breaks", "power")):
                    out.append(("grant", aff.get("filter") or {}))
            w = ab.get("when") or {}
            s = w.get("subject")
            if ab.get("kind") == "trigger" and w.get("event") in TRIG_EVENTS and isinstance(s, dict) \
                    and s.get("owner", "you") in ("you", "self"):
                out.append(("trigger", s.get("filter") or {}))
    return out


def _strong_from_yaml(y: dict, thr: float) -> set[str]:
    out = set()
    for x in y.get("screened_attack") or []:
        s = (x.get("synergy_level1") or {}).get("broken") or {}
        if (s.get("main_a") or 0) >= thr:
            out.add(x["enabler"])
        if (s.get("main_b") or 0) >= thr:
            out.add(x["payoff"])
    return out


def pick(rules, *, strong: set[str] = frozenset(), limit: int = 60, per: int = 2, max_turn: int = 4) -> dict:
    """直接つながる組を拾う。戻り値 {pairs: [...], excluded_missing: [...], counts}。"""
    from collections import Counter

    from ..eval import speed_bound as SB
    from .basebuild import _test, missing_effect
    pool = {i: d for i, d in rules.cards.items() if not _test(i) and isinstance(d.cost, int)}
    missing = sorted(i for i, d in pool.items() if missing_effect(d))
    ok = {i: d for i, d in pool.items() if i not in missing and i not in strong}
    cands = {}
    for a, da in sorted(ok.items()):
        if da.cost > 4:
            continue
        for kind, flt in links(da):
            if not specific(flt):
                continue
            cap = 8 if kind == "cheat" else 4
            for b, db in ok.items():
                if b == a or db.name == da.name or db.cost > cap or "creature" not in db.types:
                    continue
                if admits(flt, db):
                    cands.setdefault((a, b), set()).add(kind)
    ranked = sorted(cands.items(), key=lambda kv: (-len(kv[1]), ok[kv[0][0]].cost + ok[kv[0][1]].cost, kv[0]))
    out, cnt = [], Counter()
    for (a, b), kinds in ranked:
        if cnt[a] >= per or cnt[b] >= per:
            continue
        t = SB.static_bound(rules, [a, b])["turn"]
        if t is None or t > max_turn:
            continue
        out.append({"a": a, "b": b, "kinds": sorted(kinds), "turn": t, "names": [ok[a].name, ok[b].name]})
        cnt[a] += 1
        cnt[b] += 1
        if len(out) >= limit:
            break
    return {"pairs": out, "linked": len(cands), "excluded_missing": missing, "excluded_strong": sorted(strong)}


def vanillas(rules) -> list[str]:
    out = []
    for i, d in sorted(rules.cards.items()):
        if i.startswith("T") or "creature" not in d.types or getattr(d, "faces", None) or not isinstance(d.cost, int):
            continue
        if d.abilities or d.keywords or (d.text or "").strip() or "evolution" in d.types:
            continue
        out.append(i)
    return out


def vanilla_for(rules, cid, pool) -> str:
    c = rules.cards[cid]
    cost = c.cost if isinstance(c.cost, int) else 3
    return min(pool, key=lambda v: (abs(rules.cards[v].cost - cost), 0 if set(c.civs) & set(rules.cards[v].civs) else 1, v))


def four_decks(rules, a, b, pool) -> tuple[dict, dict]:
    from .basebuild import COPIES, base_deck, fillers
    core = {a: COPIES, b: COPIES}
    d = base_deck(core, fillers(rules, core))
    va, vb = vanilla_for(rules, a, pool), vanilla_for(rules, b, pool)
    decks = {"ab": d, "a": [vb if x == b else x for x in d], "b": [va if x == a else x for x in d],
             "none": [va if x == a else vb if x == b else x for x in d]}
    return decks, {"vanilla": [va, vb]}


def measure(rules, pairs, *, seeds: int = 40, opp=1, ref="2b", turn: int = 4, budget: int = 200, workers: int = 4,
            ckpt: Path | None = None, log=print) -> dict:
    """4デッキ比較。ckpt を渡すと相手ごとの局の結果を途中保存し、あれば読み直す。"""
    from ..eval import attack as A
    from ..eval.parallel import map_ordered
    pool = vanillas(rules)
    decks, meta = {}, {}
    for p in pairs:
        k = f"{p['a']}+{p['b']}"
        ds, m = four_decks(rules, p["a"], p["b"], pool)
        meta[k] = {**p, **m}
        for t, d in ds.items():
            decks[f"{k}#{t}"] = d
    jobs = [(n, s) for n in decks for s in range(1, seeds + 1)]
    out = {}
    for tag, lvl in (("base", opp), ("ref", ref)):
        if lvl is None:
            continue
        f = ckpt.with_suffix(f".{tag}.json") if ckpt else None
        if f and f.exists():
            flat = json.loads(f.read_text(encoding="utf-8"))
        else:
            def one(j, lvl=lvl):
                try:
                    return A.run_one(rules, decks[j[0]], j[1], opp_level=lvl, max_turn=turn, budget=budget)
                except Exception as ex:   # 1局の失敗は記録して続ける
                    return {"seed": j[1], "kill_turn": None, "error": f"{type(ex).__name__}: {ex}"[:200], "snaps": {}}
            t0 = time.time()
            flat = map_ordered(one, jobs, workers)
            log(f"相手 {lvl}: {len(jobs)}局 {time.time()-t0:.0f}s")
            if f:
                f.write_text(json.dumps(flat, ensure_ascii=False, default=str), encoding="utf-8")
        rows = {}
        for (n, _), r in zip(jobs, flat):
            rows.setdefault(n, []).append(r)
        for k in meta:
            g = [rows[f"{k}#{t}"] for t in ("ab", "a", "b", "none")]
            out.setdefault(k, {**meta[k], "by_opp": {}})["by_opp"][str(lvl)] = {v: A.pair_interaction(*g, turn, v) for v in VALUES}
    return out


def significant(x: dict, lvl="1") -> list[str]:
    b = x["by_opp"].get(str(lvl)) or {}
    return [v for v, s in b.items() if s.get("ci95") and s["ci95"][0] > 0]


def record(results: dict, path: Path, note: str) -> int:
    """candidates.yaml の synergy_hunt を書き直す（他の節には触れない）。値の記録のみ、足切りしない。"""
    s = path.read_text(encoding="utf-8")
    head = "\n# synergy_hunt:"
    if head in s:
        s = s[:s.index(head)]
    rows = sorted(results.values(), key=lambda x: -((x["by_opp"].get("1") or {}).get("broken", {}).get("diff") or 0))
    lines = [head + f" 直接つながる2枚組の相乗分（dmsim/discovery/synergy_hunt.py）。{note}", "synergy_hunt:"]
    for x in rows:
        y = {"a": x["a"], "b": x["b"], "names": x["names"], "kinds": x["kinds"], "static_turn": x["turn"], "vanilla": x["vanilla"],
             "significant_level1": significant(x)}
        for lvl, b in x["by_opp"].items():
            y[f"synergy_{lvl}"] = {v: {"diff": s["diff"], "ci95": list(s["ci95"]) if s["ci95"] else None,
                                       "main_a": s["main_a"]["diff"], "main_b": s["main_b"]["diff"]} for v, s in b.items()}
        lines.append("  - " + json.dumps(y, ensure_ascii=False))
    path.write_text(s.rstrip("\n") + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return len(rows)


def run(rules=None, *, limit: int = 60, seeds: int = 40, opp=1, ref="2b", strong: float = 0.3, workers: int = 4,
        out: Path | None = None, write: bool = True, log=print) -> dict:
    """拾う→測る→記録する、を1回で回す。"""
    import yaml

    from ..base.store import REPO
    from ..cards.defs import load_rules
    rules = rules or load_rules()
    cpath = REPO / "data/registry/candidates.yaml"
    y = yaml.safe_load(cpath.read_text(encoding="utf-8")) or {}
    st = _strong_from_yaml(y, strong)
    pk = pick(rules, strong=st, limit=limit)
    log(f"つながる組 {pk['linked']}、選んだ組 {len(pk['pairs'])}、単独で強い札 {len(st)}、効果の欠けた札 {len(pk["excluded_missing"])}")
    res = measure(rules, pk["pairs"], seeds=seeds, opp=opp, ref=ref, workers=workers, ckpt=out, log=log)
    hits = [k for k, x in res.items() if significant(x)]
    log(f"相乗分の区間が0を超えた組 {len(hits)}")
    if write:
        record(res, cpath, f"段階{opp}・{seeds}局、参考 {ref}、{time.strftime('%Y-%m-%d')}。")
    summary = {"pick": pk, "results": res, "hits": hits}
    if out:
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return summary


def hunt_hook(**kw) -> dict:
    """tools/hunt.py などから呼ぶ口。run と同じ引数。結果の要約（hits と組の数）を返す。"""
    s = run(**kw)
    return {"pairs": len(s["pick"]["pairs"]), "hits": s["hits"]}
