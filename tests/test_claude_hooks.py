import json
import subprocess
import sys
from pathlib import Path

HOOK = str(Path(__file__).resolve().parents[1] / "tools" / "claude_hooks.py")


def run(mode, payload):
    p = subprocess.run([sys.executable, HOOK, mode], input=json.dumps(payload), capture_output=True, text=True)
    assert p.returncode == 0  # 警告のみ。止めない
    return p.stdout


def test_log_cat_warns_only_for_full_cat():
    assert "additionalContext" in run("log-cat", {"tool_input": {"command": "cat logs/quiet/a.log"}})
    assert run("log-cat", {"tool_input": {"command": "grep x logs/quiet/a.log"}}) == ""
    assert run("log-cat", {"tool_input": {"command": "cat logs/a.log | head"}}) == ""


def test_engine_stamp_ignores_other_files_and_bad_input():
    assert run("engine-stamp", {"tool_input": {"file_path": "/x/docs/a.md"}}) == ""
    assert run("engine-stamp", {}) == ""
    assert run("unknown", {}) == ""
