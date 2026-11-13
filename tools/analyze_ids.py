"""台帳の全カードID（data/cards/ledger_ids.txt）の型を数えて docs/card-ids.md に書く。

    python tools/analyze_ids.py            # docs/card-ids.md を更新
    python tools/analyze_ids.py --check    # 古ければ失敗（CI・テスト用）

型の書き方: 数字→9、大文字→A、小文字→a（例: dm26ex4-CHO005 の番号部 CHO005 → AAA999）。
"""
from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dmsim.base.cardid import normalize_id  # noqa: E402

OUT = ROOT / "docs" / "card-ids.md"


def shape(s: str) -> str:
    return re.sub(r"[a-z]", "a", re.sub(r"[A-Z]", "A", re.sub(r"\d", "9", s)))


def load() -> list[tuple[str, str]]:
    path = ROOT / "data" / "cards" / "ledger_ids.txt"
    return [tuple(l.split("\t")) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def table(counter: collections.Counter, ex: dict, top: int = 40) -> list[str]:
    rows = ["| 型 | 件数 | 例 |", "|---|---:|---|"]
    for k, n in counter.most_common(top):
        rows.append(f"| `{k}` | {n} | `{ex[k]}` |")
    if len(counter) > top:
        rows.append(f"| その他 {len(counter) - top} 型 | {sum(counter.values()) - sum(n for _, n in counter.most_common(top))} | |")
    return rows


def build() -> str:
    rows = load()
    ids = [i for _, i in rows]
    prefix, number = collections.Counter(), collections.Counter()
    pex, nex = {}, {}
    for _, i in rows:
        a, b = i.split("-", 1)
        prefix[shape(a)] += 1
        pex.setdefault(shape(a), i)
        number[shape(b)] += 1
        nex.setdefault(shape(b), i)
    special = collections.Counter(c for i in ids if True for c in i if not c.isalnum() and c != "-")
    multi = [i for i in ids if i.count("-") != 1]
    upper_prefix = sum(1 for i in ids if i.split("-")[0] != i.split("-")[0].lower())
    needs_quote = [i for i in ids if quote(i, safe="-") != i]
    by_norm = collections.defaultdict(list)
    for i in ids:
        by_norm[normalize_id(i)].append(i)
    collide = [v for v in by_norm.values() if len(v) > 1]
    lower = collections.Counter(i.lower() for i in ids)
    out = ["# カードIDの型（台帳 全件）", "",
           "`python tools/analyze_ids.py` が `data/cards/ledger_ids.txt`（商品とIDの一覧。台帳 `sets.json` の写し）から生成する。手で編集しない。", "",
           f"- 総数 **{len(ids)}** 枚、商品 {len({p for p, _ in rows})} 件。大文字小文字を無視しても重複なし: **{'はい' if max(lower.values()) == 1 else 'いいえ'}**",
           f"- 形は `商品部-番号部`。ハイフンが2つ以上のもの: {len(multi)} 枚（例 `{multi[0] if multi else '-'}`）。最初のハイフンで商品部と番号部に分ける",
           f"- 商品部に大文字が混じるもの: {upper_prefix} 枚（全件小文字）。番号部は大文字・小文字が混在する",
           f"- 英数字とハイフン以外の記号: {dict(special) or 'なし'}。URL にそのまま入れると壊れるもの（`+` は空白になる）: {len(needs_quote)} 枚 → `detail_url` でパーセントエンコード",
           f"- `normalize_id`（人が打つ表記ゆれを吸収する整形）で衝突するもの: {len(collide)} 組 {collide[:4]} → 台帳のIDには使わず、`canonical_id`（小文字にするだけ）を正本にする",
           "", "## 商品部の型", "", *table(prefix, pex), "", "## 番号部の型", "", *table(number, nex), "",
           "## 取り扱い", "",
           "- 取得URL: `detail_url(公式ID)`（公式のIDそのまま。大文字小文字は台帳のまま）。HTMLキャッシュ名も同じエンコード。",
           "- カードの正本ID: `canonical_id(公式ID)`。台帳の全IDで衝突しないことを `tests/test_ledger_ids.py` が保証する。",
           "- 人が打ったID: `resolve_id`（台帳にあればその公式ID、なければ `normalize_id` で整形）。",
           ""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    text = build()
    if a.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            sys.exit("docs/card-ids.md が古い: python tools/analyze_ids.py を実行")
        return
    OUT.write_text(text, encoding="utf-8")
    print(f"{OUT} を更新")


if __name__ == "__main__":
    main()
