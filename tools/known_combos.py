"""既知コンボ正解集合の読み込みと検査（data/known_combos/combos.yaml）。

使い方: python tools/known_combos.py   （違反があれば終了コード1）
検査: スキーマ、id重複、tuning/holdout 間の core 部品の重なり。
"""
import sys
from pathlib import Path

import yaml

PATH = Path(__file__).resolve().parent.parent / "data" / "known_combos" / "combos.yaml"
SPLITS = {"tuning", "holdout"}
STATUS = {"verified", "hypothesis", "draft"}


def load(path=PATH):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))["combos"]


def _key(p):
    return p.get("id") or p["name"]


def core_keys(combo):
    return {_key(p) for p in combo["parts"] if p.get("role") == "core"}


def check(combos):
    errs, seen = [], set()
    for c in combos:
        if c["id"] in seen:
            errs.append(f"{c['id']}: id 重複")
        seen.add(c["id"])
        if c.get("split") not in SPLITS:
            errs.append(f"{c['id']}: split が不正")
        if c.get("status") not in STATUS:
            errs.append(f"{c['id']}: status が不正")
        if not core_keys(c):
            errs.append(f"{c['id']}: core 部品がない")
        for p in c["parts"]:
            if p.get("role") not in ("core", "support") or not p.get("name"):
                errs.append(f"{c['id']}: 部品の role/name が不正 {p}")
    for a in combos:
        for b in combos:
            if a["id"] < b["id"] and a.get("split") != b.get("split"):
                both = core_keys(a) & core_keys(b)
                if both:
                    errs.append(f"{a['id']}({a['split']}) と {b['id']}({b['split']}) が部品を共有: {sorted(both)}")
    return errs


def main():
    errs = check(load())
    for e in errs:
        print("NG", e)
    if not errs:
        print("OK")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
