"""長い出力のコマンドを実行し、全文はファイルへ、画面には要約だけを返す（トークン節約用）。

使い方: python tools/run_quiet.py [--log logs/run.log] [--context 5] [--tail 15] -- <コマンド...>
  例:   python tools/run_quiet.py -- python -m pytest tests/test_x.py
全文は logs/quiet/<時刻>.log（既定。logs/ は git 管理外）に必ず残る。
画面に出すもの: 終了コード・行数・末尾 N 行・エラー行（Traceback/FAILED/Error 等）の前後 C 行。
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

PAT = re.compile(r"Traceback|^FAILED|^ERROR|Error\b|AssertionError|\bfailed\b|^E  ", re.M)


def summarize(lines: list[str], context: int, tail: int, max_hits: int = 5) -> str:
    out: list[str] = []
    hits = [i for i, l in enumerate(lines) if PAT.search(l)]
    shown: set[int] = set()
    groups = 0
    for i in hits:
        if i in shown:
            continue
        if groups >= max_hits:
            break
        lo, hi = max(0, i - context), min(len(lines), i + context + 1)
        out.append(f"--- 行 {lo + 1}-{hi} ---")
        out.extend(lines[lo:hi])
        shown.update(range(lo, hi))
        groups += 1
    if len(hits) and groups >= max_hits:
        out.append(f"... エラー行はほかにもあり（計 {len(hits)} 行）。全文はログを参照")
    out.append(f"--- 末尾 {min(tail, len(lines))} 行 ---")
    out.extend(lines[-tail:])
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", default=None)
    ap.add_argument("--context", type=int, default=5)
    ap.add_argument("--tail", type=int, default=15)
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    if not cmd:
        ap.error("コマンドが無い")
    log = Path(a.log or f"logs/quiet/{time.strftime('%Y%m%d-%H%M%S')}.log")
    log.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with log.open("w", encoding="utf-8", errors="replace") as f:
        rc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT).returncode
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    print(f"終了コード {rc} / {len(lines)} 行 / {time.time() - t0:.1f} 秒 / 全文: {log}")
    print(summarize(lines, a.context, a.tail) if rc != 0 or len(lines) <= a.tail else
          f"--- 末尾 {a.tail} 行 ---\n" + "\n".join(lines[-a.tail:]))
    return rc


if __name__ == "__main__":
    sys.exit(main())
