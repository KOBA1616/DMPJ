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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--combo", default="tenmon")
    ap.add_argument("--targets", default="data/autofix/targets.yaml")
    ap.add_argument("--stages", help="段階目標のYAML（既定 data/eval/stages/<combo>.yaml）")
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--width", type=int, default=40)
    ap.add_argument("--seconds", type=int, default=0, help="時間の上限（0=無制限）。超えたら残りの seed を測らない")
    ap.add_argument("--store", default="data/autofix/vweights.yaml")
    ap.add_argument("--out", default="logs/v_gate.jsonl")
    a = ap.parse_args(argv)
    t = next(x for x in yaml.safe_load(Path(a.targets).read_text(encoding="utf-8"))["targets"] if x["combo"] == a.combo)
    st = vgate.load_stages(a.stages or vgate.stage_path(a.combo))
    stages = [s["target"] for s in st["stages"][1:]]
    keys = list(st["stages"][0]["target"]["hand"])             # 先頭の段（keys_in_hand）を強制開始にする
    rules = load_rules()
    deck = load_deck(t["deck"])
    t0 = time.time()
    r = vgate.run_gate(rules, deck, ["T001"] * 40, keys, stages, range(1, a.seeds + 1), width=a.width,
                       deadline=(t0 + a.seconds) if a.seconds else None)
    r.update(combo=a.combo, sec=round(time.time() - t0))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "a", encoding="utf-8") as f:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(a.combo, f"n={r['n']} base={r['base_total']}", [(x["under_w"], x["res_w"], x.get("plan_w", 0.0), x["total_n"], x["verdict"]) for x in r["rows"]])
    if r["best"]:
        p = Path(a.store)
        cur = (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}
        cur[a.combo] = {"under_w": r["best"]["under_w"], "res_w": r["best"]["res_w"], "plan_w": r["best"].get("plan_w", 0.0), "base_total": r["base_total"], "total": r["best"]["total_n"], "n": r["n"]}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump(cur, allow_unicode=True), encoding="utf-8")
        print("採用:", cur[a.combo])
    else:
        print("採用なし（base と同点か下回り）")
    return r


if __name__ == "__main__":
    main()
