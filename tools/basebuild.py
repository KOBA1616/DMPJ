"""中核を固定して基盤を選ぶ（dmsim/discovery/basebuild.py）。
  python tools/basebuild.py build saga akashic       # 貪欲に選んで data/decks/basebuild_<名前>.yaml と結果 JSON を書く
  python tools/basebuild.py compare saga akashic     # 現行デッキと選んだデッキを通常開幕40局（標準設定）で比べる（macro 有効時の段2も）
中核は data/known_combos/combos.yaml の parts の role: core を各4枚（ID の無い中核があれば data/registry/candidates.yaml の core）。入口局面は data/loops/entry/<名前>.json。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dmsim.base.registry import load_candidates, load_known_combos  # noqa: E402
from dmsim import load_rules  # noqa: E402
from dmsim.discovery import basebuild as B  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "discovery" / "basebuild"


def core_of(name: str) -> dict:
    """既知コンボの parts の role: core（各4枚）。ID の無い中核があれば、登録簿の候補（data/registry/candidates.yaml）の core を使う。"""
    kc = {c["id"]: c for c in load_known_combos()}
    parts = [p for p in kc[name]["parts"] if p.get("role") == "core"]
    if all(p.get("id") for p in parts):
        return {p["id"]: B.COPIES for p in parts}
    cands = {c["id"]: c for c in load_candidates()}
    return {c["id"]: B.COPIES for c in cands[name]["core"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["build", "compare"])
    ap.add_argument("names", nargs="+")
    ap.add_argument("--entry", default=None, help="入口局面の名前（既定はコンボ名と同じ）")
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--route", default=None, help="経路の名前（data/loops/route/）。build は段の進みを基準に入れ、経路札の温存つきで回す")
    ap.add_argument("--tag", default="", help="出力の名前に付ける接尾辞（前の結果を残すとき）")
    a = ap.parse_args(argv)
    rules = load_rules()
    OUT.mkdir(parents=True, exist_ok=True)
    for name in a.names:
        entry = a.entry or name
        if a.mode == "build":
            b = B.build(rules, core_of(name), entry, log=lambda s: print(s, flush=True), route=a.route)
            rec = {"combo": name, "entry": entry, "core": core_of(name), "added": b.added, "score": b.score, **b.measured,
                   "approval": B.approval_status(b.deck)}
            (OUT / f"{name}{a.tag}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            (ROOT / "data/decks" / f"basebuild_{name}{a.tag}.yaml").write_text(yaml.safe_dump(
                {"name": f"basebuild_{name}{a.tag}", "note": "tools/basebuild.py build が選んだデッキ（中核固定・基盤を貪欲に選択）", "combos": [name],
                 "deck": b.deck}, allow_unicode=True, sort_keys=False), encoding="utf-8")
            print(name, "採用", [x["name"] for x in b.added], "点", round(b.score, 2), flush=True)
        else:
            from dmsim.eval import loop_entry as L
            from dmsim.eval.api import measure_assembly
            from dmsim.search import macro
            cur = L.deck_of(L.load(entry))
            new = yaml.safe_load((ROOT / "data/decks" / f"basebuild_{name}.yaml").read_text(encoding="utf-8"))["deck"]
            seeds = range(1, a.games + 1)
            res = {}
            for label, deck in (("現行", cur), ("選択", new)):
                for on in (False, True):
                    macro.enable(on)
                    rows = measure_assembly(rules, entry, deck, seeds)
                    res[f"{label}{'・手あり' if on else ''}"] = B.summary(rows)
                    print(name, label, "macro" if on else "", res[f"{label}{'・手あり' if on else ''}"], flush=True)
            macro.enable(None)
            (OUT / f"{name}_compare.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
