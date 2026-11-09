"""仮説ゲート: 「Claude が書いた改良の下書きPR」を機械だけで検査する（採否の最終判断は人。自動マージはしない）。

検査1 触ってはいけない場所（評価の物差し・課金経路・定期ワークフロー・holdout）に触れていないか。テストの削除も不可。
検査2 同一シードの対比較で、キル指標（早さ中心の滑らかな点）が有意に良くなり、悪化した局が許容を超えないか。"""
from __future__ import annotations

import fnmatch

from ..eval.stats import paired_diff
from .loop import Rule
from .tune import _score

# 物差し・課金・定期処理・検証専用データ。ここを書き換える仮説は自動検証の対象外（人が見る）。
FORBIDDEN = (
    ".github/*", "CLAUDE.md", "tools/llm_offload/*", "tools/offload.py", "data/rules/*", "data/known_combos/*",
    "dmsim/eval/*", "dmsim/autofix/gate.py", "dmsim/autofix/loop.py", "tools/hypothesis_gate.py",
)


def check_paths(changes: list[tuple[str, str]], forbidden=FORBIDDEN) -> list[str]:
    """changes: [(git の状態 A/M/D/R.., パス)]。違反の説明を返す（空なら通過）。"""
    bad = []
    for st, path in changes:
        if any(fnmatch.fnmatch(path, pat) for pat in forbidden):
            bad.append(f"禁止パスの変更: {path}")
        elif st.startswith("D") and path.startswith("tests/"):
            bad.append(f"テストの削除: {path}")
    return bad


def compare(base: dict, cand: dict, rule: Rule = Rule(), max_worse_share: float = 0.2) -> dict:
    """base/cand: harness の戻り値（同じシード順）。verdict: accept_candidate / reject / inconclusive。"""
    sb, sc = _score(base, rule), _score(cand, rule)
    r = paired_diff(sc, sb, alpha=rule.alpha)
    worse = sum(1 for x, y in zip(sc, sb) if x < y) / len(sb) if sb else 0.0
    kb = sum(x is not None and x <= rule.turn for x in base["kill"])
    kc = sum(x is not None and x <= rule.turn for x in cand["kill"])
    if r["significant"] and r["diff"] > 0 and worse <= max_worse_share:
        v = "accept_candidate"
    elif r["significant"] and r["diff"] < 0:
        v = "reject"
    else:
        v = "inconclusive"
    return {"verdict": v, "diff": r["diff"], "ci": r["ci"], "worse_share": worse, "kills": [kb, kc], "n": r["n"]}
