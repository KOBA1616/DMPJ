"""コンボ発見 v3 の実行ツール（dmsim/discovery/hunt3.py）。

使い方:
  PYTHONPATH=. python tools/combo_hunt3.py --controls --out3 /tmp/controls3.json
      陽性対照: akashic / saga を v3 エンジン判定（最小性つき）＋ saga は v3 変換判定、
      tenmon は記録手順の再生（v2 と同じ方法）で通す。
  PYTHONPATH=. python tools/combo_hunt3.py --rejudge <results2.jsonl> --out3 out.jsonl
      v2 のエンジン合格組を v3 エンジン判定で再判定し、最小コアを出す。
  PYTHONPATH=. python tools/combo_hunt3.py --xenarch --out3 out.json
      サガ+XENARCH の v3 変換判定（手札型に連動した候補で、実局面から勝ちを探す）。
"""
import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.discovery import hunt3  # noqa: E402

W: dict = {}


def _ensure():
    if "rules" not in W:
        W["rules"] = load_rules()
        W["by_card"] = hunt3.bundles_by_card(W["rules"])
        W["catalog3"] = hunt3.conversion_catalog3(W["rules"], W["by_card"])
    return W["rules"], W["by_card"], W["catalog3"]


def _tenmon_control() -> dict:
    """tenmon は記録手順型なので v2 と同じ再生で確認する（combo_hunt2 の実装を読み込んで使う）。"""
    spec = importlib.util.spec_from_file_location(
        "combo_hunt2", Path(__file__).resolve().parent / "combo_hunt2.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run_tenmon_control()


def _engine_summary(v: dict) -> dict:
    return {"pass": v["pass"], "kinds": v["kinds"], "delta": v["delta"], "grown": v["grown"],
            "within_turn": v["within_turn"], "own_turns": v["own_turns"],
            "core": v.get("core"),
            "necessity": {k: x["necessary"] for k, x in (v.get("necessity") or {}).items()},
            "ablations": v.get("ablations")}


def run_controls(budget: int) -> dict:
    from dmsim.eval import loop_entry as le
    rules, by_card, catalog3 = _ensure()
    out: dict = {}
    for name in ("akashic", "saga"):
        ls = le.load(name)
        full = le.core_alternatives(ls)[0]
        t0 = time.time()
        eng = hunt3.judge_engine3(rules, full, by_card, budget=budget, seeds=(1, 2))
        row: dict = {"cards": full, "engine_full": _engine_summary(eng), "engine_full_rows": eng["rows"]}
        row["pass"] = bool(eng["pass"])
        if name == "saga":
            loop_only = le.core_alternatives(ls, "loop")[0]
            e2 = hunt3.judge_engine3(rules, loop_only, by_card, budget=budget, seeds=(1, 2))
            row["engine_loop_only"] = _engine_summary(e2)
            row["engine_loop_rows"] = e2["rows"]
            core = e2.get("core") or loop_only
            cands = hunt3.pair_conversions3(e2["delta"], e2["kinds"], catalog3, limit=4)
            convs = []
            for pc in cands:
                cv = hunt3.judge_conversion3(rules, core, [pc["card"]], by_card,
                                             engine_budget=budget, conv_budget=budget, seeds=(1,),
                                             delta=e2["delta"])
                convs.append({"card": pc["card"], "name": pc["name"], "zones": pc["zones"],
                              "engine_type": pc["engine_type"], "pass": cv["pass"], "rows": cv["rows"]})
                print(f"  変換候補 {pc['name']}: {'合格' if cv['pass'] else '不合格'}", flush=True)
            row["conversion"] = convs
            row["pass"] = bool(eng["pass"] and e2["pass"] and any(c["pass"] for c in convs))
        row["seconds"] = round(time.time() - t0, 1)
        out[name] = row
        print(f"対照 {name}: エンジン(full)={eng['pass']} core={eng.get('core')} delta={eng['delta']}"
              + (f" / loop部品のみ={row.get('engine_loop_only', {}).get('pass')}"
                 f" core={row.get('engine_loop_only', {}).get('core')}"
                 f" / 変換={any(c['pass'] for c in row.get('conversion', []))}" if name == "saga" else "")
              + f" ({row['seconds']}s)", flush=True)
    out["tenmon"] = _tenmon_control()
    return out


def run_rejudge(path: str, budget: int, limit: int | None) -> list[dict]:
    rules, by_card, _ = _ensure()
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    passed = [r for r in rows if r.get("engine", {}).get("pass")]
    if limit:
        passed = passed[:limit]
    out = []
    for r in passed:
        t0 = time.time()
        v = hunt3.judge_engine3(rules, r["counts"], by_card, budget=budget, seeds=(1,))
        rec = {"cards": r["cards"], "names": r["names"], "counts": r["counts"],
               "v2_delta": r["engine"]["delta"],
               "v3": _engine_summary(v), "rows": v["rows"],
               "seconds": round(time.time() - t0, 1)}
        out.append(rec)
        print(f"[{'合格' if v['pass'] else '不合格'}] {' + '.join(r['names'])}: "
              f"最小コア={v.get('core')} delta={v['delta']} ({rec['seconds']}s)", flush=True)
    return out


def run_xenarch(budget: int, conv_per: int) -> dict:
    rules, by_card, catalog3 = _ensure()
    cards = {"dm22ex2-021": 2, "dm22rp2x-004": 2}
    t0 = time.time()
    eng = hunt3.judge_engine3(rules, cards, by_card, budget=budget, seeds=(1,))
    core = eng.get("core") or cards
    print(f"エンジン: pass={eng['pass']} core={core} delta={eng['delta']} kinds={eng['kinds']}",
          flush=True)
    cands = hunt3.pair_conversions3(eng["delta"], eng["kinds"], catalog3, limit=conv_per)
    print(f"変換候補（型={hunt3.engine_type(eng['delta'], eng['kinds'])}）: "
          + ", ".join(f"{c['name']}(zones={c['zones']})" for c in cands), flush=True)
    convs = []
    for pc in cands:
        cv = hunt3.judge_conversion3(rules, core, [pc["card"]], by_card,
                                     engine_budget=budget, conv_budget=budget, seeds=(1,),
                                     delta=eng["delta"])
        convs.append({"card": pc["card"], "name": pc["name"], "zones": pc["zones"],
                      "pass": cv["pass"], "rows": cv["rows"]})
        r0 = cv["rows"][0]
        acc = r0.get("accum") or {}
        print(f"  {pc['name']}: {'合格（勝ち筋あり）' if cv['pass'] else '不合格'}"
              f"（蓄積: 推定{acc.get('laps_est')}周・{acc.get('turns')}ターン・停止={acc.get('stop_reason')}"
              f"・変換段到達={not r0.get('decided_in_engine_phase')}・kill_turn={r0.get('kill_turn')}）", flush=True)
    return {"cards": cards, "names": ["絶望神サガ", "死神覇王 XENARCH"],
            "engine": _engine_summary(eng), "engine_rows": eng["rows"],
            "conversion": convs, "seconds": round(time.time() - t0, 1)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--rejudge", default=None, help="v2 の results2.jsonl のパス")
    ap.add_argument("--xenarch", action="store_true")
    ap.add_argument("--budget", type=int, default=1000)
    ap.add_argument("--conv-per", type=int, default=6)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out3", default=None)
    a = ap.parse_args(argv)
    t0 = time.time()
    if a.controls:
        res = run_controls(a.budget)
        if a.out3:
            Path(a.out3).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        ok = all(v.get("pass") for v in res.values())
        print(f"対照の総合: {'合格' if ok else '不合格あり'}（{time.time()-t0:.0f}s）")
        return 0 if ok else 1
    if a.rejudge:
        res = run_rejudge(a.rejudge, a.budget, a.limit)
        if a.out3:
            with Path(a.out3).open("w", encoding="utf-8") as f:
                for r in res:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"再判定 {len(res)} 件（{time.time()-t0:.0f}s）")
        return 0
    if a.xenarch:
        res = run_xenarch(a.budget, a.conv_per)
        if a.out3:
            Path(a.out3).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"XENARCH 変換: {'勝ち筋あり' if any(c['pass'] for c in res['conversion']) else '見つからず'}"
              f"（{time.time()-t0:.0f}s）")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
