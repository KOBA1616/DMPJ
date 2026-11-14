"""攻撃型の目盛り（dmsim/eval/attack.py）の対照と、速い攻撃型の組の探索（2026-11-14）。

  python tools/attack_screen.py control --seeds 20 --out control.json
      既存デッキ（data/decks/ の saga・akashic・knight_dmc・beat_fire_gaga）とランダムなデッキを同じ条件で測る。
  python tools/attack_screen.py search --top 12 --seeds 20 --out search.json
      効果データから「早いターンに打点を増やす組」を静的にふるい、basebuild でデッキにして上位を目盛りで測る。

静的なふるい（カード名は見ない。サイキック・GR は対象外＝実カードの効果データに無い）:
- 打点の札（payoff）: クリーチャーで、ブレイク数（W・T・Q・ワールド・パワード）が2以上、または自分がスピードアタッカー。
- 打点を早く増やす札（enabler）: 他のクリーチャーにスピードアタッカーを与える常在能力、payoff を出せる踏み倒し
  （speed_bound.enablers: play_free / 手札・山札・墓地・マナ・盾から場へ）、アンタップを含む効果（追加攻撃）、攻撃時に場へ出す効果。
- 取り除き試験: 組の2種を抜いて同じ枚数のつなぎの札に置き換えたデッキも測り、4T以内のキルの差を組の寄与（pair_gain_4t）とする。
  相手が展開しない今の抵抗では、軽いクリーチャーを並べるだけで4ターン目に殴り切れる局が多いので、組の値は必ずこの差で読む。
- 組 (enabler, payoff) の点: payoff のブレイク数 + 出してすぐ攻撃できるか（スピードアタッカー持ち・付与）+ 追加攻撃。
  速さの上限（speed_bound.static_bound）が 3 以下の組だけ（3ターン目までに両方を出せる）。点の高い順、同点は上限ターンの早い順。
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine import zone_graph as Z  # noqa: E402
from dmsim.eval import attack as A  # noqa: E402
from dmsim.eval import speed_bound as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
KNOWN_DECKS = ("saga", "akashic", "knight_dmc")   # beat_fire_gaga は未変換の札があり40枚にならないので除く
BREAKS = {"double_breaker": 2, "triple_breaker": 3, "quad_breaker": 4, "world_breaker": 5, "powered_breaker": 2}
_R = None


def _rules():
    global _R
    if _R is None:
        _R = load_rules()
    return _R


def _job(args):
    deck, seed, kw = args
    try:
        return A.run_one(_rules(), deck, seed, **kw)
    except Exception as ex:   # 1局の失敗は記録して続ける
        return {"seed": seed, "first": seed % 2, "opp": None, "kill_turn": None, "kind": None, "via": None, "lost": None,
                "error": f"{type(ex).__name__}: {ex}"[:200], "marks": {}}


def measure_many(decks: dict, seeds, procs=4, **kw) -> dict:
    jobs = [(d, s, kw) for d in decks.values() for s in seeds]
    with Pool(procs) as p:
        rows = p.map(_job, jobs)
    out, i = {}, 0
    for name in decks:
        out[name] = rows[i:i + len(seeds)]
        i += len(seeds)
    return out


def _faces(d):
    return list(getattr(d, "faces", None) or []) or [d]


def feats(d) -> dict:
    kws = {ab.get("keyword") for f in _faces(d) for ab in (f.abilities or [])}
    grant = False
    rearm = False
    put_on_attack = False
    for f in _faces(d):
        for ab in f.abilities or []:
            mod = ab.get("mod") or {}
            if ab.get("kind") == "static" and ab.get("affects") != "self" and "speed_attacker" in (mod.get("allow") or []):
                grant = True
            eff = ab.get("effect") or []
            if ab.get("kind") in ("trigger", "declare") and Z._rearms(eff):
                rearm = True
            w = ab.get("when") or {}
            if ab.get("kind") == "trigger" and w.get("event") == "attack":
                if any(m.dst == "bz" and m.owner == "you" for m in Z._moves_of(eff)):
                    put_on_attack = True
    return {"creature": "creature" in d.types, "breaks": max([BREAKS.get(k, 1) for k in kws if k] or [1]),
            "haste": "speed_attacker" in kws, "grant": grant, "rearm": rearm, "put_on_attack": put_on_attack,
            "no_attack": bool({"cannot_attack", "cannot_attack_player"} & kws)}


def pairs(rules, ids, raw_missing) -> list[dict]:
    F = {i: feats(rules.cards[i]) for i in ids}
    payoff = [i for i in ids if F[i]["creature"] and not F[i]["no_attack"] and (F[i]["breaks"] >= 2 or F[i]["haste"])]
    ens = S.enablers(rules, ids)   # {出される札: [出す札]}（効果データの play_free / 場へ動かす）
    grant = [i for i in ids if F[i]["grant"]]
    extra = [i for i in ids if F[i]["rearm"] or F[i]["put_on_attack"]]
    out = {}
    for p in payoff:
        srcs = set(ens.get(p, [])) | set(grant) | set(extra)
        for e in srcs:
            if e == p or e in raw_missing or p in raw_missing:
                continue
            how = []
            if e in ens.get(p, []):
                how.append("踏み倒し")
            if F[e]["grant"]:
                how.append("スピードアタッカー付与")
            if F[e]["rearm"]:
                how.append("追加攻撃")
            if F[e]["put_on_attack"]:
                how.append("攻撃時に展開")
            score = F[p]["breaks"] + (1 if (F[p]["haste"] or F[e]["grant"]) else 0) + (1 if F[e]["rearm"] else 0) + 0.5 * len(how)
            out[(e, p)] = {"enabler": e, "payoff": p, "how": how, "score": score}
    return list(out.values())


def deck_of(name):
    return yaml.safe_load((ROOT / "data/decks" / f"{name}.yaml").read_text(encoding="utf-8"))["deck"]


VANILLA = ("dm01-075", "dm01-083", "dm01-090", "dm01-097")   # 2コストのバニラ（キーワードも効果もない札）を10枚ずつ＝「並べるだけ」の対照


def opp_arg(x: str):
    return int(x) if x.isdigit() else x


def random_decks(rules, k, seed=20261114):
    from dmsim.discovery import basebuild as B
    rng = random.Random(seed)
    pool = sorted(i for i, d in rules.cards.items() if not B._test(i) and isinstance(d.cost, int) and not B.missing_effect(d))
    return {f"random{j + 1}": [x for x in rng.sample(pool, 10) for _ in range(4)] for j in range(k)}


def cmd_control(a):
    rules = _rules()
    decks = {n: deck_of(n) for n in KNOWN_DECKS}
    decks.update(random_decks(rules, a.random))
    decks["vanilla"] = [x for x in VANILLA for _ in range(10)]
    t0 = time.time()
    rows = measure_many(decks, range(1, a.seeds + 1), a.procs, opp_level=a.opp, max_turn=a.max_turn, budget=a.budget)
    out = {n: {"summary": A.summarize(r, a.max_turn), "rows": r} for n, r in rows.items()}
    for n, x in out.items():
        s = x["summary"]
        print(f"{n}: 3T {s['kill'][3]['k']}/{s['games']} 4T {s['kill'][4]['k']}/{s['games']} 分布 {s['dist']} 勝ち方 {s['via']} 負け {s['lost']} 誤り {s['errors']}", flush=True)
    Path(a.out).write_text(json.dumps({"args": vars(a), "seconds": round(time.time() - t0), "decks": decks, "results": out},
                                      ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def cmd_search(a):
    from dmsim.base.loopspec import LoopSpec, Pred
    from dmsim.discovery import basebuild as B
    rules = _rules()
    t0 = time.time()
    ids = sorted(i for i, d in rules.cards.items() if not B._test(i) and isinstance(d.cost, int))
    missing = {i for i in ids if B.missing_effect(rules.cards[i])}
    ps = pairs(rules, ids, missing)
    ps.sort(key=lambda p: (-p["score"], p["enabler"], p["payoff"]))
    fast, picked, seen, checked = [], [], set(), 0
    for p in ps:                         # 点の高い順に速さの上限を当て、上位 top 組が揃ったら止める（打ち切り位置を記録）
        if p["payoff"] in seen or p["enabler"] in seen:
            continue                     # 同じ payoff・同じ enabler に偏らないよう、それぞれ1回まで
        checked += 1
        t = S.static_bound(rules, [p["enabler"], p["payoff"]])["turn"]
        if t is None or t > 3:
            continue
        p = {**p, "turn": t}
        fast.append(p)
        seen |= {p["payoff"], p["enabler"]}
        picked.append(p)
        if len(picked) >= a.top:
            break
    print(f"組 {len(ps)}、上限を当てた組 {checked}、選んだ組 {len(picked)} {time.time()-t0:.0f}s", flush=True)
    decks, built = {}, {}
    for p in picked:
        core = {p["enabler"]: B.COPIES, p["payoff"]: B.COPIES}
        ls = LoopSpec(name="atk", kind="deterministic", minimal=[Pred(0, {"name": p["enabler"]}, 1, ">=", "bz"),
                                                                  Pred(0, {"name": p["payoff"]}, 1, ">=", "bz")])
        if a.no_basebuild:
            deck, added = B.base_deck(core, B.fillers(rules, core)), []
        else:
            b = B.build(rules, core, ls, max_steps=a.steps)
            deck, added = b.deck, b.added
        key = f"{p['enabler']}+{p['payoff']}"
        decks[key] = deck
        built[key] = {**p, "names": [rules.cards[p["enabler"]].name, rules.cards[p["payoff"]].name], "added": added}
        print(f"デッキ {key} {built[key]['names']} 基盤 {[x['name'] for x in added]} {time.time()-t0:.0f}s", flush=True)
    # 取り除き試験: 組の2種8枚を、デッキで最も多いつなぎの札に置き換えたデッキも測る（組の寄与＝差）
    from collections import Counter
    nopair = {}
    for k, d in decks.items():
        pair = set(k.split("+"))
        fill = next(x for x, _ in Counter(d).most_common() if x not in pair)
        nopair[k + "#no_pair"] = [fill if x in pair else x for x in d]
    rnd = random_decks(rules, a.random, seed=20261115)
    rows = measure_many({**decks, **nopair, **rnd}, range(1, a.seeds + 1), a.procs, opp_level=a.opp, max_turn=a.max_turn, budget=a.budget)
    res = {}
    for n, r in rows.items():
        s = A.summarize(r, a.max_turn)
        res[n] = {"summary": s, "rows": r, **({"pair": built[n]} if n in built else {})}
        if n in built:
            base = A.summarize(rows[n + "#no_pair"], a.max_turn)
            res[n]["pair_gain_4t"] = s["kill"][4]["k"] - base["kill"][4]["k"]
            res[n]["contribution"] = {t: A.pair_contribution(r, rows[n + "#no_pair"], t) for t in (3, 4, a.max_turn)}
        nm = "+".join(built[n]["names"]) if n in built else n
        c = res[n].get("contribution", {}).get(4)
        cs = f" 寄与4T {c['diff']:+.2f} 95%{c['ci95']} 上{c['better']}/下{c['worse']}" if c else ""
        print(f"{nm}: 3T {s['kill'][3]['k']}/{s['games']} 4T {s['kill'][4]['k']}/{s['games']}（蓄積 {s['kill'][4]['accumulated']}） 分布 {s['dist']} 負け {s['lost']}{cs} 誤り {s['errors']}", flush=True)
    Path(a.out).write_text(json.dumps({"args": vars(a), "seconds": round(time.time() - t0), "pairs": len(ps), "checked": checked, "fast": len(fast),
                                       "fast_top": fast[:100], "decks": {**decks, **rnd}, "results": res},
                                      ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["control", "search"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--random", type=int, default=5)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--steps", type=int, default=3)
    ap.add_argument("--no-basebuild", action="store_true")
    ap.add_argument("--opp", type=opp_arg, default=A.DEFAULT_OPP, help="相手の段階 0 / 1 / 2a（=2、速攻寄り）/ 2b（受け寄り）")
    ap.add_argument("--max-turn", type=int, default=6)
    ap.add_argument("--budget", type=int, default=200)
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    {"control": cmd_control, "search": cmd_search}[a.mode](a)


if __name__ == "__main__":
    main()
