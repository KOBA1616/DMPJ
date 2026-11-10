"""評価関数 V の採否ゲートを回す。 python tools/v_gate.py --combo tenmon --seeds 8 [--seconds 900]
段階目標の鎖への到達数を base と v_priority の重み候補で比べ、base を上回った重みだけを data/autofix/vweights.yaml に残す。
結果は --out（既定 logs/v_gate.jsonl）に追記。足切りには使わない。docs/value-function-design.md §7。"""
import argparse
import json
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.defs import load_rules  # noqa: E402
from dmsim.eval import vgate  # noqa: E402
from dmsim.solitaire import load_deck  # noqa: E402


def _grid(text):
    return tuple(tuple(float(x) for x in g.split(":")) for g in text.split(","))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--combo", default="tenmon")
    ap.add_argument("--targets", default="data/autofix/targets.yaml")
    ap.add_argument("--stages", help="段階目標のYAML（既定 data/eval/stages/<combo>.yaml）")
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--grid", default="", help="重みの候補 例 3:1,6:1,0:0:1（under:res[:plan]）。空なら既定")
    ap.add_argument("--width", type=int, default=40)
    ap.add_argument("--seconds", type=int, default=0, help="時間の上限（0=無制限）。超えたら残りの seed を測らない")
    ap.add_argument("--store", default="data/autofix/vweights.yaml")
    ap.add_argument("--out", default="logs/v_gate.jsonl")
    ap.add_argument("--acc", default="data/autofix/vgate_acc.yaml", help="日をまたいで積み上げる seed 別の結果。合計 MIN_ADOPT_N 局以上で判定する")
    ap.add_argument("--min-n", type=int, default=vgate.MIN_ADOPT_N)
    a = ap.parse_args(argv)
    t = next(x for x in yaml.safe_load(Path(a.targets).read_text(encoding="utf-8"))["targets"] if x["combo"] == a.combo)
    st = vgate.load_stages(a.stages or vgate.stage_path(a.combo))
    stages = [s["target"] for s in st["stages"][1:]]
    keys = list(st["stages"][0]["target"]["hand"])             # 先頭の段（keys_in_hand）を強制開始にする
    rules = load_rules()
    deck = load_deck(t["deck"])
    t0 = time.time()
    accp = Path(a.acc)
    accs = (yaml.safe_load(accp.read_text(encoding="utf-8")) or {}) if accp.exists() else {}
    acc = accs.get(a.combo) or {}
    s0 = vgate.next_seed(acc)                                  # 前回までに測った次の seed から（同じ seed を測り直さない）
    r = vgate.run_gate(rules, deck, ["T001"] * 40, keys, stages, range(s0, s0 + a.seeds), width=a.width, min_n=a.min_n,
                       grid=_grid(a.grid) if a.grid else vgate.GRID,
                       deadline=(t0 + a.seconds) if a.seconds else None)
    r.update(combo=a.combo, sec=round(time.time() - t0), seeds_from=s0)
    acc = vgate.accumulate(acc, r)
    j = vgate.judge_acc(acc, r["rows"], a.min_n)               # 判定は積み上げ全体（base と同じ seed だけ）で行う
    r["acc"] = j
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "a", encoding="utf-8") as f:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(a.combo, f"今回n={r['n']} 積み上げn={j['n']} (seed {s0}〜)", [(x["under_w"], x["res_w"], x["plan_w"], x["n"], x["total_n"] - x["base_total"], x["verdict"]) for x in j["rows"]])
    best = j["best"]
    if best:
        p = Path(a.store)
        cur = (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}
        cur[a.combo] = {"under_w": best["under_w"], "res_w": best["res_w"], "plan_w": best["plan_w"], "base_total": best["base_total"], "total": best["total_n"], "n": best["n"]}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump(cur, allow_unicode=True), encoding="utf-8")
        print("採用:", cur[a.combo])
    else:
        print("採用なし（base と同点か下回り、または局数不足 n<%d）" % a.min_n)
    done = best or (j["rows"] and all(x["n"] >= vgate.MAX_ACC_N for x in j["rows"]))
    accs[a.combo] = {} if done else acc                        # 採用した／十分に測って採用なしなら、次回は新しく積み上げる
    accp.parent.mkdir(parents=True, exist_ok=True)
    accp.write_text(yaml.safe_dump(accs, allow_unicode=True), encoding="utf-8")
    return r


if __name__ == "__main__":
    main()
