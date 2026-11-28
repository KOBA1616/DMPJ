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
from dmsim.base.registry import load_candidates, load_candidates_doc  # noqa: E402
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


def known_pairs() -> dict:
    """既知デッキの中核（ループ・エンジンの札、勝ち手段は除く）。登録簿の候補 data/registry/candidates.yaml から。"""
    out = {}
    for c in load_candidates():
        if c.get("id") in KNOWN_DECKS:
            out[c["id"]] = [x["id"] for x in c.get("core") or [] if x.get("part", "loop") != "win"]
    return out


def contrib_lines(name, with_rows, without_rows, ts=(3, 4)) -> dict:
    out = {v: {t: A.pair_contribution(with_rows, without_rows, t, v) for t in ts} for v in A.VALUES}
    for v, x in out.items():
        c = x[4]
        print(f"  {name} 寄与[{v}]4T {c['diff']:+.2f} 95%{c['ci95']} 上{c['better']}/下{c['worse']} n={c['n']}", flush=True)
    return out


def cmd_known(a):
    """既知デッキの中核を取り除いた対照と同じシードで比べる（組の寄与を既知デッキにも）。"""
    from dmsim.eval.contrib import remove_pair
    kp = known_pairs()
    decks = {}
    for n, core in kp.items():
        d = deck_of(n)
        decks[n] = d
        decks[n + "#no_pair"] = remove_pair(d, core)
    rows = measure_many(decks, range(1, a.seeds + 1), a.procs, opp_level=a.opp, max_turn=a.max_turn, budget=a.budget)
    res = {}
    for n in kp:
        res[n] = {"core": kp[n], "summary": A.summarize(rows[n], a.max_turn), "base": A.summarize(rows[n + "#no_pair"], a.max_turn),
                  "contribution_by": contrib_lines(n, rows[n], rows[n + "#no_pair"]), "rows": rows[n], "rows_no_pair": rows[n + "#no_pair"]}
    Path(a.out).write_text(json.dumps({"args": vars(a), "results": res}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def _sig(ci, d):
    return ci is not None and ci[0] > 0


def cmd_wide(a):
    """静的ふるいの組を広く（--limit 組）測る。基盤選びは使わずつなぎ札で埋める（数百組を回すため）。
    値は手前の値の寄与（kill / left / broken / board、自分の --turn ターン目の終わり）。同じ中身の対照デッキは1回だけ測る。
    どれかの値の95%区間が0を超えた組だけ --confirm 局で測り直し、参考の相手（--ref、既定 2b）も併記する。
    基準の相手は段階1（トリガーデッキ、ユーザー決定 2026-11-14）。"""
    from collections import Counter
    from dmsim.discovery import basebuild as B
    from dmsim.eval.contrib import remove_pair
    rules = _rules()
    t0 = time.time()
    stage = Path(a.out).with_suffix(".screen.json")
    if a.resume and stage.exists():
        z = json.loads(stage.read_text(encoding="utf-8"))
        hits = list(z["hits"])
        if a.near is not None:   # 境目に近い組も確かめる（どれかの値の区間の下端が -near より上）
            hits += [k for k, r in z["results"].items() if k not in hits
                     and any(x["ci95"] and x["ci95"][0] > -a.near and x["diff"] > 0 for x in r["contribution"].values())]
        return _confirm(a, rules, z["results"], hits, z["decks"], z["ctrl_of"], z["uniq"], z["picked"], t0)
    ids = sorted(i for i, d in rules.cards.items() if not B._test(i) and isinstance(d.cost, int))
    missing = {i for i in ids if B.missing_effect(rules.cards[i])}
    ps = pairs(rules, ids, missing)
    ps.sort(key=lambda p: (-p["score"], p["enabler"], p["payoff"]))
    picked, cnt = [], Counter()
    for p in ps:                       # 同じ札が並びすぎないよう、1枚あたり --per 組まで
        if cnt[p["payoff"]] >= a.per or cnt[p["enabler"]] >= a.per:
            continue
        t = S.static_bound(rules, [p["enabler"], p["payoff"]])["turn"]
        if t is None or t > 3:
            continue
        picked.append({**p, "turn": t})
        cnt[p["payoff"]] += 1
        cnt[p["enabler"]] += 1
        if len(picked) >= a.limit:
            break
    print(f"組 {len(ps)}、選んだ組 {len(picked)} {time.time()-t0:.0f}s", flush=True)
    decks, ctrl_of, uniq = {}, {}, {}
    for p in picked:
        core = {p["enabler"]: B.COPIES, p["payoff"]: B.COPIES}
        d = B.base_deck(core, B.fillers(rules, core))
        k = f"{p['enabler']}+{p['payoff']}"
        decks[k] = d
        ctrl = remove_pair(d, [p["enabler"], p["payoff"]])
        h = json.dumps(sorted(ctrl))
        uniq.setdefault(h, ctrl)
        ctrl_of[k] = h
    ctrl_names = {h: f"#ctrl{i}" for i, h in enumerate(uniq)}
    print(f"対照デッキ {len(uniq)} 種", flush=True)
    kw = dict(opp_level=a.opp, max_turn=a.turn, budget=a.budget)
    seeds = range(1, a.seeds + 1)
    rows = measure_many({**decks, **{ctrl_names[h]: d for h, d in uniq.items()}}, seeds, a.procs, **kw)
    res, hits = {}, []
    for k in decks:
        base = rows[ctrl_names[ctrl_of[k]]]
        cb = {v: A.pair_contribution(rows[k], base, a.turn, v) for v in A.VALUES}
        p = next(x for x in picked if f"{x['enabler']}+{x['payoff']}" == k)
        res[k] = {"pair": {**p, "names": [rules.cards[p["enabler"]].name, rules.cards[p["payoff"]].name]},
                  "contribution": cb, "errors": sum(1 for r in rows[k] if r["error"])}
        if any(_sig(x["ci95"], x["diff"]) for x in cb.values()):
            hits.append(k)
    print(f"区間が0を超えた組 {len(hits)} {time.time()-t0:.0f}s", flush=True)
    stage = Path(a.out).with_suffix(".screen.json")   # 途中保存（確認の段で止まっても、ふるいの結果は残る）
    stage.write_text(json.dumps({"args": vars(a), "picked": len(picked), "controls": len(uniq), "results": res, "hits": hits,
                                 "decks": decks, "ctrl_of": ctrl_of, "uniq": uniq}, ensure_ascii=False, default=str), encoding="utf-8")
    return _confirm(a, rules, res, hits, decks, ctrl_of, uniq, len(picked), t0)


def _confirm(a, rules, res, hits, decks, ctrl_of, uniq, picked_n, t0):
    ctrl_names = {h: f"#ctrl{i}" for i, h in enumerate(uniq)}
    kw = dict(opp_level=a.opp, max_turn=a.turn, budget=a.budget)
    conf = {}
    if hits and a.confirm:
        cs = range(1, a.confirm + 1)
        need = {k: decks[k] for k in hits}
        need.update({ctrl_names[ctrl_of[k]]: uniq[ctrl_of[k]] for k in hits})
        def cached(tag, lvl):   # 段ごとに途中保存（止まっても済んだ段は測り直さない）
            f = Path(a.out).with_suffix(f".confirm_{tag}.json")
            if a.resume and f.exists():
                return json.loads(f.read_text(encoding="utf-8"))
            r = measure_many(need, cs, a.procs, **{**kw, "opp_level": lvl})
            f.write_text(json.dumps(r, ensure_ascii=False, default=str), encoding="utf-8")
            return r
        r2 = cached("base", a.opp)
        r1 = cached("ref", a.ref)
        for k in hits:
            c = ctrl_names[ctrl_of[k]]
            conf[k] = {"opp": {str(a.opp): {v: A.pair_contribution(r2[k], r2[c], a.turn, v) for v in A.VALUES},
                               str(a.ref): {v: A.pair_contribution(r1[k], r1[c], a.turn, v) for v in A.VALUES}}}
            x = conf[k]["opp"][str(a.opp)]
            print(f"確認 {'+'.join(res[k]['pair']['names'])}: " + " ".join(f"{v} {x[v]['diff']:+.2f}{x[v]['ci95']}" for v in A.VALUES), flush=True)
    Path(a.out).write_text(json.dumps({"args": vars(a), "seconds": round(time.time() - t0), "picked": picked_n, "controls": len(uniq),
                                       "results": res, "hits": hits, "confirm": conf}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def vanillas(rules) -> list[str]:
    """効果もキーワードもないクリーチャー（テキストが空、ツインパクトでない）。相乗分の対照の置き換え札。"""
    out = []
    for i, d in sorted(rules.cards.items()):
        if i.startswith("T") or "creature" not in d.types or getattr(d, "faces", None) or not isinstance(d.cost, int):
            continue
        if d.abilities or d.keywords or (d.text or "").strip() or "evolution" in d.types:
            continue
        out.append(i)
    return out


def vanilla_for(rules, cid, pool) -> str:
    """cid と同じコスト（無ければ近いコスト）で、文明が重なるバニラ。同点は ID 順。"""
    c = rules.cards[cid]
    cost = c.cost if isinstance(c.cost, int) else 3
    civ = set(c.civs)
    return min(pool, key=lambda v: (abs(rules.cards[v].cost - cost), 0 if civ & set(rules.cards[v].civs) else 1, v))


def cmd_synergy(a):
    """組の相乗分（2×2 の取り除き、eval.contrib.interaction）。candidates.yaml の screened_attack（または --pairs）の組を、
    両方あり・Aだけ・Bだけ・両方なしの4デッキで同じシードに測る。抜いた札は同じコスト・文明のバニラに置き換える。
    基準の相手 --opp と参考 --ref の段ごとに途中保存し、--resume で続きから。"""
    from dmsim.discovery import basebuild as B
    rules = _rules()
    t0 = time.time()
    y = load_candidates_doc()
    prs = [(x["enabler"], x["payoff"]) for x in y.get("screened_attack") or []]
    if a.pairs:
        prs = [tuple(x.split("+")) for x in a.pairs.split(",")]
    pool = vanillas(rules)
    decks, meta = {}, {}
    for ea, pb in prs:
        core = {ea: B.COPIES, pb: B.COPIES}
        d = B.base_deck(core, B.fillers(rules, core))
        va, vb = vanilla_for(rules, ea, pool), vanilla_for(rules, pb, pool)
        k = f"{ea}+{pb}"
        decks[k + "#ab"] = d
        decks[k + "#a"] = [vb if x == pb else x for x in d]
        decks[k + "#b"] = [va if x == ea else x for x in d]
        decks[k + "#none"] = [va if x == ea else vb if x == pb else x for x in d]
        meta[k] = {"names": [rules.cards[ea].name, rules.cards[pb].name], "vanilla": [va, vb],
                   "vanilla_names": [rules.cards[va].name, rules.cards[vb].name]}
    print(f"組 {len(prs)}、デッキ {len(decks)}、バニラ候補 {len(pool)} {time.time()-t0:.0f}s", flush=True)
    seeds = range(1, a.seeds + 1)
    kw = dict(max_turn=a.turn, budget=a.budget)
    out = {}
    for tag, lvl in (("base", a.opp), ("ref", a.ref)):
        f = Path(a.out).with_suffix(f".{tag}.json")
        if a.resume and f.exists():
            rows = json.loads(f.read_text(encoding="utf-8"))
        else:
            rows = measure_many(decks, seeds, a.procs, opp_level=lvl, **kw)
            f.write_text(json.dumps(rows, ensure_ascii=False, default=str), encoding="utf-8")
        for k in meta:
            g = [rows[k + s] for s in ("#ab", "#a", "#b", "#none")]
            out.setdefault(k, {**meta[k], "by_opp": {}})["by_opp"][str(lvl)] = {v: A.pair_interaction(*g, a.turn, v) for v in A.VALUES}
            if tag == "base":
                x = out[k]["by_opp"][str(lvl)]
                print(f"{'+'.join(meta[k]['names'])[:40]}: " + " ".join(f"{v} {x[v]['diff']:+.2f}{x[v]['ci95']}" for v in A.VALUES), flush=True)
        print(f"相手 {lvl} 済み {time.time()-t0:.0f}s", flush=True)
    Path(a.out).write_text(json.dumps({"args": vars(a), "seconds": round(time.time() - t0), "results": out, "decks": decks},
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
            res[n]["contribution_by"] = contrib_lines(n[:24], r, rows[n + "#no_pair"])
        nm = "+".join(built[n]["names"]) if n in built else n
        c = res[n].get("contribution", {}).get(4)
        cs = f" 寄与4T {c['diff']:+.2f} 95%{c['ci95']} 上{c['better']}/下{c['worse']}" if c else ""
        print(f"{nm}: 3T {s['kill'][3]['k']}/{s['games']} 4T {s['kill'][4]['k']}/{s['games']}（蓄積 {s['kill'][4]['accumulated']}） 分布 {s['dist']} 負け {s['lost']}{cs} 誤り {s['errors']}", flush=True)
    Path(a.out).write_text(json.dumps({"args": vars(a), "seconds": round(time.time() - t0), "pairs": len(ps), "checked": checked, "fast": len(fast),
                                       "fast_top": fast[:100], "decks": {**decks, **rnd}, "results": res},
                                      ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["control", "search", "known", "wide", "synergy"])
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
    ap.add_argument("--limit", type=int, default=300, help="wide: 測る組の数")
    ap.add_argument("--per", type=int, default=3, help="wide: 1枚の札が入る組の上限")
    ap.add_argument("--turn", type=int, default=4, help="wide: 値を読むターン（この先は回さない）")
    ap.add_argument("--ref", type=opp_arg, default="2b", help="wide: 確認の時に併記する参考の相手")
    ap.add_argument("--resume", action="store_true", help="wide: 途中保存（<out>.screen.json）があれば、ふるいを飛ばして確認から")
    ap.add_argument("--pairs", default="", help="synergy: 組を明示（A+B をカンマ区切り）。省くと candidates.yaml の screened_attack")
    ap.add_argument("--near", type=float, default=None, help="wide --resume: 区間の下端が -near より上の組も確認に入れる")
    ap.add_argument("--confirm", type=int, default=40, help="wide: 区間が0を超えた組を測り直す局数")
    a = ap.parse_args()
    {"control": cmd_control, "search": cmd_search, "known": cmd_known, "wide": cmd_wide, "synergy": cmd_synergy}[a.mode](a)


if __name__ == "__main__":
    main()
