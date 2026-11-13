"""仮説ゲート（機械検証）。Claude が書いた改良の下書きPRを、人が見る前に機械で検査する。自動マージはしない。
  main 側:  python tools/hypothesis_gate.py baseline --out logs/gate_base.json   （改良前の木で実行）
  改良側:   python tools/hypothesis_gate.py check --base-ref origin/main --baseline logs/gate_base.json
結果は標準出力にJSON。終了コード 0=accept_candidate / 1=reject / 2=inconclusive / 3=禁止パスやテスト失敗。
対象・シード・予算は固定（既定: --targets の最初の非holdout対象 knight_dmc 等、seeds 1..N、保存済みノブ）。"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exec_tier  # noqa: E402
from dmsim.autofix import Knobs, Rule, harness_measure  # noqa: E402
from dmsim.autofix.batch import default_board, default_need  # noqa: E402
from dmsim.autofix.gate import check_paths, compare  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.eval.progress import ProgressSpec  # noqa: E402
from dmsim.autofix.partsgenome import load_specs_evolved  # noqa: E402
from dmsim.autofix.valuelearn import load_model  # noqa: E402
from dmsim.eval.measure import load_deck  # noqa: E402


def measure_all(a) -> dict:
    """対象ごとの測定を連結（局の並びは対象順・シード順で固定）。"""
    combos = {c["id"]: c for c in yaml.safe_load(Path("data/known_combos/combos.yaml").read_text(encoding="utf-8"))["combos"]}
    ts = [t for t in yaml.safe_load(Path(a.targets).read_text(encoding="utf-8"))["targets"]
          if combos.get(t["combo"], {}).get("split") != "holdout" and (not a.only or t["combo"] in a.only.split(","))]
    store = (yaml.safe_load(Path(a.store).read_text(encoding="utf-8")) or {}) if Path(a.store).exists() else {}
    rules, specs, out = load_rules(), load_specs_evolved(), {"kill": [], "board": [], "cards": []}
    for t in ts:
        c = combos[t["combo"]]
        k = Knobs(**{**Knobs().__dict__, **store.get(t["combo"], {})})
        opp = load_deck(t["opp_deck"]) if t.get("opp_deck") else ["T001"] * 40
        deck = load_deck(t["deck"])
        spec, _ = exec_tier.exec_spec(rules, t, deck, cold=a.cold)     # 実行層（仕込み済み開始）で測る
        m = harness_measure(rules, deck, opp, list(range(1, a.seeds + 1)), spec,
                            ProgressSpec(board=default_board(c), cards=default_need(c)), specs[t["combo"]],
                            max_turn=a.turns, workers=a.workers, value_model=load_model(t["combo"]))(k)
        for key in out:
            out[key] += m[key]
    return out


def changed_files(base_ref: str) -> list[tuple[str, str]]:
    r = subprocess.run(["git", "diff", "--name-status", f"{base_ref}...HEAD"], capture_output=True, text=True, check=True)
    return [(ln.split("\t")[0], ln.split("\t")[-1]) for ln in r.stdout.splitlines() if ln.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["baseline", "check"])
    ap.add_argument("--targets", default="data/autofix/targets.yaml")
    ap.add_argument("--only", default="knight_dmc,akashic", help="対象 combo（カンマ区切り。固定すること）")
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--store", default="data/autofix/knobs.yaml")
    ap.add_argument("--cold", action="store_true", help="通常の開幕で測る（既定は仕込み済み開始の実行層）")
    ap.add_argument("--out")
    ap.add_argument("--baseline")
    ap.add_argument("--base-ref", default="origin/main")
    ap.add_argument("--test-cmd", default="python -m pytest -q -x --deselect tests/test_file_schemas.py::test_card_files_match_schema",
                    help="空文字でテストを省く")
    a = ap.parse_args(argv)
    if a.mode == "baseline":
        Path(a.out).write_text(json.dumps(measure_all(a)), encoding="utf-8")
        return 0
    bad = check_paths(changed_files(a.base_ref))
    if bad:
        print(json.dumps({"verdict": "forbidden", "violations": bad}, ensure_ascii=False))
        return 3
    if a.test_cmd and subprocess.run(a.test_cmd.split()).returncode != 0:
        print(json.dumps({"verdict": "tests_failed"}))
        return 3
    res = compare(json.loads(Path(a.baseline).read_text(encoding="utf-8")), measure_all(a), Rule(turn=a.turns))
    print(json.dumps(res, ensure_ascii=False))
    return {"accept_candidate": 0, "reject": 1}.get(res["verdict"], 2)


if __name__ == "__main__":
    sys.exit(main())
