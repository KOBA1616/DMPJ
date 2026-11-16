"""公式カード検索から、弾（商品）の一覧と、各弾のカードID一覧を取って台帳 data/cards/catalog/sets.json に記録する。

    python tools/catalog_sets.py --list-products          # 商品の一覧だけ（1リクエスト）
    python tools/catalog_sets.py --products 26ex4,22rp1   # 指定した商品のカードID一覧（検索結果を50枚ずつ）
    python tools/catalog_sets.py --all --max-minutes 100  # 台帳で未確認の商品を順に（時間で打ち切り。再実行で続きから）

- 検索は POST /card/（products=商品の値, samename=show, pagenum=ページ）。1ページ50枚、total_count に総数が出る。
- 台帳の各商品: name, code(正規化した弾コード), total(公式の総数), ids(検索結果の順), listed(確認済みか)。
  ids の数が total に達していれば listed=true。ここに残るので、途中で止めても再実行で続きから進む。
- 間隔は 3 秒以上。取得は個人利用の範囲で、GitHub Actions など外部の環境から実行する（クラウド開発環境は届かない）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dmsim.base.cardid import set_code  # noqa: E402

URL = "https://dm.takaratomy.co.jp/card/"
UA = "dmpj-card-fetch/0.1 (personal use; 1 request per few seconds)"
LEDGER = Path(__file__).resolve().parent.parent / "data" / "cards" / "catalog" / "sets.json"
_last = [0.0]


def _wait(interval: float):
    w = _last[0] + interval - time.monotonic()
    if w > 0:
        time.sleep(w)
    _last[0] = time.monotonic()


def http(data: dict | None, interval: float) -> str:
    _wait(interval)
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(URL, data=body, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_products(page: str) -> list[tuple[str, str]]:
    i = page.index('name="products"')
    j = page.index("</select>", i)
    return [(v, n.strip()) for v, n in re.findall(r'<option value="([^"]+)">([^<]*)</option>', page[i:j])]


def parse_list(page: str) -> tuple[int, list[str]]:
    m = re.search(r'id\s*=\s*"total_count">(\d+)<', page)
    total = int(m.group(1)) if m else -1
    ids = []
    for x in re.findall(r"data-href='/card/detail/\?id=([^']+)'", page):
        if x not in ids:
            ids.append(x)
    return total, ids


def product_code(name: str) -> str:
    m = re.match(r"^([A-Za-z]+[A-Za-z0-9]*(?:-[A-Za-z0-9]+)?)(?:\s|$)", name)
    return set_code(m.group(1)) if m else ""


def load() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {"products": {}}


def save(led: dict):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(led, ensure_ascii=False, indent=1), encoding="utf-8")


def list_products(led: dict, interval: float):
    for v, n in parse_products(http(None, interval)):
        p = led["products"].setdefault(v, {})
        p.update(name=n, code=product_code(n))
        p.setdefault("ids", [])
        p.setdefault("listed", False)
    save(led)


def list_cards(led: dict, value: str, interval: float, max_pages: int = 200):
    p = led["products"][value]
    ids: list[str] = []
    total = -1
    for page_no in range(1, max_pages + 1):
        total, got = parse_list(http({"products": value, "samename": "show", "pagenum": page_no}, interval))
        new = [x for x in got if x not in ids]
        ids += new
        if not new or (total >= 0 and len(ids) >= total):
            break
    p.update(ids=ids, total=total, listed=total >= 0 and len(ids) == total)
    if not p["listed"]:
        p["note"] = f"件数が合わない: total={total} ids={len(ids)}"
    else:
        p.pop("note", None)
    save(led)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list-products", action="store_true")
    ap.add_argument("--products", help="商品の値をカンマ区切り（例: 26ex4,22rp1）")
    ap.add_argument("--all", action="store_true", help="台帳で listed でない商品をすべて")
    ap.add_argument("--max-minutes", type=float, default=0, help="この時間で打ち切る（0 は無制限）")
    ap.add_argument("--interval", type=float, default=3.0)
    a = ap.parse_args(argv)
    if a.interval < 2:
        ap.error("--interval は 2 秒以上")
    led = load()
    if a.list_products or not led["products"]:
        list_products(led, a.interval)
    todo = [v for v in (a.products.split(",") if a.products else
                        [v for v, p in led["products"].items() if not p.get("listed")] if a.all else [])]
    t0 = time.monotonic()
    for v in todo:
        if a.max_minutes and (time.monotonic() - t0) / 60 > a.max_minutes:
            print("時間切れ。再実行で続きから進む", file=sys.stderr)
            break
        try:
            list_cards(led, v, a.interval)
        except Exception as e:      # 1商品の失敗で止めない（台帳には listed=false のまま残る）
            print(f"{v}: {e}", file=sys.stderr)
            continue
        p = led["products"][v]
        print(f"{v}\t{p['total']}\t{len(p['ids'])}\t{'ok' if p['listed'] else p.get('note')}\t{p['name']}")


if __name__ == "__main__":
    main()
