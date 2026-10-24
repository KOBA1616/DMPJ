"""公式サイトのカード詳細ページからカードテキストを取得する（個人利用・ローカル実行用）。

    python tools/fetch_cards.py dm01-001 dm01-027 ... > data/cards/raw/official_YYYYMMDD.jsonl
    python tools/fetch_cards.py --ids-file ids.txt --out data/cards/raw/official_YYYYMMDD.jsonl

- サーバーに負担をかけないよう、取得は1件ずつ・既定で3秒以上の間隔を空ける（--interval）。
- 取得した HTML は .cache/official/<id>.html に保存し、2回目以降はネットワークに出ない。
- クラウド環境からは 403 になることがある。その場合は手元のPCで実行する。
- ページの表は「カードの種類」「文明」などの見出しと値が並ぶ形なので、見出しの語で値を拾う。
  ページの構造が変わったら LABELS を直す。拾えなかった項目は空文字のまま出力する。
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

URL = "https://dm.takaratomy.co.jp/card/detail/?id={id}"
CACHE = Path(__file__).resolve().parent.parent / ".cache" / "official"
UA = "dmpj-card-fetch/0.1 (personal use; 1 request per few seconds)"
LABELS = {   # 出力のキー: ページの見出し
    "card_type": "カードの種類", "civilization": "文明", "cost": "コスト", "power": "パワー",
    "race": "種族", "mana": "マナ", "rarity": "レアリティ", "text": "特殊能力",
}


class _Cells(HTMLParser):
    """th/td と見出し要素のテキストを順に集める。<br> は改行にする。"""

    def __init__(self):
        super().__init__()
        self.cells: list[str] = []
        self.title = ""
        self._buf: list[str] | None = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ("th", "td", "h3"):
            self._buf = []
        elif tag == "br" and self._buf is not None:
            self._buf.append("\n")
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in ("th", "td", "h3") and self._buf is not None:
            self.cells.append(re.sub(r"[ \t\r\f\v]+", " ", "".join(self._buf)).strip())
            self._buf = None
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._buf is not None:
            self._buf.append(data)
        if self._in_title:
            self.title += data


def parse(card_id: str, page: str) -> dict:
    p = _Cells()
    p.feed(page)
    out = {"id": card_id, "name": ""}
    cells = p.cells
    for key, label in LABELS.items():
        out[key] = ""
        for i, c in enumerate(cells[:-1]):
            if c == label:
                out[key] = html.unescape(cells[i + 1]).strip()
                break
    # カード名は h3 か <title> の先頭（「カード名 | ...」の形）
    name = next((c for c in cells if c and c not in LABELS.values()), "")
    out["name"] = (p.title.split("|")[0].strip() or name)
    out["text"] = "\n".join(s.strip() for s in out["text"].splitlines() if s.strip())
    return out


def fetch(card_id: str, interval: float, last: list[float]) -> str:
    f = CACHE / f"{card_id}.html"
    if f.exists():
        return f.read_text(encoding="utf-8")
    wait = last[0] + interval - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(URL.format(id=card_id), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", errors="replace")
    last[0] = time.monotonic()
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(page, encoding="utf-8")
    return page


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--ids-file")
    ap.add_argument("--out", help="jsonl の出力先（省略時は標準出力）")
    ap.add_argument("--interval", type=float, default=3.0, help="リクエストの最小間隔（秒、2未満は不可）")
    a = ap.parse_args(argv)
    if a.interval < 2:
        ap.error("--interval は 2 秒以上にする")
    ids = list(a.ids)
    if a.ids_file:
        ids += [s.strip() for s in Path(a.ids_file).read_text(encoding="utf-8").splitlines()
                if s.strip() and not s.startswith("#")]
    out = open(a.out, "w", encoding="utf-8") if a.out else sys.stdout
    last = [0.0]
    for cid in ids:
        try:
            row = parse(cid, fetch(cid, a.interval, last))
        except Exception as e:   # 1件の失敗で止めない
            print(f"{cid}: {e}", file=sys.stderr)
            continue
        if not row["text"] and not row["card_type"]:
            print(f"{cid}: 見出しが見つからない（ページ構造の変更？ キャッシュ: {CACHE / (cid + '.html')}）",
                  file=sys.stderr)
        out.write(json.dumps(row, ensure_ascii=False) + "\n")
        out.flush()
    if a.out:
        out.close()


if __name__ == "__main__":
    main()
