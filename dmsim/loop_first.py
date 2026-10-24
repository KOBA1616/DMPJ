"""ループ発見と勝ち筋探索の分離（2段探索）。

1段目 discover_loops: 勝ちを求めず、配置から1ターンの探索を行い、見つかったループ（骨格が戻る行動列と
カウンタの差分 Δ）を集める。証明書は再生できるので、結果は決定的に再現できる。
2段目 seek_wins: 見つけたループごとに、周回数を変えてストックした局面（山札を残り何枚にするか、など）から
勝ちを探索する。周回数がパラメータになるので、「ループ直後に抜ける」「残り1枚まで回す」の2通りに限らない。

  python -m dmsim.loop_first --setup tests/saga_typhoon_setup.yaml --discover-budget 1500 --seek-budget 1500
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .engine import Engine
from .engine.core import IllegalAnswer
from .loop import LoopCertificate, fast_forward, verify
from .solitaire import WIN, TurnSearch


@dataclass
class Finding:
    cert: LoopCertificate
    start: Engine = field(repr=False)
    verified: bool = False
    wins: list[dict] = field(default_factory=list)       # {"cycles": n, "nodes": m, "turn": t}
    tried: list[dict] = field(default_factory=list)

    def summary(self) -> dict:
        return {"delta": self.cert.delta, "length": len(self.cert.actions), "limit": self.cert.limit,
                "win_by": self.cert.win_by, "verified": self.verified, "tried": self.tried, "wins": self.wins}


def discover_loops(eng: Engine, me: int = 0, budget: int = 1500) -> list[Finding]:
    """eng（自分の決定待ち）から、そのターンに作れるループを集める。"""
    ts = TurnSearch(me, budget)
    ts.collect = []
    ts.run(eng)
    out = []
    for snap, cert in ts.collect:
        f = Finding(cert, snap)
        f.verified = verify(snap, cert, times=1).verified >= 1
        out.append(f)
    return out


def cycle_counts(cert: LoopCertificate, deck_now: int, limit_cap: int = 60) -> list[int]:
    """試す周回数。0（回さない）、最大（山札を残り1枚まで等）、その間のいくつか。"""
    top = int(cert.limit) if math.isfinite(cert.limit) else limit_cap
    top = min(top, limit_cap)
    ns = {0, top, top - 1, max(0, top - 2), top // 2}
    return sorted(n for n in ns if 0 <= n <= top)


def seek_wins(f: Finding, me: int = 0, budget: int = 1500, stop_at_first: bool = True) -> Finding:
    if not f.verified:
        return f
    for n in cycle_counts(f.cert, len(f.start.zlist("deck", me))):
        e = f.start.clone()
        try:
            fast_forward(e, f.cert, n)
        except IllegalAnswer:
            f.tried.append({"cycles": n, "error": "replay"})
            continue
        ts = TurnSearch(me, budget)
        ts.burn_stock = False
        leaf, st = ts.run(e)
        r = leaf.s.result
        won = r is not None and r["winner"] == me
        f.tried.append({"cycles": n, "nodes": st.nodes, "won": won})
        if won:
            f.wins.append({"cycles": n, "nodes": st.nodes, "turn": r["turn"], "reason": r["reason"]})
            if stop_at_first:
                break
    return f


def two_stage(eng: Engine, me: int = 0, discover_budget: int = 1500, seek_budget: int = 1500) -> list[Finding]:
    found = discover_loops(eng, me, discover_budget)
    for f in found:
        seek_wins(f, me, seek_budget)
    return found


def main(argv=None):
    import argparse
    import json
    from pathlib import Path

    import yaml

    from . import scenario
    from .defs import load_rules
    ap = argparse.ArgumentParser(description="ループ発見→勝ち筋探索の2段探索")
    ap.add_argument("--setup", required=True, help="配置 spec（YAML。dmsim.scenario の形）")
    ap.add_argument("--discover-budget", type=int, default=1500)
    ap.add_argument("--seek-budget", type=int, default=1500)
    a = ap.parse_args(argv)
    rules = load_rules()
    spec = yaml.safe_load(Path(a.setup).read_text(encoding="utf-8"))
    eng = scenario.build(rules, spec)
    for f in two_stage(eng, 0, a.discover_budget, a.seek_budget):
        print(json.dumps(f.summary(), ensure_ascii=False))


if __name__ == "__main__":
    main()
