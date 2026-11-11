"""キルが出ない原因の自動診断→改善→再測定。 python tools/auto_fix.py --combo saga --setup tests/saga_setup.yaml --need DEFN:1 --board graveyard:DEFN:1 --out logs/autofix.jsonl
検証専用(holdout)のコンボは拒否する。履歴は --out に追記（版つき規則 v0）。"""
import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.autofix import Knobs, Rule, autofix, harness_measure  # noqa: E402
from dmsim.defs import load_rules  # noqa: E402
from dmsim.eval.progress import ProgressSpec  # noqa: E402
from dmsim.search.leaf_parts import load_specs  # noqa: E402
from dmsim.solitaire import load_deck  # noqa: E402


def _board(xs):
    board: dict = {}
    for x in xs:
        z, d, *n = x.split(":")
        board.setdefault(z, {})[d] = int(n[0]) if n else 1
    return board


def _prep_ids(combo, rules, deck, opp, spec):
    """準備札: combos.yaml の prep_ids があればそれ、無ければプレイログから自動検出（dmsim.autofix.usage）。"""
    if combo.get("prep_ids"):
        return tuple(combo["prep_ids"])
    from dmsim.autofix.usage import auto_prep_ids
    return auto_prep_ids(rules, deck, opp, spec)


STATS_TURNS = 8      # 記録用の通しターン数（4ターンキルが評価指標。これは参考の記録で、採否には使わない）
STATS_SEEDS = 20


def _win_stats(a, ts, combos, mk):
    """各対象（holdout 除く）を現在の採用ノブで STATS_TURNS ターンまで回し、勝ち率（STATS_TURNS 以内）・4ターン内の勝ち率・最速勝ちターンを返す。"""
    from dmsim.autofix.loop import Knobs as K
    saved = (yaml.safe_load(Path(a.store).read_text(encoding="utf-8")) or {}) if a.store and Path(a.store).exists() else {}
    out = {}
    for t in ts:
        c = combos.get(t["combo"])
        if c is None or c.get("split") == "holdout":
            continue
        try:
            t2 = {**t, "seeds": STATS_SEEDS}
            kill = mk(t2, turns=STATS_TURNS)(K(**{**K().__dict__, **saved.get(t["combo"], {})}))["kill"]
        except Exception as e:                               # 記録用なので失敗しても日次は続ける
            out[t["combo"]] = {"error": f"{type(e).__name__}: {e}"[:200]}
            continue
        w = [x for x in kill if x is not None]
        out[t["combo"]] = {"n": len(kill), f"win_{STATS_TURNS}t": round(sum(x <= STATS_TURNS for x in w) / max(1, len(kill)), 3),
                           "win_4t": round(sum(x <= 4 for x in w) / max(1, len(kill)), 3), "fastest_turn": min(w) if w else None}
        print(f"勝ち率(通し{STATS_TURNS}ターン以内): {t['combo']} {out[t['combo']]}")
    return out


def run_batch(a, combos):
    from dmsim.autofix import run_targets
    import time
    t0 = time.time()
    ts = yaml.safe_load(Path(a.targets).read_text(encoding="utf-8"))["targets"]
    rules = load_rules()
    from dmsim.autofix.partsgenome import load_specs_evolved
    from dmsim.autofix.valuelearn import load_model
    from dmsim.autofix.reach import cards_ceiling
    import exec_tier
    specs = load_specs_evolved()                              # 進化で採用した部品の重み倍率を反映（data/autofix/parts.yaml）

    def mk(t, turns=None):
        from dmsim.autofix.batch import default_board, default_need
        cards = {x.split(":")[0]: int(x.split(":")[1]) if ":" in x else 1 for x in t["need"]} if t.get("need") else default_need(combos[t["combo"]])
        board = _board(t["board"]) if t.get("board") else default_board(combos[t["combo"]])
        deck, opp = load_deck(t["deck"]), load_deck(t["opp_deck"]) if t.get("opp_deck") else ["T001"] * 40
        spec, origin = exec_tier.exec_spec(rules, t, deck, cold=a.cold)      # 既定は実行層（仕込み済み開始）。到達層は理論上限で別に記録
        meas = harness_measure(rules, deck, opp, list(range(1, t.get("seeds", a.seeds) + 1)), spec,
                               ProgressSpec(board=board, cards=cards) if (cards or board) else None, specs[t["combo"]], max_turn=turns or a.turns, workers=a.workers,
                               prep_ids=_prep_ids(combos[t["combo"]], rules, deck, opp, specs[t["combo"]]),
                               value_model=load_model(t["combo"]))
        meas.info = {"tier": "cold" if a.cold else "exec", "setup_origin": origin,
                     "cards_ceiling": round(cards_ceiling(deck, cards, a.turns), 4)}   # デッキだけで決まる「部品がそろう」確率の上限
        return meas
    from dmsim.autofix import selfheal
    timing = {}                                               # 段階ごとの所要秒と割当（枠の配分を数字で見直す用）。data/autofix/timing_history.jsonl に1日1行残す

    def timed(name, fn, alloc=None):
        ts0 = time.time()
        try:
            return fn()
        finally:
            timing[name] = {"sec": round(time.time() - ts0), **({"alloc": int(alloc)} if alloc else {})}
    td0 = time.time()
    for r in run_targets(ts, combos, mk, Rule(turn=a.turns), a.rounds, a.out, a.store, health=a.health):
        print(r)
    timing["diagnose"] = {"sec": round(time.time() - td0)}
    stats = _win_stats(a, ts, combos, mk) if a.total_seconds else {}                      # 記録用: 通しターン STATS_TURNS 以内の勝ち率と最速勝ちターン（評価指標の4ターンは変えない）
    timing["win_stats"] = {"sec": round(time.time() - td0 - timing["diagnose"]["sec"])}
    from dmsim.eval.vgate import stage_path as vgate_stage_path
    vg = [t["combo"] for t in ts if t["combo"] in combos and combos[t["combo"]].get("split") != "holdout" and vgate_stage_path(t["combo"])]
    VGATE_TOTAL = min(2400, int((a.total_seconds or 6000) * 0.4))                                        # 評価関数 V の採否ゲートの日次枠（段階目標のあるコンボで等分。1件あたり最低600秒）。局数は日をまたいで積み上げる
    VGATE_SEC = max(600, VGATE_TOTAL // max(1, len(vg)))
    if a.total_seconds:                                       # 日次の総枠から、診断に使った残りを deck_fix と tune に自動で配る
        from dmsim.deckplan import budget as B
        a.deck_fix_budget, a.tune_seconds = B.split_remaining(a.total_seconds - (VGATE_SEC * len(vg)), time.time() - t0, bool(a.deck_fix and a.out), True)
        print(f"日次枠{a.total_seconds}秒: deck_fix {a.deck_fix_budget}秒 / tune {a.tune_seconds}秒")
    if a.deck_fix and a.out and (a.deck_fix_budget or not a.total_seconds):
        import deck_fix                                   # 同じ tools/ にある。cards 段階の記録があるコンボだけ回る
        timed("deck_fix", lambda: selfheal.run_phase("deck_fix", lambda: deck_fix.main(["--targets", a.targets, "--stage-from", a.out, "--seeds", str(a.seeds), "--turns", str(a.turns),
                           "--workers", str(a.workers), "--cands", "6", "--time-budget", str(a.deck_fix_budget)]), a.health), a.deck_fix_budget)
    if a.tune_seconds:
        import auto_tune                                  # 進化戦略のノブ探索。採用は再確認シードで再現した時だけ（docs/autotune.md）
        timed("auto_tune", lambda: selfheal.run_phase("auto_tune", lambda: auto_tune.main(["--targets", a.targets, "--seeds", str(a.seeds), "--turns", str(a.turns), "--workers", str(a.workers),
                           "--seconds", str(a.tune_seconds), "--store", a.store] + (["--out", a.out.replace(".jsonl", "") + "_tune.jsonl"] if a.out else [])), a.health), a.tune_seconds)
    if vg and a.total_seconds:
        import v_gate
        for cb in vg:
            timed(f"v_gate:{cb}", lambda cb=cb: selfheal.run_phase(f"v_gate:{cb}", lambda cb=cb: v_gate.main(["--combo", cb, "--targets", a.targets, "--seeds", str(max(6, VGATE_SEC // 100)), "--seconds", str(VGATE_SEC - 30),
                                                                         "--out", (a.out.replace(".jsonl", "") + "_vgate.jsonl") if a.out else "logs/v_gate.jsonl"]), a.health), VGATE_SEC)
    if a.total_seconds:
        import json
        import datetime
        total = round(time.time() - t0)
        line = {"date": datetime.date.today().isoformat(), "total_alloc": a.total_seconds, "total": total, "phases": timing, "win_stats": stats}
        print("所要時間:", " / ".join(f"{k} {v['sec']}s" + (f"(割当{v['alloc']}s)" if "alloc" in v else "") for k, v in timing.items()), f"/ 合計 {total}s（枠{a.total_seconds}s）")
        tp = Path("data/autofix/timing_history.jsonl")
        tp.parent.mkdir(parents=True, exist_ok=True)
        with open(tp, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    body = selfheal.render_issue(selfheal.load(a.health))     # 失敗した段階があれば、Issue 用の要約を残す（日次ルーティンが Issue 化して直す）
    if body:
        Path(a.issue_file).parent.mkdir(parents=True, exist_ok=True)
        Path(a.issue_file).write_text(body, encoding="utf-8")
        print(f"失敗した段階あり → {a.issue_file}（label autofix-failing の Issue にする）")
    elif Path(a.issue_file).exists():
        Path(a.issue_file).unlink()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", help="複数対象のYAML(data/autofix/targets.yaml)。指定時は --combo/--deck 等は無視")
    ap.add_argument("--combo")
    ap.add_argument("--deck")
    ap.add_argument("--setup")
    ap.add_argument("--opp-deck")
    ap.add_argument("--need", nargs="*", default=[])
    ap.add_argument("--board", nargs="*", default=[])
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--store", default="data/autofix/knobs.yaml", help="採用した設定の保存先（次回の開始点になる）")
    ap.add_argument("--workers", type=int, default=1, help="並列プロセス数（seeds を分けて回す。CPU数まで）")
    ap.add_argument("--deck-fix", action="store_true", help="終了後、cards 段階の記録があれば tools/deck_fix.py --stage-from を続けて回す（--out 必須）")
    ap.add_argument("--deck-fix-budget", type=int, default=5400, help="--deck-fix の時間予算（秒）。対象ごとの候補数と粗比較の局数を自動配分し、前回途中のデッキを優先する（既定 90分）")
    ap.add_argument("--cold", action="store_true", help="実行層（仕込み済み開始）でなく通常の開幕で測る（到達層の確認用）")
    ap.add_argument("--tune-seconds", type=int, default=0, help="0以外なら、終了後に tools/auto_tune.py をこの秒数の予算で続けて回す（--targets 指定時）。既定は無効")
    ap.add_argument("--total-seconds", type=int, default=0, help="0以外なら日次の総枠（秒）。診断ループの後、残り時間を deck_fix(65%%)と tune(35%%)へ自動配分する（--deck-fix-budget/--tune-seconds は上書きされる）")
    ap.add_argument("--health", default="data/autofix/health.yaml", help="段階ごとの成否の記録（自己修復。連続失敗は隔離される）")
    ap.add_argument("--issue-file", default="logs/autofix_issue.md", help="失敗した段階の要約（Issue 本文）の出力先。失敗が無ければ作らない")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    combos = {c["id"]: c for c in yaml.safe_load(Path("data/known_combos/combos.yaml").read_text(encoding="utf-8"))["combos"]}
    cards = {x.split(":")[0]: int(x.split(":")[1]) if ":" in x else 1 for x in a.need}
    board: dict = {}
    for x in a.board:
        z, d, *n = x.split(":")
        board.setdefault(z, {})[d] = int(n[0]) if n else 1
    if a.targets:
        return run_batch(a, combos)
    spec = yaml.safe_load(Path(a.setup).read_text(encoding="utf-8")) if a.setup else None
    rules_, deck_, opp_ = load_rules(), load_deck(a.deck), load_deck(a.opp_deck) if a.opp_deck else ["T001"] * 40
    meas = harness_measure(rules_, deck_, opp_,
                           list(range(1, a.seeds + 1)), spec, ProgressSpec(board=board, cards=cards) if (cards or board) else None,
                           load_specs()[a.combo], max_turn=a.turns, workers=a.workers, prep_ids=_prep_ids(combos[a.combo], rules_, deck_, opp_, load_specs()[a.combo]))
    k, hist = autofix(meas, Knobs(), combos[a.combo], Rule(turn=a.turns), a.rounds, a.out)
    for h in hist:
        print(h["round"], h["stage"], h["cause"], h["rates"], [(t["change"], t["verdict"]) for t in h.get("tries", [])])
    print("final", k)


if __name__ == "__main__":
    main()
