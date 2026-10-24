"""公式カード検索ページの「商品名」の選択肢（弾の一覧）を取得して保存する。

    python tools/discover_sets.py --out .cache/official/_search.html

ページの HTML をそのまま保存する（構造が変わっても後から解析し直せるように）。解析は tools/build_sets.py。
"""
from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

URL = "https://dm.takaratomy.co.jp/card/"
UA = "dmpj-card-fetch/0.1 (personal use)"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=".cache/official/_search.html")
    a = ap.parse_args(argv)
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", errors="replace")
    p = Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(page, encoding="utf-8")
    print(f"{len(page)} bytes -> {p}")
    # 検索の仕組みを調べるための補助ファイル（検索ページが読み込むスクリプト）
    for name in ("search.js", "ajax_pop.js"):
        req = urllib.request.Request(f"https://dm.takaratomy.co.jp/common/js/{name}", headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                (p.parent / f"_{name}").write_text(r.read().decode("utf-8", errors="replace"), encoding="utf-8")
        except Exception as e:   # 取れなくても続ける
            print(name, e)


if __name__ == "__main__":
    main()
