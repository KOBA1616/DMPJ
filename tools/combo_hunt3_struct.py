"""コンボ発見 v3・構造提案: 束の移動・誘発構造（構造署名）による候補生成と v3 判定。

属性近傍置換（tools/combo_hunt3_propose.py）は新規エンジン0件だった。所見は
「ループの相互作用は効果の正確な配線に依存し、粗い属性類似では保存されない」。
ここでは dmsim/discovery/structsig.py の構造署名で候補を作る:

  S_control:     対照 {サガ×2, XENARCH×2}（手札型が再現されることの確認）
  S_xenarch_sub: XENARCH の傍受配線（墓地で hand→graveyard を受け、自分を墓地→手札
                 に戻す。層: 厳密／戻し先が場／移動元不問）を共有するカードで
                 XENARCH を置換し、{サガ×2, 候補×2} を判定する
  S_saga_sub:    サガの自己回帰配線（draw＋discard＋自己適合の蘇生。層は structsig
                 参照）を共有するカード単独×2 を判定する

判定は judge_engine3（予算1000・シード1）。合格で新規性（最小コアと増分の組が
既知エンジンと不一致）があれば judge_conversion3 で変換まで見る。
各候補の判定はサブプロセスで隔離し、タイムアウトを未決着として明示する。

--retry-unresolved: 属性提案 D（アカシック置換）で 420 秒タイムアウトした4件を、
条件を変えて再判定する。手順: (1) judge_engine_once（予算1000・シード1、
タイムアウト700秒）。タイムアウトなら (2) 予算500・シード2 で再試行。
素の判定が合格なら (3) judge_engine3（最小化、タイムアウト1800秒）まで行う。

使い方:
  PYTHONPATH=. python tools/combo_hunt3_struct.py --list-only
  PYTHONPATH=. python tools/combo_hunt3_struct.py --out ~/workspace/combo3/proposals_struct.jsonl
  PYTHONPATH=. python tools/combo_hunt3_struct.py --retry-unresolved \
      --out ~/workspace/combo3/proposals_struct_retry.jsonl
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.discovery import hunt3, structsig  # noqa: E402
from tools.combo_hunt3_run import KNOWN_CORE  # noqa: E402

SAGA = "dm22ex2-021"
XENARCH = "dm22rp2x-004"
AKASHIC_CORE = {"dm23ex2-009": 1, "dm23bd7-035": 2, "dm24ex1-038": 1, "dmrp12-s01": 1}

KNOWN_ENGINES = [
    ({SAGA: 2}, {"deck:0": -1, "graveyard:0": 1}),
    ({SAGA: 2, XENARCH: 2}, {"deck:0": -1, "hand:0": 1}),
    (dict(AKASHIC_CORE), {"deck:1": -1, "graveyard:1": 1}),
]

# 属性提案 D で 420 秒タイムアウトした4件（docs/combo-hunt-v3.md「モデル提案」節）
UNRESOLVED = [
    {"cards": {"dm23ex2-009": 1, "dm23bd7-035": 2, "dmrp12-s01": 1, "dm26ex3-047": 1},
     "replaced": "dm24ex1-038", "with": "dm26ex3-047"},   # ウォカンナ枠: ルード・ザーナ
    {"cards": {"dm23ex2-009": 1, "dm23bd7-035": 2, "dmrp12-s01": 1, "dm26ex3-081": 1},
     "replaced": "dm24ex1-038", "with": "dm26ex3-081"},   # ウォカンナ枠: 流星アーシュ
    {"cards": {"dm23ex2-009": 1, "dm23bd7-035": 2, "dmrp12-s01": 1, "dmrp13-016": 1},
     "replaced": "dm24ex1-038", "with": "dmrp13-016"},    # ウォカンナ枠: エビデンスバード
    {"cards": {"dm23ex2-009": 1, "dm23bd7-035": 2, "dm24ex1-038": 1, "dmrp08-s01": 1},
     "replaced": "dmrp12-s01", "with": "dmrp08-s01"},    # ホーリーエンド枠: ゼブルエ
]


def _is_known_engine(core: dict, delta: dict | None) -> bool:
    return any(core == kc and delta == kd for kc, kd in KNOWN_ENGINES)


def _engine_summary(v: dict, rules) -> dict:
    core = v.get("core")
    return {"pass": v["pass"], "kinds": v["kinds"], "delta": v["delta"],
            "grown": v["grown"], "within_turn": v["within_turn"],
            "own_turns": v["own_turns"], "core": core,
            "core_names": ({cid: rules.cards[cid].name for cid in core} if core else None),
            "necessity": {k: x["necessary"] for k, x in (v.get("necessity") or {}).items()}}


# ---------------------------------------------------------------- 候補生成

def build_candidates(rules, by_card) -> tuple[list[dict], dict]:
    """構造署名から候補を作る。戻り値: (候補, 走査結果の要約)。"""
    exclude_ids = set(KNOWN_CORE) | {XENARCH}
    xen_name = rules.cards[XENARCH].name
    saga_name = rules.cards[SAGA].name
    scan = {"interceptors": {}, "saga_like": {}, "skipped": []}

    inter = structsig.find_interceptors(by_card)
    for cid, hits in sorted(inter.items()):
        scan["interceptors"][cid] = {"name": rules.cards[cid].name,
                                     "kinds": [h["kind"] for h in hits],
                                     "signatures": [h["signature"] for h in hits]}
    sl = structsig.find_saga_like(by_card, rules)
    for cid, hits in sorted(sl.items()):
        scan["saga_like"][cid] = {"name": rules.cards[cid].name,
                                  "tiers": [h["tier"] for h in hits],
                                  "signatures": [h["signature"] for h in hits]}

    cands = [{"cards": {SAGA: 2, XENARCH: 2}, "pattern": "S_control",
              "seed_card": XENARCH, "replaced": None, "with": XENARCH, "tier": "control"}]
    for cid, info in scan["interceptors"].items():
        if cid == XENARCH:
            continue
        if cid in exclude_ids or info["name"] == xen_name:
            scan["skipped"].append({"card": cid, "reason": "既知コアまたは同名"})
            continue
        cands.append({"cards": {SAGA: 2, cid: 2}, "pattern": "S_xenarch_sub",
                      "seed_card": XENARCH, "replaced": XENARCH, "with": cid,
                      "tier": info["kinds"], "signature": info["signatures"]})
    for cid, info in scan["saga_like"].items():
        if cid == SAGA:
            continue
        if cid in exclude_ids or info["name"] == saga_name:
            scan["skipped"].append({"card": cid, "reason": "既知コアまたは同名"})
            continue
        cands.append({"cards": {cid: 2}, "pattern": "S_saga_sub",
                      "seed_card": SAGA, "replaced": SAGA, "with": cid,
                      "tier": info["tiers"], "signature": info["signatures"]})
    return cands, scan


# ---------------------------------------------------------------- サブプロセス側

def _one_engine(job: dict) -> dict:
    rules = load_rules()
    by_card = hunt3.bundles_by_card(rules)
    if job.get("mode") == "once":
        v = hunt3.judge_engine_once(rules, job["cards"], by_card,
                                    budget=job["budget"], seeds=(job["seed"],))
    else:
        v = hunt3.judge_engine3(rules, job["cards"], by_card,
                                budget=job["budget"], seeds=(job["seed"],))
    return {"engine": _engine_summary(v, rules), "engine_rows": v["rows"]}


def _one_conv(job: dict) -> dict:
    rules = load_rules()
    by_card = hunt3.bundles_by_card(rules)
    cv = hunt3.judge_conversion3(rules, job["core"], [job["conv_card"]], by_card,
                                 engine_budget=job["budget"], conv_budget=job["budget"],
                                 seeds=(job["seed"],), delta=job["delta"])
    return {"pass": cv["pass"], "rows": cv["rows"]}


def _run_sub(job: dict, timeout: int) -> dict:
    """このスクリプトを --one モードで子プロセス実行し、結果 dict を返す。
    タイムアウトは {"error": "timeout after Ns"} として返す（未決着の明示）。"""
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                            "--one", json.dumps(job)],
                           capture_output=True, text=True, timeout=timeout,
                           cwd=str(Path(__file__).resolve().parent.parent))
    except subprocess.TimeoutExpired:
        return {"error": f"timeout after {timeout}s", "seconds": round(time.time() - t0, 1)}
    if p.returncode != 0:
        return {"error": f"exit {p.returncode}: {p.stderr.strip()[-500:]}",
                "seconds": round(time.time() - t0, 1)}
    out = {"seconds": round(time.time() - t0, 1)}
    out.update(json.loads(p.stdout.strip().splitlines()[-1]))
    return out


# ---------------------------------------------------------------- 運転側

def judge_struct_candidate(rules, cand: dict, budget: int, timeout: int,
                           conv_limit: int, conv_timeout: int) -> dict:
    rec = dict(cand)
    rec["names"] = {cid: rules.cards[cid].name for cid in cand["cards"]}
    job = {"mode": "engine3", "cards": cand["cards"], "budget": budget, "seed": 1}
    r = _run_sub(job, timeout)
    rec["seconds"] = r.pop("seconds", None)
    if "error" in r:
        rec["error"] = r["error"]
        return rec
    rec["engine"] = r["engine"]
    rec["engine_rows"] = r["engine_rows"]
    eng = r["engine"]
    if eng.get("pass"):
        core = eng.get("core") or cand["cards"]
        if _is_known_engine(core, eng["delta"]):
            rec["conversion"] = "skipped_known_engine"
        else:
            by_card = hunt3.bundles_by_card(rules)
            catalog3 = hunt3.conversion_catalog3(rules, by_card)
            convs = []
            for pc in hunt3.pair_conversions3(eng["delta"], eng["kinds"], catalog3,
                                              limit=conv_limit):
                cj = {"core": core, "conv_card": pc["card"], "delta": eng["delta"],
                      "budget": budget, "seed": 1}
                cr = _run_sub_conv(cj, conv_timeout)
                convs.append({"card": pc["card"], "name": pc["name"], "zones": pc["zones"],
                              **cr})
            rec["conversion"] = convs
    return rec


def _run_sub_conv(job: dict, timeout: int) -> dict:
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                            "--one-conv", json.dumps(job)],
                           capture_output=True, text=True, timeout=timeout,
                           cwd=str(Path(__file__).resolve().parent.parent))
    except subprocess.TimeoutExpired:
        return {"error": f"timeout after {timeout}s", "seconds": round(time.time() - t0, 1)}
    if p.returncode != 0:
        return {"error": f"exit {p.returncode}: {p.stderr.strip()[-500:]}",
                "seconds": round(time.time() - t0, 1)}
    out = {"seconds": round(time.time() - t0, 1)}
    out.update(json.loads(p.stdout.strip().splitlines()[-1]))
    return out


def judge_unresolved(rules, cand: dict, once_timeout: int, min_timeout: int) -> dict:
    """未決着4件の段階的再判定。条件と段階ごとの結果を全て記録する。"""
    rec = {"pattern": "S_retry_unresolved", "cards": cand["cards"],
           "replaced": cand["replaced"], "with": cand["with"],
           "names": {cid: rules.cards[cid].name for cid in cand["cards"]},
           "stages": []}
    # 段階1: 素の判定（予算1000・シード1）
    r1 = _run_sub({"mode": "once", "cards": cand["cards"], "budget": 1000, "seed": 1},
                  once_timeout)
    rec["stages"].append({"stage": "once", "budget": 1000, "seed": 1, **r1})
    if "error" in r1 and "timeout" in r1["error"]:
        # 段階2: 予算500・シード2
        r2 = _run_sub({"mode": "once", "cards": cand["cards"], "budget": 500, "seed": 2},
                      once_timeout)
        rec["stages"].append({"stage": "once", "budget": 500, "seed": 2, **r2})
        if "error" in r2:
            rec["verdict"] = "unresolved"
            rec["reason"] = ("探索爆発が予算1000・シード1 と予算500・シード2 の"
                             "両方でタイムアウト内に収まらなかった")
            return rec
        r1 = r2
    elif "error" in r1:
        rec["verdict"] = "error"
        rec["reason"] = r1["error"]
        return rec
    eng = r1["engine"]
    rec["engine_once"] = eng
    if not eng.get("pass"):
        rec["verdict"] = "fail"
        return rec
    # 段階3: 最小化まで（judge_engine3）
    r3 = _run_sub({"mode": "engine3", "cards": cand["cards"], "budget": 1000, "seed": 1},
                  min_timeout)
    rec["stages"].append({"stage": "engine3", "budget": 1000, "seed": 1, **r3})
    if "error" in r3:
        rec["verdict"] = "pass_minimization_unresolved"
        rec["reason"] = f"素の判定は合格したが最小化が完了しなかった: {r3['error']}"
        return rec
    rec["engine"] = r3["engine"]
    rec["engine_rows"] = r3["engine_rows"]
    rec["verdict"] = "pass"
    return rec


def _load_done(path: str | None) -> set:
    done = set()
    if path and Path(path).exists():
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                done.add(json.dumps(d["cards"], sort_keys=True))
    return done


def _append(path: str | None, rec: dict):
    if path:
        with Path(path).open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="結果 JSONL（追記・再開可能）")
    ap.add_argument("--signatures-out", default=None, help="走査結果（署名）JSON の出力先")
    ap.add_argument("--list-only", action="store_true")
    ap.add_argument("--retry-unresolved", action="store_true")
    ap.add_argument("--budget", type=int, default=1000)
    ap.add_argument("--timeout", type=int, default=1200, help="エンジン判定1件の上限秒")
    ap.add_argument("--conv-timeout", type=int, default=1200)
    ap.add_argument("--conv-limit", type=int, default=4)
    ap.add_argument("--once-timeout", type=int, default=700)
    ap.add_argument("--min-timeout", type=int, default=1800)
    ap.add_argument("--one", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--one-conv", default=None, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)

    if a.one:
        job = json.loads(a.one)
        print(json.dumps(_one_engine(job), ensure_ascii=False))
        return 0
    if a.one_conv:
        job = json.loads(a.one_conv)
        print(json.dumps(_one_conv(job), ensure_ascii=False))
        return 0

    rules = load_rules()
    by_card = hunt3.bundles_by_card(rules)

    if a.retry_unresolved:
        done = _load_done(a.out)
        for cand in UNRESOLVED:
            key = json.dumps(cand["cards"], sort_keys=True)
            if key in done:
                print(f"済: {cand['with']}", flush=True)
                continue
            rec = judge_unresolved(rules, cand, a.once_timeout, a.min_timeout)
            print(f"{rules.cards[cand['with']].name}: verdict={rec['verdict']}"
                  + (f" core={(rec.get('engine') or {}).get('core')}" if rec["verdict"] == "pass" else "")
                  + (f" reason={rec.get('reason')}" if rec.get("reason") else ""), flush=True)
            _append(a.out, rec)
        return 0

    cands, scan = build_candidates(rules, by_card)
    if a.signatures_out:
        dump = {"xenarch_signature": scan["interceptors"].get(XENARCH),
                "saga_signature": scan["saga_like"].get(SAGA),
                "interceptors": scan["interceptors"], "saga_like": scan["saga_like"],
                "skipped": scan["skipped"]}
        Path(a.signatures_out).write_text(json.dumps(dump, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    from collections import Counter
    print("候補内訳:", dict(Counter(c["pattern"] for c in cands)), "合計", len(cands), flush=True)
    print("傍受配線の全件:", {cid: (v["name"], v["kinds"]) for cid, v in scan["interceptors"].items()},
          flush=True)
    print("自己回帰配線の全件:", {cid: (v["name"], v["tiers"]) for cid, v in scan["saga_like"].items()},
          flush=True)
    if a.list_only:
        for c in cands:
            print(json.dumps(c, ensure_ascii=False), flush=True)
        return 0

    done = _load_done(a.out)
    n_pass = 0
    for i, cand in enumerate(cands):
        key = json.dumps(cand["cards"], sort_keys=True)
        if key in done:
            continue
        rec = judge_struct_candidate(rules, cand, a.budget, a.timeout,
                                     a.conv_limit, a.conv_timeout)
        eng = rec.get("engine") or {}
        if eng.get("pass"):
            n_pass += 1
        print(f"[{i+1}/{len(cands)}] {cand['pattern']} {' + '.join(rec['names'].values())}: "
              f"{'合格' if eng.get('pass') else '不合格'}"
              + (f" core={eng.get('core')} delta={eng.get('delta')}" if eng.get("pass") else "")
              + (f" ERROR={rec['error']}" if rec.get("error") else "")
              + f" ({rec.get('seconds')}s)", flush=True)
        _append(a.out, rec)
    print(f"完了: エンジン合格 {n_pass} 件", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
