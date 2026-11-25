"""コンボ発見 v3 の発見ラン（dmsim/discovery/hunt3.py の判定器で候補プールを検証する）。

v2（tools/combo_hunt2.py）との違い:
- 候補の母集団・層化は v2 と同じ枠組み（hunt2.enumerate_candidates → hunt2.stratified_sample、
  シード 42）。ただし既知エンジンの最小コアのカードを含む候補は、抽出の前に除外する
  （KNOWN_CORE と除外の定義は下記）。
- 判定は v3: エンジン判定は judge_engine3（最小性＋増分同一性）、合格した組は
  最小コアに対して pair_conversions3（増分の型に連動）→ judge_conversion3（実蓄積＋停止条件）。
  v2 の開幕検証（段2）は v3 の設計に無いため実施しない。

除外の定義: 候補のカード種類の集合が KNOWN_CORE と1種でも交わる候補を除外する
（枚数は問わない）。KNOWN_CORE は既知エンジンの最小コアのカード:
- サガループ: dm22ex2-021（絶望神サガ。最小コア {サガ×2}）
- アカシック: docs/combo-hunt-v3.md の陽性対照で確定した最小コア4種
  （dm23ex2-009 完全水中要塞 アカシック3 / dm23bd7-035 魔刻の斬将オルゼキア／訪れる魔の時刻 /
   dm24ex1-038 冥土人形ウォカンナ・ピエール / dmrp12-s01 天命龍装 ホーリーエンド／ナウ・オア・ネバー）
- 天門ループ: data/loops/tenmon_initial.json の source.board（p0）に現れる実カード全種
  （プロトの埋め札 T013 を除く。光霊姫アレフティナ dmx12b-031、ヘブンズ・ゲート dm16-007 を含む）
なおサガ+XENARCH の既知エンジン（最小コア {サガ×2, XENARCH×2}）はサガの除外で自動的に外れる。
除外は候補（発見対象）にのみ適用し、変換候補カタログには適用しない。

使い方:
  PYTHONPATH=. python tools/combo_hunt3_run.py --smoke --out3 smoke3.json
      陽性対照スモーク: 最小コア {サガ×2} が v3 エンジン判定で検出されることの確認。
  PYTHONPATH=. python tools/combo_hunt3_run.py --sample 300 --singles --workers 4 \
      --out results3.jsonl --candidates-out candidates3.json
      発見ラン。結果は --out に1候補1行で追記し、記録済みの候補は飛ばす（再開可能）。
"""
import argparse
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.discovery import hunt2, hunt3  # noqa: E402

KNOWN_CORE = {
    "dm22ex2-021",                                    # 絶望神サガ（サガループの最小コア）
    "dm23ex2-009", "dm23bd7-035", "dm24ex1-038", "dmrp12-s01",   # アカシック最小コア4種
    # 天門ループ spec（data/loops/tenmon_initial.json）の board に現れる実カード
    "dm01-080", "dm02-024", "dm06-085", "dm16-007", "dm23bd7-022", "dm23ex2-cho018",
    "dm31-025", "dmd24-024", "dmx11-082", "dmx12b-031", "dmx19-s06", "dmx24-017",
}

W: dict = {}


def _init_worker():
    W["rules"] = load_rules()
    W["by_card"] = hunt3.bundles_by_card(W["rules"])
    W["catalog3"] = hunt3.conversion_catalog3(W["rules"], W["by_card"])


def _ensure():
    if "rules" not in W:
        _init_worker()
    return W["rules"], W["by_card"], W["catalog3"]


def is_excluded(cand: dict) -> bool:
    return bool(set(cand["cards"]) & KNOWN_CORE)


def _engine_summary(v: dict, rules) -> dict:
    core = v.get("core")
    return {"pass": v["pass"], "kinds": v["kinds"], "delta": v["delta"], "win_by": v["win_by"],
            "grown": v["grown"], "evidence": v["evidence"], "within_turn": v["within_turn"],
            "own_turns": v["own_turns"], "core": core,
            "core_names": ({cid: rules.cards[cid].name for cid in core} if core else None),
            "necessity": {k: x["necessary"] for k, x in (v.get("necessity") or {}).items()},
            "ablations": v.get("ablations")}


def run_candidate(cand: dict, cfg: dict) -> dict:
    """1候補: v3 エンジン判定 →（合格時）最小コアへの型連動の変換判定。例外は記録して止めない。"""
    rules, by_card, catalog3 = _ensure()
    t0 = time.time()
    rec: dict = {k: cand[k] for k in ("cards", "counts", "names", "score", "static", "stratum")}
    try:
        eng = hunt3.judge_engine3(rules, cand["counts"], by_card, budget=cfg["budget"],
                                  seeds=tuple(cfg["seeds"]))
        rec["engine"] = _engine_summary(eng, rules)
        rec["engine_rows"] = eng["rows"]
        if eng["pass"]:
            core = eng.get("core") or cand["counts"]
            pairs = hunt3.pair_conversions3(eng["delta"], eng["kinds"], catalog3,
                                            limit=cfg["conv_per"])
            conv_results = []
            for pc in pairs:
                cv = hunt3.judge_conversion3(rules, core, [pc["card"]], by_card,
                                             engine_budget=cfg["conv_budget"],
                                             conv_budget=cfg["conv_budget"],
                                             seeds=tuple(cfg["seeds"]), delta=eng["delta"])
                conv_results.append({"card": pc["card"], "name": pc["name"], "zones": pc["zones"],
                                     "engine_type": pc["engine_type"], "pass": cv["pass"],
                                     "rows": cv["rows"]})
            rec["conversion"] = conv_results
    except Exception as ex:      # 1候補の失敗で全体を止めない
        rec["error"] = f"{type(ex).__name__}: {ex}"
    rec["seconds"] = round(time.time() - t0, 1)
    return rec


def run_smoke(budget: int) -> dict:
    """陽性対照スモーク: 既知の最小コア {サガ×2} が v3 でも検出されること（コアと増分まで一致）。"""
    rules, by_card, _ = _ensure()
    t0 = time.time()
    v = hunt3.judge_engine3(rules, {"dm22ex2-021": 2}, by_card, budget=budget, seeds=(1,))
    expect_delta = {"deck:0": -1, "graveyard:0": 1}
    ok = bool(v["pass"] and v.get("core") == {"dm22ex2-021": 2} and v["delta"] == expect_delta)
    row = {"cards": {"dm22ex2-021": 2}, "engine": _engine_summary(v, rules), "rows": v["rows"],
           "expect_delta": expect_delta, "pass": ok, "seconds": round(time.time() - t0, 1)}
    print(f"スモーク saga最小コア: pass={v['pass']} core={v.get('core')} delta={v['delta']}"
          f" -> {'合格' if ok else '不合格'} ({row['seconds']}s)", flush=True)
    return row


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="陽性対照スモーク（{サガ×2} の v3 検出）")
    ap.add_argument("--sample", type=int, default=0, help="層化抽出して検証する候補数（0 = 列挙だけ）")
    ap.add_argument("--pair-limit", type=int, default=None, help="静的ふるいで調べる速い組の上限")
    ap.add_argument("--singles", action="store_true", help="単独で循環する札も候補に入れる")
    ap.add_argument("--budget", type=int, default=1000, help="エンジン判定の探索予算")
    ap.add_argument("--conv-budget", type=int, default=1000)
    ap.add_argument("--conv-per", type=int, default=2, help="エンジン1件あたりの変換候補の試行数")
    ap.add_argument("--seeds", type=int, default=1, help="判定ごとのシード数（1, 2, ... と連番で使う）")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--time-cap", type=int, default=None, help="全体の打ち切り秒（途中結果は残る）")
    ap.add_argument("--out", default="results3.jsonl")
    ap.add_argument("--candidates-out", default=None, help="母集団・除外・抽出の記録を JSON で残す")
    ap.add_argument("--out3", default=None, help="スモーク結果の保存先")
    a = ap.parse_args(argv)
    t0 = time.time()
    if a.smoke:
        res = run_smoke(a.budget)
        if a.out3:
            Path(a.out3).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        return 0 if res["pass"] else 1

    rules, by_card, _ = _ensure()
    print(f"load {time.time()-t0:.0f}s", flush=True)
    pool = hunt2.enumerate_candidates(rules, by_card, pair_limit=a.pair_limit, singles=a.singles)
    items = pool["full"] + pool["engine"]
    excluded = [c for c in items if is_excluded(c)]
    filtered = [c for c in items if not is_excluded(c)]
    print(f"静的ふるい: full {len(pool['full'])} / engine {len(pool['engine'])} / 落ち {pool['drop']}"
          f" / 既知コア除外 {len(excluded)} / 残り {len(filtered)}（{time.time()-t0:.0f}s）", flush=True)
    rng = random.Random(42)
    picked = hunt2.stratified_sample(filtered, a.sample, rng) if a.sample > 0 else []
    if a.candidates_out:
        meta = {"known_core": sorted(KNOWN_CORE),
                "known_core_names": {cid: rules.cards[cid].name for cid in sorted(KNOWN_CORE)
                                     if cid in rules.cards},
                "exclusion": "候補のカード種類の集合が KNOWN_CORE と1種でも交わる候補を除外（枚数は問わない）",
                "pool": {"full": len(pool["full"]), "engine": len(pool["engine"]),
                         "drop": pool["drop"], "total": len(items),
                         "excluded": len(excluded), "filtered": len(filtered)},
                "strata_before": dict(Counter(c["stratum"] for c in items)),
                "strata_after": dict(Counter(c["stratum"] for c in filtered)),
                "strata_sampled": dict(Counter(c["stratum"] for c in picked)),
                "excluded_candidates": [{k: c[k] for k in ("cards", "counts", "names", "stratum")}
                                        for c in excluded],
                "sampled": [{k: c[k] for k in ("cards", "counts", "names", "score", "static", "stratum")}
                            for c in picked]}
        Path(a.candidates_out).write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.sample <= 0:
        return 0
    out = Path(a.out)
    done = set()
    if out.exists():
        done = {tuple(json.loads(l)["cards"]) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()}
    todo = [c for c in picked if tuple(c["cards"]) not in done]
    print(f"検証対象 {len(todo)} 件（抽出 {len(picked)}、済み {len(picked)-len(todo)}）", flush=True)
    cfg = {"budget": a.budget, "conv_budget": a.conv_budget, "conv_per": a.conv_per,
           "seeds": list(range(1, a.seeds + 1))}
    out.parent.mkdir(parents=True, exist_ok=True)
    n_pass = n_conv = 0

    def emit(rec: dict):
        nonlocal n_pass, n_conv
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        ep = bool(rec.get("engine", {}).get("pass"))
        cp = any(c.get("pass") for c in rec.get("conversion", []))
        n_pass, n_conv = n_pass + ep, n_conv + cp
        core = rec.get("engine", {}).get("core")
        print(f"[{'E' if ep else '-'}{'C' if cp else '-'}] {' + '.join(rec['names'])}"
              f" core={core} delta={rec.get('engine', {}).get('delta')}"
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
    print(f"完了: エンジン合格 {n_pass} / 変換合格 {n_conv}（全体 {time.time()-t0:.0f}s）", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
