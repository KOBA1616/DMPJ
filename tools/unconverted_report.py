"""未変換の札を「なぜ変換できないか」で分類し、型ごとの枚数を多い順に出す（読むだけ。何も書かない）。

    python tools/unconverted_report.py            # 表で出す
    python tools/unconverted_report.py --json     # JSON で出す

対象は approval_stats.targets と同じ（サイキック・GR の種類を除く）。札は名前でまとめる
（dmsim/cards/canonical.py の方針「同名は同じカード」。古い収録の ID は最新版の別名として引ける）。

分類（上から順に当てはめ、最初に当たったもの）:
  同名が変換済み        … 同名の別収録が変換済み。別名で引けるので追加の変換は要らない
  形式外の種類          … convert_cards.OUT_OF_FORMAT（ドラグハート・超次元など）。変換しない
  形式外を本文で参照    … GR召喚・超次元ゾーン・サイキックを本文で使う。オリジナルフォーマットでは働かない
  取得が不完全          … 原文の欠け（precheck の fetch_incomplete、または変換の申告 data_incomplete）
  語彙不足:<語>         … 変換の検査落ち（rejects.jsonl）の不足語彙。1枚に複数あれば先頭の語で数え、全語の枚数も別に出す
  未試行                … まだ変換に掛けていない
"""
from __future__ import annotations

import argparse
import ast
import collections
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import approval_stats as stats  # noqa: E402
import convert_cards as cc  # noqa: E402
from dmsim.cards.cardfiles import card_files  # noqa: E402

OUT_TEXT = re.compile(r"GR召喚|GRクリーチャー|超GR|超次元|サイキック")


def _text(r: dict) -> str:
    return "\n".join([r.get("text") or "", *[f.get("text") or "" for f in r.get("faces") or []]])


def _gaps(rej: dict) -> list[str]:
    g = rej.get("gaps") or []
    if isinstance(g, str):
        try:
            g = ast.literal_eval(g)
        except (ValueError, SyntaxError):
            g = [g]
    return [str(x) for x in g if str(x).strip()]


def run() -> dict:
    tg = {k: v for k, v in stats.targets().items() if not stats.excluded(v.get("card_type"))}
    conv = set()
    for f in card_files():
        for c in (yaml.safe_load(Path(f).read_text(encoding="utf-8")) or {}).get("cards") or []:
            conv.add(c["id"])
    rj = {}
    p = stats.RAW / "rejects.jsonl"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                rj[r["id"]] = r
    conv_names = {v["name"] for k, v in tg.items() if k in conv}
    by_name: dict[str, list[str]] = collections.defaultdict(list)
    for k, v in tg.items():
        by_name[v["name"]].append(k)

    kind_ids, kind_names = collections.Counter(), collections.Counter()
    all_gaps = collections.Counter()
    examples: dict[str, str] = {}
    for name, ids in by_name.items():
        if name in conv_names:
            n_un = sum(1 for k in ids if k not in conv)
            if n_un:
                kind_ids["同名が変換済み"] += n_un
                kind_names["同名が変換済み"] += 0      # 名前としては変換済みなので数えない
            continue
        r = tg[ids[0]]
        gaps = [g for k in ids if k in rj for g in _gaps(rj[k])]
        pre = cc.precheck(r) or {}
        if pre.get("reason") == "out_of_format":
            kind = "形式外の種類"
        elif OUT_TEXT.search(_text(r)):
            kind = "形式外を本文で参照"
        elif pre.get("reason") == "fetch_incomplete" or "data_incomplete" in gaps:
            kind = "取得が不完全"
        elif pre.get("reason") == "no_text":
            kind = "能力文が無い"
        elif gaps:
            kind = "語彙不足:" + gaps[0]
            for g in dict.fromkeys(gaps):
                all_gaps[g] += 1
        elif any(k in rj for k in ids):
            kind = "検査落ち（語彙の申告なし）"
        else:
            kind = "未試行"
        kind_ids[kind] += len(ids)
        kind_names[kind] += 1
        examples.setdefault(kind, f"{ids[0]} {name}")

    n, nn = len(tg), len(by_name)
    conv_ids = sum(1 for k in tg if k in conv)
    covered_ids = sum(len(v) for nm, v in by_name.items() if nm in conv_names)
    return {
        "targets": n, "target_names": nn,
        "converted_ids": conv_ids, "converted_names": len(conv_names),
        "covered_ids_incl_same_name": covered_ids,
        "rate": {"ids": round(conv_ids / n, 4), "names": round(len(conv_names) / nn, 4),
                 "ids_incl_same_name": round(covered_ids / n, 4)},
        "kinds": [{"kind": k, "names": kind_names[k], "ids": kind_ids[k], "example": examples.get(k, "")}
                  for k in sorted(kind_ids, key=lambda k: (-kind_names[k], -kind_ids[k]))],
        "gaps_all": all_gaps.most_common(60),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args(argv)
    out = run()
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    r = out["rate"]
    print(f"対象 {out['targets']} 枚 / 名前 {out['target_names']}")
    print(f"  変換済み: {out['converted_ids']} 枚 ({r['ids']:.1%}) / 名前 {out['converted_names']} ({r['names']:.1%})")
    print(f"  同名の別収録を含めた枚数: {out['covered_ids_incl_same_name']} ({r['ids_incl_same_name']:.1%})")
    print("| 名前 | 枚数 | 型 | 例 |\n|---:|---:|---|---|")
    for k in out["kinds"][: a.top]:
        print(f"| {k['names']} | {k['ids']} | {k['kind']} | {k['example']} |")


if __name__ == "__main__":
    main()
