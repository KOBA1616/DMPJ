"""コンボ発見 v2 の実行ツール。検証はエンジン判定と変換判定に分ける（dmsim/discovery/hunt2.py）。

使い方:
  PYTHONPATH=. python tools/combo_hunt2.py --controls                 陽性対照（akashic / saga を通常経路、tenmon を記録手順の再生で通す）
  PYTHONPATH=. python tools/combo_hunt2.py --sample 12 --pair-limit 3000 --singles   スモーク（小規模）
  PYTHONPATH=. python tools/combo_hunt2.py --sample 300 --workers 4 --out data/combohunt/results2.jsonl

流れ: 静的ふるい（段0）→ 層化抽出 → エンジン判定（段1: 揃った局面から探索）
→ 変換判定（段1.5: 資源が莫大化した局面＋変換札）→ 開幕検証（段2: 役割補完デッキで通常開幕）。
結果は --out に1候補1行で追記し、既に記録した候補は飛ばす（再開可能）。
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.discovery import hunt2  # noqa: E402

W: dict = {}


def _init_worker():
    W["rules"] = load_rules()
    W["by_card"] = hunt2.bundles_by_card(W["rules"])
    W["catalog"] = hunt2.conversion_catalog(W["rules"], W["by_card"])


def _ensure():
    if "rules" not in W:
        _init_worker()
    return W["rules"], W["by_card"], W["catalog"]


def run_candidate(cand: dict, cfg: dict) -> dict:
    """1候補の全段（エンジン→変換→開幕）。例外は記録に残して止めない。"""
    rules, by_card, catalog = _ensure()
    t0 = time.time()
    rec: dict = {k: cand[k] for k in ("cards", "counts", "names", "score", "static", "stratum")}
    try:
        eng = hunt2.judge_engine(rules, cand["counts"], by_card, budget=cfg["budget"],
                                 max_turn=cfg["engine_turns"], seeds=tuple(cfg["seeds"]))
        rec["engine"] = {k: eng[k] for k in ("pass", "kinds", "delta", "grown", "evidence")}
        rec["engine_rows"] = eng["rows"]
        conv_tried: list[str] = []
        if eng["pass"]:
            pairs = hunt2.pair_conversions(eng["grown"], eng["kinds"], catalog, limit=cfg["conv_per"])
            conv_results = []
            for pc in pairs:
                cv = hunt2.judge_conversion(rules, cand["counts"], [pc["card"]], eng["grown"], by_card,
                                            budget=cfg["conv_budget"], seeds=tuple(cfg["seeds"]))
                conv_tried.append(pc["card"])
                conv_results.append({"card": pc["card"], "name": pc["name"], "pass": cv["pass"],
                                     "rows": cv["rows"]})
            rec["conversion"] = conv_results
            deck = hunt2.build_deck_v2(rules, cand["counts"], conv_tried[:1])
            op = hunt2.judge_opening(rules, deck, budget=cfg["opening_budget"],
                                     max_turn=cfg["opening_turns"], seeds=tuple(cfg["seeds"]))
            rec["opening"] = op
            rec["deck"] = deck
    except Exception as ex:      # 1候補の失敗で全体を止めない
        rec["error"] = f"{type(ex).__name__}: {ex}"
    rec["seconds"] = round(time.time() - t0, 1)
    return rec


def run_tenmon_control() -> dict:
    """tenmon（天門ループ、種別 reroll）は中核の組ではなく記録手順が定義そのものなので、
    対照は「spec の board から記録手順を再生し、最後まで通って勝てるか」で確認する（evalstarts の汎用再生）。
    spec は修正済み（board.deck の並び替えで prepare なしに再生できる）を取り込んである。"""
    from dmsim.base.loopspec import LoopSpec
    from dmsim.engine import scenario
    from dmsim.engine.view import result_of
    from dmsim.eval import evalstarts
    rules, _, _ = _ensure()
    t0 = time.time()
    ls = LoopSpec.from_json(Path("data/loops/tenmon_initial.json").read_text(encoding="utf-8"))
    steps = evalstarts._steps(ls)
    e = scenario.build(rules, ls.source["board"])
    applied = 0
    for kind, keys, idx in steps:
        if result_of(e) is not None:
            break
        if not evalstarts._answer(e, kind, keys, idx):
            break
        applied += 1
    if applied == len(steps):
        e.advance()          # 最終手の解決を確定させる（eval.replay.replay_test と同じ終端処理）
    res = result_of(e)
    ok = applied == len(steps) and (res or {}).get("winner") == 0
    row = {"method": "recorded-line replay (evalstarts)", "steps_applied": applied,
           "steps_total": len(steps), "result": str(res), "pass": ok,
           "seconds": round(time.time() - t0, 1)}
    print(f"対照 tenmon: 再生 {applied}/{len(steps)} result={res} -> {'合格' if ok else '不合格'}"
          f" ({row['seconds']}s)", flush=True)
    return row


def run_controls(budget: int) -> dict:
    """陽性対照: 登録済みループ（akashic / saga）の入口 spec は使わず、
    中核の組 → 機械的な仕込み → エンジン判定／変換判定、という通常経路で通るかを見る。
    tenmon は種別が違う（記録手順型）ため、記録手順の再生で確認する。"""
    from dmsim.eval import loop_entry as le
    rules, by_card, _ = _ensure()
    out: dict = {}
    for name in ("akashic", "saga"):
        ls = le.load(name)
        full = le.core_alternatives(ls)[0]
        loop_only = le.core_alternatives(ls, "loop")[0]
        win_cards = sorted({i for g in le.win_groups(ls) for o in g["any"] for i in o})
        t0 = time.time()
        eng = hunt2.judge_engine(rules, full, by_card, budget=budget, max_turn=3, seeds=(1, 2))
        row = {"cards": full, "engine_full": {k: eng[k] for k in ("pass", "kinds", "delta", "grown", "evidence")},
               "engine_full_rows": eng["rows"]}
        if name == "saga":
            e2 = hunt2.judge_engine(rules, loop_only, by_card, budget=budget, max_turn=3, seeds=(1, 2))
            row["engine_loop_only"] = {k: e2[k] for k in ("pass", "kinds", "delta", "grown", "evidence")}
            row["engine_loop_rows"] = e2["rows"]
            conv_card = [c for c in win_cards if c == "dmrp03-s03"] or win_cards[:1]
            cv = hunt2.judge_conversion(rules, loop_only, conv_card, e2["grown"] or ["graveyard", "deck_thin"],
                                        by_card, budget=budget, seeds=(1, 2))
            row["conversion"] = {"cards": conv_card, "pass": cv["pass"], "rows": cv["rows"]}
            row["pass"] = bool(eng["pass"] and cv["pass"])
        else:
            row["pass"] = bool(eng["pass"])
        row["seconds"] = round(time.time() - t0, 1)
        out[name] = row
        print(f"対照 {name}: エンジン(full)={eng['pass']} {eng['kinds']} delta={eng['delta']}"
              + (f" / エンジン(loop部品のみ)={row.get('engine_loop_only', {}).get('pass')}"
                 f" / 変換={row.get('conversion', {}).get('pass')}" if name == "saga" else "")
              + f" ({row['seconds']}s)", flush=True)
    out["tenmon"] = run_tenmon_control()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--controls", action="store_true", help="陽性対照だけ回す")
    ap.add_argument("--controls-out", default=None, help="対照の結果 JSON の保存先")
    ap.add_argument("--sample", type=int, default=0, help="層化抽出して検証する候補数（0 = 列挙だけ）")
    ap.add_argument("--pair-limit", type=int, default=None, help="静的ふるいで調べる速い組の上限")
    ap.add_argument("--singles", action="store_true", help="単独で循環する札も候補に入れる")
    ap.add_argument("--budget", type=int, default=1000, help="エンジン判定の探索予算")
    ap.add_argument("--conv-budget", type=int, default=1000)
    ap.add_argument("--opening-budget", type=int, default=600)
    ap.add_argument("--engine-turns", type=int, default=3)
    ap.add_argument("--opening-turns", type=int, default=6)
    ap.add_argument("--conv-per", type=int, default=2, help="エンジン1件あたりの変換候補の試行数")
    ap.add_argument("--seeds", type=int, default=1, help="判定ごとのシード数（1, 2, ... と連番で使う）")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--time-cap", type=int, default=None, help="全体の打ち切り秒（途中結果は残る）")
    ap.add_argument("--out", default="data/combohunt/results2.jsonl")
    ap.add_argument("--candidates-out", default=None, help="静的ふるいの結果一覧を JSON で残す")
    a = ap.parse_args(argv)
    t0 = time.time()
    if a.controls:
        res = run_controls(a.budget)
        if a.controls_out:
            Path(a.controls_out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        ok = all(v.get("pass") for v in res.values())
        print(f"対照の総合: {'合格' if ok else '不合格あり'}（{time.time()-t0:.0f}s）")
        return 0 if ok else 1

    rules, by_card, _ = _ensure()
    print(f"load {time.time()-t0:.0f}s", flush=True)
    pool = hunt2.enumerate_candidates(rules, by_card, pair_limit=a.pair_limit, singles=a.singles)
    print(f"静的ふるい: full {len(pool['full'])} / engine {len(pool['engine'])} / 落ち {pool['drop']}"
          f"（{time.time()-t0:.0f}s）", flush=True)
    if a.candidates_out:
        Path(a.candidates_out).write_text(json.dumps(pool, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.sample <= 0:
        return 0
    items = pool["full"] + pool["engine"]
    rng = random.Random(42)
    picked = hunt2.stratified_sample(items, a.sample, rng)
    out = Path(a.out)
    done = set()
    if out.exists():
        done = {tuple(json.loads(l)["cards"]) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()}
    todo = [c for c in picked if tuple(c["cards"]) not in done]
    print(f"検証対象 {len(todo)} 件（抽出 {len(picked)}、済み {len(picked)-len(todo)}）", flush=True)
    cfg = {"budget": a.budget, "conv_budget": a.conv_budget, "opening_budget": a.opening_budget,
           "engine_turns": a.engine_turns, "opening_turns": a.opening_turns,
           "conv_per": a.conv_per, "seeds": list(range(1, a.seeds + 1))}
    out.parent.mkdir(parents=True, exist_ok=True)
    n_pass = n_conv = n_open = 0

    def emit(rec: dict):
        nonlocal n_pass, n_conv, n_open
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        ep = bool(rec.get("engine", {}).get("pass"))
        cp = any(c.get("pass") for c in rec.get("conversion", []))
        op = bool(rec.get("opening", {}).get("pass"))
        n_pass, n_conv, n_open = n_pass + ep, n_conv + cp, n_open + op
        print(f"[{'E' if ep else '-'}{'C' if cp else '-'}{'O' if op else '-'}] {' + '.join(rec['names'])}"
              f" ({rec['seconds']}s) {rec.get('error', '')}", flush=True)

    if a.workers > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(a.workers, initializer=_init_worker) as ex:
            futs = [ex.submit(run_candidate, c, cfg) for c in todo]
            for fu in futs:
                if a.time_cap and time.time() - t0 > a.time_cap:
                    print("時間上限に達したため打ち切ります（残りは再開時に続きます）", flush=True)
                    break
                emit(fu.result())
    else:
        for c in todo:
            if a.time_cap and time.time() - t0 > a.time_cap:
                print("時間上限に達したため打ち切ります（残りは再開時に続きます）", flush=True)
                break
            emit(run_candidate(c, cfg))
    print(f"完了: エンジン合格 {n_pass} / 変換合格 {n_conv} / 開幕合格 {n_open}"
          f"（全体 {time.time()-t0:.0f}s）", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
