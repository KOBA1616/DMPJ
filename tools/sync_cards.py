"""台帳（data/cards/catalog/sets.json）の ID 一覧に沿って、カード詳細ページを弾ごとに取得する。

    python tools/sync_cards.py --products 26ex4,22rp1 --max-minutes 100
    python tools/sync_cards.py --all --max-minutes 300          # 台帳で listed かつ未取得の商品を順に

- 取得済みの行は data/cards/raw/by_product/<商品の値>.jsonl にあり、2回目以降はその ID を飛ばす（途中で止まっても続きから）。
- 行の id は正規化した ID（小文字）、official_id は公式のままの ID。
- 台帳の fetched に取得済みの枚数を書く。fetched == len(ids) で完了。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import catalog_sets as cs  # noqa: E402
import fetch_cards as fc  # noqa: E402
from dmsim.cardid import normalize_id  # noqa: E402

MAX_RETRIES = 3              # 1枚あたりの失敗がこの回数に達したら飛ばす（台帳の errors に残る）
MAX_CONSECUTIVE_FAILS = 5
OUT = ROOT / "data" / "cards" / "raw" / "by_product"


def sync_product(led: dict, value: str, interval: float, deadline: float | None) -> bool:
    p = led["products"][value]
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / f"{value}.jsonl"
    have = {json.loads(x)["official_id"] for x in f.read_text(encoding="utf-8").splitlines() if x.strip()} if f.exists() else set()
    last = [0.0]
    fails = 0
    with f.open("a", encoding="utf-8") as out:
        for oid in p["ids"]:
            if oid in have or p.get("errors", {}).get(oid, 0) >= MAX_RETRIES:
                continue
            if deadline and time.monotonic() > deadline:
                break
            try:
                row = fc.parse(oid, fc.fetch(oid, interval, last))
            except Exception as e:
                print(f"{oid}: {e}", file=sys.stderr)
                errs = p.setdefault("errors", {})
                errs[oid] = errs.get(oid, 0) + 1
                fails += 1
                if fails >= MAX_CONSECUTIVE_FAILS:       # 弾かれている／サイト不調 → 今回は止める（再実行で続きから）
                    print("連続失敗が多いので中断", file=sys.stderr)
                    break
                continue
            fails = 0
            p.get("errors", {}).pop(oid, None)
            row.update(official_id=oid, id=normalize_id(oid), product=value)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            have.add(oid)
    p["fetched"] = len(have)
    cs.save(led)
    return len(have) >= len(p["ids"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--products")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--max-minutes", type=float, default=0)
    ap.add_argument("--interval", type=float, default=3.0)
    a = ap.parse_args(argv)
    if a.interval < 2:
        ap.error("--interval は 2 秒以上")
    led = cs.load()
    todo = a.products.split(",") if a.products else \
        [v for v, p in led["products"].items() if p.get("listed") and p.get("fetched", 0) < len(p["ids"])] if a.all else []
    deadline = time.monotonic() + a.max_minutes * 60 if a.max_minutes else None
    for v in todo:
        if deadline and time.monotonic() > deadline:
            print("時間切れ。再実行で続きから進む", file=sys.stderr)
            break
        done = sync_product(led, v, a.interval, deadline)
        p = led["products"][v]
        print(f"{v}\t{p.get('fetched', 0)}/{len(p['ids'])}\t{'完了' if done else '途中'}\t{p['name']}")


if __name__ == "__main__":
    main()
