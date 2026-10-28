"""原文を API なしで調べて、変換に取りかかる前に「どんな文が何枚あるか」を数える。

    python tools/survey_text.py data/cards/raw/by_product --top 40
    python tools/survey_text.py raw.jsonl --uncovered      # 変換済みカードの文に無いものだけ

- 文を正規化（括弧書き・カード名・数字・「」内を畳む）して、同じ形の文を持つカードの枚数で並べる。
  枚数の多い文を先に語彙化すれば、少ない作業で多くのカードが通る。
- 変換済みカード（data/cards/*.yaml の text）に同じ形の文があれば「済」。無ければ新しい語彙が要る可能性が高い。
- 先頭が既知のキーワード能力（data/rules/keywords.yaml）で始まる行は、キーワード欄にまとめる。
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from convert_cards import load_rows  # noqa: E402

DATA = ROOT / "data"


def strip_parens(text: str) -> str:
    """括弧書きの注釈を消す（入れ子・括弧内の句点も含む）。"""
    prev = None
    while prev != text:
        prev, text = text, re.sub(r"[（(][^（）()]*[）)]", "", text)
    return text


def lines_of(text: str) -> list[str]:
    return [x.strip(" /　") for x in re.split(r"\n| / ", strip_parens(text)) if x.strip(" /　")]


def normalize(sentence: str, name: str = "") -> str:
    s = sentence
    if name:
        s = s.replace(name, "〈名〉")
    s = re.sub(r"「[^」]*」", "「…」", s)
    s = re.sub(r"[0-9０-９]+", "N", s)
    return re.sub(r"\s+", "", s)


def sentences(text: str) -> list[str]:
    out = []
    for line in text.split("\n"):
        out += [p + ("。" if i < len(line.split("。")) - 1 else "") for i, p in enumerate(line.split("。")) if p.strip()]
    return out


def keyword_names() -> list[str]:
    kw = yaml.safe_load((DATA / "rules" / "keywords.yaml").read_text(encoding="utf-8"))["keywords"]
    return sorted((v["ja"] for v in kw.values()), key=len, reverse=True)


def covered_forms() -> set[str]:
    forms: set[str] = set()
    from dmsim.cardfiles import card_files
    for f in card_files():
        for c in (yaml.safe_load(f.read_text(encoding="utf-8")) or {}).get("cards") or []:
            if (c.get("source") or {}).get("review") == "rejected":
                continue
            for part in lines_of(str(c.get("text", ""))):
                forms |= {normalize(x, c.get("name", "")) for x in sentences(part)}
    return forms


def survey(rows: list[dict]) -> dict:
    kws, covered = keyword_names(), covered_forms()
    forms: dict[str, dict] = defaultdict(lambda: {"cards": {}, "covered": False})
    kw_count: dict[str, set] = defaultdict(set)
    for r in rows:
        for line in lines_of(r.get("text", "")):
            head = next((k for k in kws if normalize(line).startswith(normalize(k))), None)
            if head and len(normalize(line)) <= len(normalize(head)) + 1:     # 説明だけの行
                kw_count[head].add(r["id"])
                continue
            for sent in sentences(line):
                n = normalize(sent, r.get("name", ""))
                if n:
                    g = forms[n]
                    g["cards"].setdefault(r["id"], sent.strip())
                    g["covered"] = n in covered
    return {"forms": forms, "keywords": kw_count, "cards": len(rows)}


def render(sv: dict, top: int, uncovered: bool) -> str:
    items = [(k, g) for k, g in sv["forms"].items() if not (uncovered and g["covered"])]
    items.sort(key=lambda kg: (-len(kg[1]["cards"]), kg[0]))
    total = len(sv["forms"])
    cov = sum(1 for g in sv["forms"].values() if g["covered"])
    lines = [f"原文 {sv['cards']} 枚、文の形 {total} 種類（変換済みカードに同じ形あり: {cov}）", ""]
    if sv["keywords"]:
        lines.append("キーワード能力: " + "、".join(f"{k} {len(v)}" for k, v in
                                                 sorted(sv["keywords"].items(), key=lambda kv: -len(kv[1]))) + "\n")
    lines += ["| 枚数 | 済 | 例（カードID: 原文） |", "|---:|:-:|---|"]
    for _, g in items[:top]:
        cid, ex = next(iter(g["cards"].items()))
        lines.append(f"| {len(g['cards'])} | {'済' if g['covered'] else ''} | {cid}: {ex[:70]} |")
    if len(items) > top:
        lines.append(f"\n（ほか {len(items) - top} 種類）")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw", nargs="*", default=[str(DATA / "cards" / "raw")])
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--uncovered", action="store_true", help="変換済みカードに無い形だけ")
    a = ap.parse_args(argv)
    sys.stdout.write(render(survey(load_rows(a.raw)), a.top, a.uncovered))


if __name__ == "__main__":
    main()
