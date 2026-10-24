"""公式サイトのカード詳細ページからカードテキストを取得する（個人利用・ローカル実行用）。

    python tools/fetch_cards.py dm01-001 dm01-027 ... > data/cards/raw/official_YYYYMMDD.jsonl
    python tools/fetch_cards.py --ids-file ids.txt --out data/cards/raw/official_YYYYMMDD.jsonl

- サーバーに負担をかけないよう、取得は1件ずつ・既定で3秒以上の間隔を空ける（--interval）。
- 取得した HTML は .cache/official/<id>.html に保存し、2回目以降はネットワークに出ない。
- クラウド環境からは 403 になることがある。その場合は手元のPCで実行する。
- ページの表は「カードの種類」「文明」などの見出しと値が並ぶ形なので、見出しの語で値を拾う。
  ページの構造が変わったら LABELS を直す。拾えなかった項目は空文字のまま出力し、標準エラーに警告を出す。
- 検証: 手元で1枚だけ取り、`--check .cache/official/<id>.html` で解析結果を確認する。
- ツインパクト等で「カードの種類」の表が複数ある場合は faces に面ごとの値を入れる。
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
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
EXTRA_LABELS = {"flavor": "フレーバー", "illustrator": "イラストレーター"}   # 変換には使わないが、表の区切り・自己点検用


class _Cells(HTMLParser):
    """th/td と見出し要素のテキストを順に集める。<br> は改行にする。"""

    def __init__(self):
        super().__init__()
        self.cells: list[str] = []
        self.title = ""
        self.h3s: list[str] = []
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
            text = re.sub(r"[ \t\r\f\v]+", " ", "".join(self._buf)).strip()
            if tag == "h3":
                self.h3s.append(text)   # カード名。表のセルの並びには混ぜない
            else:
                self.cells.append(text)
            self._buf = None
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._buf is not None:
            self._buf.append(data)
        if self._in_title:
            self.title += data


def _clean_name(h3: str) -> tuple[str, str]:
    """「ヘル・スラッシュ(DM6 57/110)」→ (カード名, 収録番号)。括弧が無ければ番号は空。"""
    m = re.match(r"^(.*?)\s*[(（]([^()（）]*\d+/\d+[^()（）]*)[)）]\s*$", h3)
    return (m.group(1).strip(), m.group(2).strip()) if m else (h3.strip(), "")


def _segment(cells: list[str]) -> dict:
    """見出し語の次のセルを値として拾う。次のセルが別の見出し語なら値は空（パワー無しなど）。"""
    out = {}
    labels = set(LABELS.values()) | set(EXTRA_LABELS.values())
    for key, label in {**LABELS, **EXTRA_LABELS}.items():
        out[key] = ""
        for i, c in enumerate(cells[:-1]):
            if c == label:
                v = html.unescape(cells[i + 1]).strip()
                out[key] = "" if v in labels else v
                break
    out["text"] = "\n".join(s.strip() for s in out["text"].splitlines() if s.strip())
    return out


def parse(card_id: str, page: str) -> dict:
    """1ページ分を dict にする。ツインパクトなど「カードの種類」が複数回出るページは faces に面ごとに入れる。"""
    p = _Cells()
    p.feed(page)
    cells = p.cells
    names = [_clean_name(h) for h in p.h3s]
    starts = [i for i, c in enumerate(cells) if c == LABELS["card_type"]]
    # 面ごとの区切り: 「カードの種類」の位置（面が1つなら全体を1区切りにする）
    if len(starts) > 1:
        bounds = [(starts[k], starts[k + 1] if k + 1 < len(starts) else len(cells)) for k in range(len(starts))]
        segs = [_segment(cells[a:b]) for a, b in bounds]
    else:
        segs = [_segment(cells)]
    title = p.title.split("|")[0].strip()
    out = {"id": card_id, "name": names[0][0] if names else title, "set_no": names[0][1] if names else ""}
    out.update(segs[0])
    if len(segs) > 1:
        out["faces"] = [{"name": names[k][0] if k < len(names) else "", **segs[k]} for k in range(len(segs))]
    return out


def missing_fields(row: dict) -> list[str]:
    """取れていないはずの項目（自己点検用）。パワー・種族・マナは無いカードもあるので呪文以外のパワーだけ見る。"""
    need = ["name", "card_type", "civilization", "cost", "text"]
    if "クリーチャー" in row.get("card_type", ""):
        need.append("power")
    return [k for k in need if not row.get(k)]


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
    ap.add_argument("--check", metavar="HTML", help="保存済みHTMLを解析して結果と取れなかった項目を表示する（通信しない）")
    ap.add_argument("--ids-file")
    ap.add_argument("--out", help="jsonl の出力先（省略時は標準出力）")
    ap.add_argument("--interval", type=float, default=3.0, help="リクエストの最小間隔（秒、2未満は不可）")
    a = ap.parse_args(argv)
    if a.check:
        row = parse(Path(a.check).stem, Path(a.check).read_text(encoding="utf-8"))
        print(json.dumps(row, ensure_ascii=False, indent=1))
        print("取れていない項目:", missing_fields(row) or "なし", file=sys.stderr)
        return
    if a.interval < 2:
        ap.error("--interval は 2 秒以上にする")
    ids = list(a.ids)
    if a.ids_file:
        ids += [s.strip() for s in Path(a.ids_file).read_text(encoding="utf-8").splitlines()
                if s.strip() and not s.startswith("#")]
    out = open(a.out, "w", encoding="utf-8") if a.out else sys.stdout
    last = [0.0]
    failed, suspicious = [], []
    for cid in ids:
        try:
            row = parse(cid, fetch(cid, a.interval, last))
        except urllib.error.HTTPError as e:
            hint = "（403: このネットワークからは拒否されている。手元のPCで実行する）" if e.code == 403 else ""
            print(f"{cid}: HTTP {e.code}{hint}", file=sys.stderr)
            failed.append(cid)
            continue
        except Exception as e:   # 1件の失敗で止めない
            print(f"{cid}: {e}", file=sys.stderr)
            failed.append(cid)
            continue
        miss = missing_fields(row)
        if miss:
            print(f"{cid}: 取れていない項目 {miss}（ページ構造の変更？ 確認: python tools/fetch_cards.py --check "
                  f"{CACHE / (cid + '.html')}）", file=sys.stderr)
            suspicious.append(cid)
        out.write(json.dumps(row, ensure_ascii=False) + "\n")
        out.flush()
    if a.out:
        out.close()
    print(f"取得 {len(ids) - len(failed)}/{len(ids)} 件、要確認 {len(suspicious)} 件、失敗 {len(failed)} 件", file=sys.stderr)
    if failed:
        print("失敗したID: " + " ".join(failed), file=sys.stderr)


if __name__ == "__main__":
    main()
