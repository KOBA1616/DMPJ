"""既知コンボの部品データから段階目標の鎖を自動生成する。python tools/gen_stages.py saga [--from leaf|loopspec] [--out PATH]
出力は data/eval/stages/<combo>.generated.yaml（手書きの <combo>.yaml は上書きしない）。v_gate.py の --stages に渡せる。"""
import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.discovery.loopspec import LoopSpec  # noqa: E402
from dmsim.plan.stagegen import stages_from_leaf_parts, stages_from_loopspec  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("combo")
    ap.add_argument("--from", dest="src", choices=["leaf", "loopspec"], default="leaf")
    ap.add_argument("--graph", action="store_true", help="前提つきの段の集合（同じゾーンの部品は並列）として <combo>.graph.yaml に出す")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    combos = yaml.safe_load(Path("data/known_combos/combos.yaml").read_text(encoding="utf-8"))["combos"]
    c = next(x for x in combos if x["id"] == a.combo)
    if a.graph:
        from dmsim.plan.stagegen import graph_from_leaf_parts, graph_from_loopspec
        g = graph_from_loopspec(LoopSpec.from_json(Path(c["loopspec"]).read_text(encoding="utf-8"))) if a.src == "loopspec" else graph_from_leaf_parts(c["leaf_parts"])
        out = Path(a.out or f"data/eval/stages/{a.combo}.graph.yaml")
        out.write_text("# tools/gen_stages.py --graph による自動生成（dmsim/plan/stagegen.py）。手で直さず、元データを直して作り直す。\n"
                       "# 段は前提つきの有向グラフ（dmsim/plan/stagegraph.py）。requires が無い段どうしは並列。\n"
                       + yaml.safe_dump({"stages": g.to_stage_dicts()}, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(out, len(g.nodes), "段（グラフ）")
        return
    if a.src == "loopspec":
        st = stages_from_loopspec(LoopSpec.from_json(Path(c["loopspec"]).read_text(encoding="utf-8")))
    else:
        st = stages_from_leaf_parts(c["leaf_parts"])
    out = Path(a.out or f"data/eval/stages/{a.combo}.generated.yaml")
    out.write_text("# tools/gen_stages.py による自動生成（dmsim/plan/stagegen.py）。手で直さず、元データを直して作り直す。\n"
                   + yaml.safe_dump({"stages": st}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(out, len(st), "段")


if __name__ == "__main__":
    main()
