"""チャットの AI（エージェント）に、API なしでカード変換をさせるための補助。AI は git を読めて、コマンドを実行できる前提。

    python tools/agent_convert.py system               # 変換の指示文（語彙表・スキーマ・変換例つき）。1回読めばよい
    python tools/agent_convert.py next 5 [--order newest]   # 次に変換するカード5枚の依頼文（ルールで片づく分は先に登録して除く）
    python tools/agent_convert.py submit answer.yaml   # AI の答えを検査して converted.yaml に登録（合格分だけ。不合格は理由を表示）
    python tools/agent_convert.py reopen <gap名>...    # 語彙を足したあと、その不足だけで rejects に入っていたカードを外して再変換できるようにする

プロンプトは docs/prompts/convert-by-agent.md。参照先は実ファイルなので、貼り付けは要らない。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import convert_cards as cc  # noqa: E402
import rule_convert  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402
from dmsim.cards.defs import DATA, load_tables  # noqa: E402

RAW = DATA / "cards" / "raw"
OUT, REJ = cardstore.converted_path(DATA), RAW / "rejects.jsonl"


def todo_rows(order: str) -> list[dict]:
    rows = cc.load_rows([str(RAW)])
    done = cc.known_ids(OUT)
    failed = {r["id"] for r in cc.read_jsonl(REJ)}
    key = {"id": lambda r: r["id"], "short": lambda r: len(r.get("text", "")), "newest": cc.newest_key()}[order]
    return sorted((r for r in rows if r["id"] not in done and r["id"] not in failed), key=key)


def cmd_next(n: int, order: str):
    tables = load_tables()
    cc.run_rules(cc.load_rows([str(RAW)]), tables, OUT, REJ)      # ルールだけで済む分は先に登録（モデル不要）
    pick = []
    for r in todo_rows(order):
        if cc.precheck(r) or rule_convert.convert(r) is not None:
            continue
        part = rule_convert.split(r)
        pick.append({**r, "text": part[1], "known_keywords": part[0]} if part else r)
        if len(pick) >= n:
            break
    if not pick:
        print("変換するカードはありません", file=sys.stderr)
        return 1
    print(cc.pack_prompt(pick))
    return 0


def summon_lint(card: dict, row: dict) -> list[str]:
    """play_free / reason: summon は「召喚する・唱える」専用。原文にその語が無ければ警告する（出す・置くは move to bz reason: put）。"""
    txt = row.get("text") or row.get("ability") or json.dumps(row, ensure_ascii=False)
    s = json.dumps(card.get("abilities") or [], ensure_ascii=False)
    out = []
    if ("play_free" in s or '"reason": "summon"' in s) and not re.search(r"召喚|唱え|実行|ジェネレート|ニンジャ・ストライク|ストライク|G・ゼロ|革命", txt):
        out.append("play_free/reason: summon は召喚・唱えるの意味。原文に召喚・唱えるが無い。出す・置くなら move to bz reason: put")
    return out


def cmd_submit(path: str) -> int:
    text = Path(path).read_text(encoding="utf-8")
    m = cc.re.search(r"```ya?ml\s*\n(.*?)```", text, cc.re.S)
    raw = yaml.safe_load(m.group(1) if m else text)
    items = raw.get("cards") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        print("cards: のリストになっていない", file=sys.stderr)
        return 2
    rows = {r["id"]: r for r in cc.load_rows([str(RAW)])}
    tables = load_tables()
    cards = cardstore.read(OUT)
    have = {c["id"] for c in cards}
    rejects = {x["id"]: x for x in cc.read_jsonl(REJ)}
    bad = 0
    for it in items:
        cid = it.get("id") if isinstance(it, dict) else None
        r = rows.get(cid)
        if r is None:
            print(f"✗ {cid}: 取得済みの原文に無いID", file=sys.stderr)
            bad += 1
            continue
        if cid in have:
            print(f"- {cid}: 変換済みなので飛ばす")
            continue
        pre = cc.precheck(r)
        if pre:
            print(f"- {cid}: {pre['reason']}（{pre['error']}）。飛ばす")
            continue
        try:
            part = rule_convert.split(r)
            if part:
                cc.merge_split(it, r, part)
            card = cc.validate(it, r, tables)
            for w in summon_lint(card, r):
                print(f"! {cid} {r.get('name', '')}: {w}")
            vr = cc.vocab_reject(card, r)
            if vr:      # 語彙が足りないカードは登録しない（rejects に vocab として残し、足りない語彙は report_gaps に出る）
                rejects[cid] = vr
                print(f"- {cid} {r.get('name', '')}: {vr['error']}（登録しない。語彙が足りてから変換し直す）")
                continue
            cards.append(card)
            have.add(cid)
            rejects.pop(cid, None)      # 語彙が足りて登録できたら rejects から外す
            print(f"✓ {cid} {r.get('name', '')}")
        except (cc.DefError, KeyError, TypeError) as e:
            print(f"✗ {cid} {r.get('name', '')}: {e}", file=sys.stderr)
            bad += 1
    cardstore.write(OUT, cards, cc.CONVERTED_HEADER)
    cc.write_jsonl(REJ, list(rejects.values()))
    return 1 if bad else 0


def cmd_reopen(gaps: list[str]) -> int:
    """語彙を足したあと、その不足（gaps 名）だけで rejects に入っていたカードを rejects から外す（`next` がもう一度出す）。
    他の不足も付いているカードは外さない。"""
    rejects = cc.read_jsonl(REJ)
    want = set(gaps)
    keep, opened = [], []
    for r in rejects:
        g = r.get("gaps") or []
        if isinstance(g, str):      # 古い記録は gaps が文字列（リストの repr）
            import ast
            try:
                g = ast.literal_eval(g)
            except (ValueError, SyntaxError):
                g = [g]
        g = {str(x) for x in g}
        if r.get("reason") == "vocab" and g and g <= want:
            opened.append(r["id"])
        else:
            keep.append(r)
    cc.write_jsonl(REJ, keep)
    print(f"{len(opened)}枚を rejects から外した（next で再変換できる）: {' '.join(opened)}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("system")
    n = sub.add_parser("next")
    n.add_argument("count", type=int, nargs="?", default=5)
    n.add_argument("--order", choices=["id", "short", "newest"], default="id")
    s = sub.add_parser("submit")
    s.add_argument("file")
    ro = sub.add_parser("reopen", help="語彙を足した不足（gaps 名）の rejects を外して再変換できるようにする")
    ro.add_argument("gaps", nargs="+")
    a = ap.parse_args(argv)
    if a.cmd == "system":
        print(cc.system_prompt())
        return 0
    if a.cmd == "next":
        return cmd_next(a.count, a.order)
    if a.cmd == "reopen":
        return cmd_reopen(a.gaps)
    return cmd_submit(a.file)


if __name__ == "__main__":
    sys.exit(main())
