"""変換で足りなかったもの（未対応の op・語彙）を集計する。どの語彙を足せば何枚のカードが通るかが分かる。

    python tools/report_gaps.py                      # 既定の場所（rejects.jsonl, converted.yaml, real.yaml）を集計
    python tools/report_gaps.py --rejects a.jsonl --cards b.yaml --top 20

集計元:
- rejects.jsonl      検査（defs.parse_card）を通らなかった変換。error 文を分類する（unknown op 'x' → op:x など）。
- カード定義の source.unsupported  LLM が「表せない」と申告したもの。[{need: 必要な語彙の案, text: 該当する原文}]
- カード定義の source.notes に「未実装/未対応/表せない/近似」を含むもの（注意書き。語彙の不足とは限らない）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "data" / "cards"
NOTE_WORDS = ("未実装", "未対応", "表せない", "近似")


def categorize(error: str) -> tuple[str, str]:
    """検査のエラー文を (種類, 語) にする。語彙の不足は種類ごとに「足すもの」が決まる。"""
    error = error.removeprefix("2回とも検査を通らなかった: ")
    msg = error.split(": ", 1)[-1] if re.match(r"^[\w.\[\]/ -]+: ", error) else error
    m = re.search(r"unknown op '([^']+)'", msg)
    if m:
        return "op", m.group(1)
    m = re.search(r"op '([^']+)' has unknown arg '([^']+)'", msg)
    if m:
        return "op引数", f"{m.group(1)}.{m.group(2)}"
    m = re.search(r"op '([^']+)' missing arg '([^']+)'", msg)
    if m:
        return "op引数(不足)", f"{m.group(1)}.{m.group(2)}"
    m = re.search(r"unknown ((?:\w+ )*?\w+?) keys \[(.*)\]", msg)
    if m:
        return f"{m.group(1)}のキー", m.group(2).replace("'", "")
    m = re.search(r"unknown ([\w ]+?) '([^']*)'", msg)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"unknown (\w+) \[(.*)\]", msg)
    if m:
        return m.group(1), m.group(2).replace("'", "")
    if "モデルが変換を断った" in msg:
        return "拒否", ""
    if "id が" in msg:
        return "id不一致", ""
    return "その他", msg[:80]


def collect(rejects: list[Path], cards: list[Path]) -> dict:
    """{(種類, 語): {"cards": {id: 例の文}, "origin": 集計元}} を返す。"""
    gaps: dict = defaultdict(lambda: {"cards": {}, "origin": set()})
    for f in rejects:
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            for part in r.get("error", "").split("\n"):
                part = part.strip()
                if part:
                    g = gaps[categorize(part)]
                    g["cards"][r["id"]] = r.get("text", "")[:60].replace("\n", " / ")
                    g["origin"].add("検査エラー")
    for f in cards:
        if not f.exists():
            continue
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for c in doc.get("cards") or []:
            src = c.get("source") or {}
            for u in src.get("unsupported") or []:
                g = gaps[("申告", str(u.get("need", "?")))]
                g["cards"][c["id"]] = str(u.get("text", ""))[:60]
                g["origin"].add("LLMの申告")
            note = str(src.get("notes", ""))
            if any(w in note for w in NOTE_WORDS):
                g = gaps[("注意書き", "未実装/近似")]
                g["cards"][c["id"]] = note[:60]
                g["origin"].add("notes")
    return gaps


def render(gaps: dict, top: int) -> str:
    rows = sorted(gaps.items(), key=lambda kv: (-len(kv[1]["cards"]), kv[0]))
    if not rows:
        return "不足している語彙はありません。\n"
    lines = ["| 枚数 | 種類 | 語 | 例（カードID: 原文） |", "|---:|---|---|---|"]
    for (kind, term), g in rows[:top]:
        ids = sorted(g["cards"])
        ex = f"{ids[0]}: {g['cards'][ids[0]]}" if g["cards"][ids[0]] else ids[0]
        lines.append(f"| {len(ids)} | {kind} | {term} | {ex} |")
    if len(rows) > top:
        lines.append(f"\n（ほか {len(rows) - top} 種類）")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rejects", nargs="*", type=Path, default=[CARDS / "raw" / "rejects.jsonl"])
    ap.add_argument("--cards", nargs="*", type=Path, default=[CARDS / "converted.yaml", CARDS / "real.yaml"])
    ap.add_argument("--top", type=int, default=30)
    a = ap.parse_args(argv)
    sys.stdout.write(render(collect(a.rejects, a.cards), a.top))


if __name__ == "__main__":
    main()
