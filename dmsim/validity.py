"""測定の妥当性ゲート: 陽性対照（既知コンボがランダムな組より上位に出る）を通っていない測定器の結果は「採用不可」と印を付ける。

背景: 甘い開始条件で何でも勝つ状態の結果（PR #299/#300）を、対照で確かめずに採用してしまった。
使い方: 対照を回す側が write_stamp() を呼び、結果を出す側は annotate() で印を付ける。
印は測定器（dmsim/*.py と data/cards の中身）が変わると失効する。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAMP = ROOT / "data" / "eval" / "control_stamp.json"
MIN_PERCENTILE = 0.9        # 調整用コンボの中核が、ランダムな組のこの割合より高い点を取ること


def fingerprint(root: Path = ROOT) -> str:
    """測定器（エンジン・探索・評価のコード）とカードデータの指紋。"""
    h = hashlib.sha256()
    files = sorted((root / "dmsim").rglob("*.py")) + sorted((root / "data" / "cards").rglob("*.yaml"))
    for f in files:
        h.update(str(f.relative_to(root)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:16]


def judge(rows: list[dict], min_percentile: float = MIN_PERCENTILE) -> tuple[bool, str]:
    """対照の行（combo, split, percentile）から合否。調整用(tuning)の全コンボが基準を満たすこと。"""
    tune = [r for r in rows if r.get("split") == "tuning"]
    if not tune:
        return False, "調整用の既知コンボの対照結果がない"
    bad = [r["combo"] for r in tune if r["percentile"] < min_percentile]
    if bad:
        return False, f"陽性対照に届かない既知コンボ: {sorted(set(bad))}（基準 {min_percentile}）"
    return True, "ok"


def write_stamp(rows: list[dict], path: Path = STAMP, root: Path = ROOT) -> dict:
    ok, why = judge(rows)
    st = {"passed": ok, "reason": why, "fingerprint": fingerprint(root), "rows": rows}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    return st


def status(path: Path = STAMP, root: Path = ROOT) -> tuple[bool, str]:
    try:
        st = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return False, "陽性対照の印がない（combo_screen --control を先に回す）"
    if st.get("fingerprint") != fingerprint(root):
        return False, "測定器かカードデータが変わり、印が古い（対照をやり直す）"
    if not st.get("passed"):
        return False, st.get("reason", "陽性対照に不合格")
    return True, "ok"


def annotate(result: dict, path: Path = STAMP, root: Path = ROOT) -> dict:
    """結果に妥当性の印を付ける。valid=False の結果は採用（デッキ・組の確定、設定の保存）に使わない。"""
    ok, why = status(path, root)
    return {**result, "validity": {"valid": ok, "reason": why}}
