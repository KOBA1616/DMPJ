"""LoopSpec の勝ち手順から、勝ちの N 手前の開始局面（評価用）を作る。計画書 §3.3。
   python tools/gen_eval_starts.py data/loops/tenmon_initial.json --levels 30 20 10 --out data/eval/auto/tenmon_initial.v1.yaml
自動で入れるのは調整用(tuning)のみ。変換未確認のカードを含む局面は unverified と use_for_primary: false が付く。"""
import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dmsim import load_rules  # noqa: E402
from dmsim.discovery import evalstarts  # noqa: E402
from dmsim.discovery.loopspec import LoopSpec  # noqa: E402
from dmsim.engine_view import defn_of, order_zone, zone_of  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("loopspec")
    ap.add_argument("--levels", type=int, nargs="*", help="勝ちまでの残り決定数の目安。省略時は全てのターン頭")
    ap.add_argument("--prepare", help="山札の並びの固定など（既定は tenmon の並び）。none で無し")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    rules = load_rules()
    approved = evalstarts.approved_ids(load_rules(only_approved=True))
    ls = LoopSpec.from_json(Path(a.loopspec).read_text(encoding="utf-8"))
    prep = None
    if a.prepare != "none" and "deck_order" in ls.source and "転生スイッチ" in ls.source["deck_order"]:
        def prep(e):
            ts, fa = "dm23ex2-cho018", "dm31-025"
            dk = zone_of(e, "deck", 0)
            order_zone(e, "deck", 0, lambda c: (defn_of(e, c) != ts, defn_of(e, c) != fa))
    starts = evalstarts.make_starts(rules, ls, approved, a.levels, prep)
    text = yaml.safe_dump({"version": evalstarts.VERSION, "starts": starts}, allow_unicode=True, sort_keys=False)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text, encoding="utf-8")
    for s in starts:
        print(s["id"], "turn", s["turn"], "unverified", s["unverified"])


if __name__ == "__main__":
    main()
