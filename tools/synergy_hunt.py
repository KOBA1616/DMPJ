"""直接つながる2枚組の発見を1コマンドで回す（dmsim/discovery/synergy_hunt.py の run）。

  python tools/synergy_hunt.py --out /tmp/sh.json            拾う→4デッキ比較（段階1・40局、参考 2b）→ candidates.yaml の synergy_hunt に記録
  python tools/synergy_hunt.py --pick-only                    拾った組の一覧だけ出す
途中保存: --out の隣に <out>.base.json / <out>.ref.json を書き、あれば読み直す（止まっても済んだ相手は測り直さない）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dmsim.discovery import synergy_hunt as SH  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--seeds", type=int, default=40)
    ap.add_argument("--opp", default="1")
    ap.add_argument("--ref", default="2b")
    ap.add_argument("--strong", type=float, default=0.3, help="片方だけの寄与（割った盾）がこれ以上の札は除く")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--pick-only", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    opp = int(a.opp) if a.opp.isdigit() else a.opp
    ref = None if a.ref == "none" else (int(a.ref) if a.ref.isdigit() else a.ref)
    if a.pick_only:
        import yaml

        from dmsim.base.store import REPO
        from dmsim.cards.defs import load_rules
        rules = load_rules()
        st = SH._strong_from_yaml(yaml.safe_load((REPO / "data/registry/candidates.yaml").read_text(encoding="utf-8")), a.strong)
        pk = SH.pick(rules, strong=st, limit=a.limit)
        for p in pk["pairs"]:
            print(p["a"], p["b"], p["kinds"], p["turn"], " + ".join(p["names"]))
        print(f"つながる組 {pk['linked']}、選んだ組 {len(pk['pairs'])}、単独で強い札 {len(st)}、効果の欠けた札 {len(pk["excluded_missing"])}")
        if a.out:
            a.out.write_text(json.dumps(pk, ensure_ascii=False, indent=1), encoding="utf-8")
        return 0
    SH.run(limit=a.limit, seeds=a.seeds, opp=opp, ref=ref, strong=a.strong, workers=a.workers, out=a.out, write=not a.no_write,
           log=lambda m: print(m, flush=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
