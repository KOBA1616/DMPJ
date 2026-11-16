"""登録簿へ候補を通す（docs/registry-design.md）。

  python tools/registry.py            # data/registry/candidates.yaml の全候補を検証して data/registry/combos.yaml へ書く
  python tools/registry.py saga akashic
  python tools/registry.py --show     # 登録済み・落ちた候補の一覧だけ
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dmsim.base import registry  # noqa: E402

CANDIDATES = Path(__file__).resolve().parents[1] / "data" / "registry" / "candidates.yaml"


def load_candidates(path: Path = CANDIDATES) -> list[registry.Candidate]:
    return [registry.Candidate.from_dict(d) for d in yaml.safe_load(path.read_text(encoding="utf-8"))["candidates"]]


def show() -> None:
    reg = registry.load()
    for r in reg["entries"]:
        print(f"[登録] {r['id']:12s} {r['split']:10s} {'/'.join(r['types']):8s} 段2 {r['measured'].get('stage2')}")
    for r in reg["rejected"]:
        why = next(c["detail"] for c in r["checks"] if not c["ok"])
        print(f"[不可] {r['id']:12s} {r['split']:10s} {r['failed_at']:7s} {why}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args(argv)
    if a.show:
        show()
        return 0
    from dmsim import load_rules
    from dmsim.eval.verify import register
    rules = load_rules()
    for c in load_candidates():
        if a.ids and c.id not in a.ids:
            continue
        ev, _ = register(rules, c)
        print(c.id, "通過" if ev.passed else f"不可（{ev.failed_at()}）", ev.measured.get("stage2", ""), flush=True)
        for nv in registry.novelty(c):
            print("   新規性:", nv)
    show()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
