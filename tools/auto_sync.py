"""定期実行用の自動取得。台帳を見て「次にやること」を自分で決め、時間いっぱい進める。

    python tools/auto_sync.py --max-minutes 300

順序: 1) 商品一覧を更新（新商品は台帳に listed=false で加わる） 2) 未確認の商品のカードID一覧 3) 新しい弾から順にカード詳細。
- 商品一覧は公式の並び（新しい弾が先）のまま台帳に入るので、その順で処理する。
- 失敗は台帳の errors に数え、3回で飛ばす。連続で失敗したら今回は打ち切る（403/429 などで無理に叩かない）。
- 全部済んだら data/cards/catalog/status.json に complete=true と書く。毎回 status.json に進捗を書く。
- 間隔は 3 秒以上。止めるには tools/auto_sync.yaml の enabled を false にする。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import catalog_sets as cs  # noqa: E402
import sync_cards as sc  # noqa: E402

STATUS = cs.LEDGER.parent / "status.json"


def summary(led: dict) -> dict:
    ps = led["products"]
    listed = [p for p in ps.values() if p.get("listed")]
    return dict(
        updated=datetime.now(timezone.utc).strftime("%FT%TZ"),
        products=len(ps), products_listed=len(listed),
        cards_total=sum(len(p["ids"]) for p in listed),
        cards_fetched=sum(p.get("fetched", 0) for p in ps.values()),
        products_done=sum(1 for p in listed if p.get("fetched", 0) >= len(p["ids"])),
        cards_gave_up=sum(sum(1 for n in p.get("errors", {}).values() if n >= sc.MAX_RETRIES) for p in ps.values()),
        complete=bool(ps) and len(listed) == len(ps) and all(p.get("fetched", 0) + sum(1 for n in p.get("errors", {}).values() if n >= sc.MAX_RETRIES) >= len(p["ids"]) for p in listed),
    )


def write_status(led: dict) -> dict:
    s = summary(led)
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(s, ensure_ascii=False), flush=True)
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-minutes", type=float, default=300)
    ap.add_argument("--interval", type=float, default=3.0)
    a = ap.parse_args(argv)
    if a.interval < 2:
        ap.error("--interval は 2 秒以上")
    deadline = time.monotonic() + a.max_minutes * 60
    led = cs.load()
    try:
        cs.list_products(led, a.interval)         # 新商品の検出（既存の ids/listed は保たれる）
    except Exception as e:
        print(f"商品一覧の更新に失敗: {e}", file=sys.stderr)
        if not led["products"]:
            write_status(led)
            return
    for v, p in list(led["products"].items()):
        if time.monotonic() > deadline:
            break
        if p.get("listed"):
            continue
        try:
            cs.list_cards(led, v, a.interval)
        except Exception as e:
            print(f"{v}: {e}", file=sys.stderr)
    for v, p in list(led["products"].items()):
        if time.monotonic() > deadline:
            break
        if p.get("listed") and p.get("fetched", 0) < len(p["ids"]):
            sc.sync_product(led, v, a.interval, deadline)
            q = led["products"][v]
            print(f"{v}\t{q.get('fetched', 0)}/{len(q['ids'])}\t{q['name']}", flush=True)
            write_status(led)
    write_status(led)


if __name__ == "__main__":
    main()
