#!/usr/bin/env python3
"""束化カバレッジの常設測定（抽出層の語彙統合、2026-11-26）。

正準モジュール dmsim.engine.bundle_canon が全カードを束化する過程で、
「束にならない能力」「解決できない移動（'?'）」「前提にならないイベント」を
理由付きで数えて JSON で出す。黙って落ちるものが無いかをここで監視する。

使い方:
  python3 tools/bundle_coverage.py [--out coverage.json]
  python3 tools/bundle_coverage.py --legacy-diff   # 旧2系統との差分も測る
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dmsim.cards.defs import load_rules          # noqa: E402
from dmsim.engine import bundle_canon as BC       # noqa: E402


def _strict_key(b):
    prem = b.prem
    pk = None if prem is None else (prem.kind, str(prem.to), str(prem.frm),
                                    str(prem.subject), str(prem.player),
                                    str(prem.zone))
    mk = tuple((str(m.src), str(m.dst), m.ref_self, bool(m.draw), str(m.owner),
                bool(m.delayed), bool(m.blind)) for m in b.moves)
    return (b.card, b.origin, pk, mk)


def legacy_diff(rules) -> dict:
    """正準と旧2系統（zone_graph.bundles_of / 旧 loop_cond 相当）の差分。

    旧 loop_cond は統合で正準への委譲になったため、ここでは zone_graph との
    差だけを厳密キーで数える（loop_cond との差は git 履歴の実測値を参照）。
    """
    from dmsim.engine import zone_graph as Z
    canon = BC.bundles(rules)
    zg = Z.bundles_of(rules)
    ck = Counter(_strict_key(b) for b in canon)
    zk = Counter(_strict_key(b) for b in zg)
    return {
        "canon_bundles": len(canon),
        "zone_graph_bundles": len(zg),
        "common": sum((ck & zk).values()),
        "canon_only": sum((ck - zk).values()),
        "zone_graph_only": sum((zk - ck).values()),
        "canon_only_by_origin": dict(Counter(
            k[1] for k in (ck - zk).elements())),
        "zone_graph_only_by_origin": dict(Counter(
            k[1] for k in (zk - ck).elements())),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--legacy-diff", action="store_true")
    args = ap.parse_args()

    rules = load_rules()
    rep = BC.coverage(rules)
    if args.legacy_diff:
        rep["legacy_diff"] = legacy_diff(rules)
    text = json.dumps(rep, ensure_ascii=False, indent=1, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
