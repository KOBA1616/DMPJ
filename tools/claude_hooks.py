"""Claude Code フック（警告だけを出し、操作は止めない。常に終了コード 0）。

  python tools/claude_hooks.py engine-stamp   # PostToolUse(Edit|Write): dmsim/engine を触ったら Rust スタンプの古さを警告
  python tools/claude_hooks.py log-cat        # PreToolUse(Bash): logs/ の全文 cat を警告
標準入力はフックの JSON。警告は additionalContext として Claude に渡る。
"""
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def _emit(event: str, msg: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": msg}}, ensure_ascii=False))


def engine_stamp(data: dict) -> None:
    path = str((data.get("tool_input") or {}).get("file_path", "")).replace("\\", "/")
    if "dmsim/engine/" not in path or not path.endswith(".py"):
        return
    sys.path.insert(0, ROOT)
    try:
        from dmsim.engine import rustcore
        cur = open(rustcore.STAMP, encoding="utf-8").read().split()[0]
        stale = cur != rustcore.engine_hash()
    except Exception:
        return
    if stale:
        _emit("PostToolUse", "Rust スタンプが古い（Rust は無効化され Python のみで動く）。dmcore を作り直して tests/test_rust_*.py を通し、"
              "`python tools/rust_stamp.py` で記録し直す。")


def log_cat(data: dict) -> None:
    cmd = str((data.get("tool_input") or {}).get("command", ""))
    if re.search(r"\b(cat|type)\s+[^|;&]*logs/", cmd) and "|" not in cmd:
        _emit("PreToolUse", "logs/ のログを全文 cat しない。grep や sed -n で該当箇所だけ見る（CLAUDE.md の出力節約）。")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    try:
        {"engine-stamp": engine_stamp, "log-cat": log_cat}.get(argv[0] if argv else "", lambda d: None)(data)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
