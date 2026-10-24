"""機械的な作業を無料モデルに投げる CLI。使い方は docs/offload.md。

    git diff | python tools/offload.py review-diff
    pytest -q 2>&1 | python tools/offload.py digest            # LLM なし（ルールベース）
    pytest -q 2>&1 | python tools/offload.py summarize-log     # 無料モデルで要約
    python tools/offload.py affected-tests                      # 変更に関係するテストだけ
    python tools/offload.py ask --instruction "…" < file

終了コード 0=成功 / 3=ESCALATE（無料モデルでは済まなかった。Claude で処理してよい） / 2=課金の兆候で停止
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from llm_offload import (DAILY_LIMIT, MAX_CHARS, TASKS, Escalate, Fatal, affected_tests, ask,  # noqa: E402
                         digest_pytest, scrub)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("task", choices=[*TASKS, "ask", "digest", "affected-tests"])
    ap.add_argument("file", nargs="?", help="入力ファイル（省略時は標準入力）")
    ap.add_argument("--instruction", help="ask 用の指示")
    ap.add_argument("--provider", default="opencode-cli", choices=["opencode-cli", "opencode"])
    ap.add_argument("--model")
    ap.add_argument("--daily-limit", type=int, default=DAILY_LIMIT)
    ap.add_argument("--max-chars", type=int, default=MAX_CHARS)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--base", default="origin/main", help="affected-tests の比較元")
    a = ap.parse_args(argv)

    if a.task == "affected-tests":
        r = subprocess.run(["git", "diff", "--name-only", a.base], capture_output=True, text=True)
        files = [ln for ln in r.stdout.split() if ln]
        t = affected_tests(files)
        print("pytest -q " + " ".join(t) if t else "pytest -q")
        return 0
    text = Path(a.file).read_text(encoding="utf-8", errors="replace") if a.file else sys.stdin.read()
    if a.task == "digest":
        print(scrub(digest_pytest(text)))
        return 0
    if a.task == "ask" and not a.instruction:
        ap.error("ask には --instruction が必要")
    try:
        r = ask(a.task, text, instruction=a.instruction, provider=a.provider, model=a.model,
                daily_limit=a.daily_limit, max_chars=a.max_chars, use_cache=not a.no_cache)
    except Escalate as e:
        print(f"ESCALATE: {e}", file=sys.stderr)
        return 3
    except Fatal as e:
        print(f"STOP（課金の兆候・許可外）: {scrub(str(e))}", file=sys.stderr)
        return 2
    print(r.text)
    print(f"[{r.model}{' cache' if r.cached else ''}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
