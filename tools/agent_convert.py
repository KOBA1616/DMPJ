"""チャットの AI（エージェント）に、API なしでカード変換をさせるための補助。AI は git を読めて、コマンドを実行できる前提。

    python tools/agent_convert.py system               # 変換の指示文（語彙表・スキーマ・変換例つき）。1回読めばよい
    python tools/agent_convert.py next 5 [--order newest]   # 次に変換するカード5枚の依頼文（ルールで片づく分は先に登録して除く）
    python tools/agent_convert.py submit answer.yaml   # AI の答えを検査して converted.yaml に登録（合格分だけ。不合格は理由を表示）

プロンプトは docs/prompts/convert-by-agent.md。参照先は実ファイルなので、貼り付けは要らない。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import convert_cards as cc  # noqa: E402
import rule_convert  # noqa: E402
from auto_convert import newest_key  # noqa: E402
from dmsim.defs import DATA, load_tables  # noqa: E402

RAW = DATA / "cards" / "raw"
OUT, REJ = DATA / "cards" / "converted.yaml", RAW / "rejects.jsonl"


def todo_rows(order: str) -> list[dict]:
    rows = cc.load_rows([str(RAW)])
    done = cc.known_ids(OUT)
    failed = {r["id"] for r in cc.read_jsonl(REJ)}
    key = {"id": lambda r: r["id"], "short": lambda r: len(r.get("text", "")), "newest": newest_key()}[order]
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
    doc = (yaml.safe_load(OUT.read_text(encoding="utf-8")) if OUT.exists() else None) or {}
    cards = doc.get("cards") or []
    have = {c["id"] for c in cards}
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
        try:
            part = rule_convert.split(r)
            if part:
                cc.merge_split(it, r, part)
            cards.append(cc.validate(it, r, tables))
            have.add(cid)
            print(f"✓ {cid} {r.get('name', '')}")
        except (cc.DefError, KeyError, TypeError) as e:
            print(f"✗ {cid} {r.get('name', '')}: {e}", file=sys.stderr)
            bad += 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("# convert_cards.py の出力（review: pending）。確認後に real.yaml へ移す。\n"
                   + yaml.safe_dump({"cards": cards}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("system")
    n = sub.add_parser("next")
    n.add_argument("count", type=int, nargs="?", default=5)
    n.add_argument("--order", choices=["id", "short", "newest"], default="id")
    s = sub.add_parser("submit")
    s.add_argument("file")
    a = ap.parse_args(argv)
    if a.cmd == "system":
        print(cc.system_prompt())
        return 0
    if a.cmd == "next":
        return cmd_next(a.count, a.order)
    return cmd_submit(a.file)


if __name__ == "__main__":
    sys.exit(main())
