"""docs/STATUS.md の「現在の数字」節（マーカーの間）を自動生成する。

    python tools/gen_status.py          # STATUS.md を更新
    python tools/gen_status.py --check  # 数字が古ければ終了コード1（更新はしない）

数字の出どころ:
  テスト件数   tests/ の `def test_`（pytest が入っていれば --collect-only の値を優先）
  実カード枚数 data/cards/real*.yaml の cards（review の内訳つき）
  取得/台帳    cards-data ブランチの data/cards/catalog/sets.json（git show。無ければ手元のファイル）
キル率などの手で書く部分はマーカーの外に書く（このスクリプトは触らない）。
"""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STATUS = ROOT / "docs" / "STATUS.md"
BEGIN, END = "<!-- auto:begin -->", "<!-- auto:end -->"


def _run(*cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def count_tests():
    r = _run(sys.executable, "-m", "pytest", "--collect-only", "-q")
    m = re.search(r"(\d+) tests? collected", r.stdout)
    if m:
        return int(m.group(1)), "pytest"
    n = sum(len(re.findall(r"^\s*def test_", p.read_text(encoding="utf-8"), re.M))
            for p in (ROOT / "tests").glob("test_*.py"))
    return n, "def test_ の数（パラメータ展開前）"


def count_cards():
    total, reviews = 0, Counter()
    for p in sorted((ROOT / "data/cards").glob("real*.yaml")):
        for c in (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("cards", []):
            total += 1
            reviews[(c.get("source") or {}).get("review", "none")] += 1
    return total, reviews


def load_sets():
    r = _run("git", "show", "origin/cards-data:data/cards/catalog/sets.json")
    if r.returncode == 0:
        return json.loads(r.stdout)["products"]
    p = ROOT / "data/cards/catalog/sets.json"
    return json.loads(p.read_text(encoding="utf-8"))["products"] if p.exists() else None


def build():
    tests, how = count_tests()
    cards, reviews = count_cards()
    rev = " / ".join(f"{k} {v}" for k, v in sorted(reviews.items()))
    lines = [f"- テスト: {tests} 件（{how}）",
             f"- 実カード（DSL変換済み）: {cards} 枚（確認状態: {rev}）"]
    sets = load_sets()
    if sets is None:
        lines.append("- 取得/台帳: 台帳(sets.json)が読めない（`git fetch origin cards-data` を実行）")
    else:
        ids = sum(len(p["ids"]) if isinstance(p.get("ids"), list) else p.get("ids", 0) for p in sets.values())
        total = sum(p.get("total", 0) for p in sets.values())
        fetched = sum(len(p["fetched"]) if isinstance(p.get("fetched"), list) else p.get("fetched", 0) for p in sets.values())
        listed = sum(1 for p in sets.values() if p.get("listed"))
        lines.append(f"- 台帳: 商品 {len(sets)} 件（一覧取得済み {listed}）、カード {total} 枚中 ID取得 {ids}")
        lines.append(f"- 詳細取得済み: {fetched} 枚（{fetched / total:.1%}）" if total else "- 詳細取得済み: 0 枚")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    text = STATUS.read_text(encoding="utf-8")
    pat = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
    if not pat.search(text):
        sys.exit(f"{STATUS} に {BEGIN} ... {END} がない")
    new = pat.sub(lambda _: f"{BEGIN}\n{build()}\n{END}", text)
    if a.check:
        sys.exit(0 if new == text else 1)
    STATUS.write_text(new, encoding="utf-8")
    print(build())


if __name__ == "__main__":
    main()
