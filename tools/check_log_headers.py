"""実験ログのヘッダ点検（lint）: 設定の完全記録を機械で確かめる。

過去に exhaustive_multiturn のログヘッダへ order（順序方式）が記録されておらず、
データの出所をファイル更新時刻から復元する羽目になった。その再発防止として、
各ログの1行目（kind="header"）に tool ごとの必須の設定項目があるかを点検する。

必須項目:
- 共通: kind="header"、tool、engine_version、settings
- exhaustive_multiturn: settings.order、settings.stages
- exhaustive_crossturn: settings.mode、settings.stage、settings.order、
  settings.trim_order。さらに trim_order="plan" の時は settings.stages_file
- exhaustive_proto: settings があること（共通の点検で足りる）

使い方:
  python tools/check_log_headers.py 'logs/*.jsonl'
不備が1件でもあれば終了コード1。
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

# tool ごとに settings の必須キー。値が無い（欠落・None・空文字）場合は不備とする
REQUIRED_SETTINGS: dict[str, list[str]] = {
    "exhaustive_multiturn": ["order", "stages"],
    "exhaustive_crossturn": ["mode", "stage", "order", "trim_order"],
    "exhaustive_proto": [],
}


def _present(settings: dict, key: str) -> bool:
    v = settings.get(key)
    return v is not None and v != ""


def check_file(path: Path) -> tuple[list[str], str | None]:
    """(不備の項目名リスト, tool名) を返す。tool が判定できない場合は None。"""
    try:
        with path.open(encoding="utf-8") as f:
            first = f.readline()
    except OSError as e:
        return [f"<読み取り不可: {e}>"], None
    if not first.strip():
        return ["header"], None
    try:
        head = json.loads(first)
    except json.JSONDecodeError:
        return ["header"], None
    if not isinstance(head, dict) or head.get("kind") != "header":
        return ["header"], None

    missing: list[str] = []
    tool = head.get("tool")
    if not tool:
        missing.append("tool")
    if not head.get("engine_version"):
        missing.append("engine_version")
    settings = head.get("settings")
    if not isinstance(settings, dict) or not settings:
        missing.append("settings")
        return missing, tool
    if tool in REQUIRED_SETTINGS:
        for key in REQUIRED_SETTINGS[tool]:
            if not _present(settings, key):
                missing.append(f"settings.{key}")
        # trim_order=plan の時は、どの鎖で保持したかが再現に必須
        if tool == "exhaustive_crossturn" and settings.get("trim_order") == "plan":
            if not _present(settings, "stages_file"):
                missing.append("settings.stages_file")
    return missing, tool


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("patterns", nargs="+", help="点検する JSONL ログの glob（複数可）")
    a = ap.parse_args()

    files = sorted({p for pat in a.patterns for p in glob.glob(pat)})
    if not files:
        print("対象ファイルが無い", file=sys.stderr)
        return 1

    n_ok = 0
    n_missing = 0
    n_skip = 0
    for name in files:
        path = Path(name)
        missing, tool = check_file(path)
        if tool is not None and tool not in REQUIRED_SETTINGS:
            print(f"SKIP    {name} (対象外の tool: {tool})")
            n_skip += 1
            continue
        if missing:
            print(f"MISSING {name} [{', '.join(missing)}]")
            n_missing += 1
        else:
            print(f"OK      {name}")
            n_ok += 1
    print(f"集計: {len(files)} ファイル / OK {n_ok} / MISSING {n_missing} / SKIP {n_skip}")
    return 1 if n_missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
