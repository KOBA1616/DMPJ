"""deck_fix の時間予算の自動配分（トークンを使わない純Python）。
全体の時間上限（例 日次実行の7200秒）を、対象デッキごとの候補数と粗比較の局数に振り分ける。
- 前回途中で終わった／未実行のデッキを先に回す（その次は最後に回してから日の古い順）
- 重いデッキは前回の「1候補×1局あたりの所要秒」から見積もり、枠に収まるまで粗比較の局数→候補数の順に縮める
履歴は data/autofix/deckfix_times.yaml（{combo: {sec, cands, coarse_seeds, complete, last_run}}）。"""
from __future__ import annotations

from pathlib import Path

import yaml

DEFAULT_UNIT_SEC = 3.0     # 履歴が無いデッキの 1候補×1局あたりの所要秒（保守的な初期値）
MIN_SLOT_SEC = 120         # これ未満の枠しか残っていなければそのデッキは次回へ回す
SAFETY = 0.8               # 見積もりに使う枠の割合（粗比較の締め切りはこの割合の時点）


def load_history(path) -> dict:
    p = Path(path)
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}


def save_history(path, hist: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(yaml.safe_dump(hist, allow_unicode=True, sort_keys=True), encoding="utf-8")


def order_targets(names: list[str], hist: dict) -> list[str]:
    """未実行・前回途中で終わったものが先、あとは last_run の古い順。"""
    def key(n):
        h = hist.get(n)
        if not h:
            return (0, 0.0)
        return (1 if h.get("complete") else 0, float(h.get("last_run", 0.0)))
    return sorted(names, key=key)


def unit_sec(h: dict | None) -> float:
    if h and h.get("cands") and h.get("coarse_seeds") and h.get("sec"):
        return max(0.05, h["sec"] / (h["cands"] * h["coarse_seeds"]))
    return DEFAULT_UNIT_SEC


def allocate(h: dict | None, slot_sec: float, max_cands: int, max_cs: int, min_cands: int = 3, min_cs: int = 8, kinds: int = 4) -> tuple[int, int]:
    """枠 slot_sec に収まる (種類ごとの候補数, 粗比較の局数)。まず局数を縮め、次に候補数を縮める。
    履歴の cands は評価した候補の総数なので、見積もりは 種類ごとの候補数×kinds（deck_fix の既定は4種類）で数える。"""
    u, budget = unit_sec(h) * kinds, slot_sec * SAFETY
    cands, cs = max_cands, max_cs
    while cs > min_cs and u * cands * cs > budget:
        cs -= 1
    while cands > min_cands and u * cands * cs > budget:
        cands -= 1
    return cands, cs


def update(hist: dict, name: str, res: dict, cands: int, cs: int, now: float) -> None:
    """two_stage の結果で履歴を更新する。途中で終わった時は complete=False のままにして次回優先にする。"""
    hist[name] = {"sec": float(res.get("sec", 0.0)), "cands": int(res.get("evaluated", cands)) or cands, "coarse_seeds": cs,
                  "complete": bool(res.get("complete", True)), "last_run": now}
