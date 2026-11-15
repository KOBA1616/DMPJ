"""同名カードの正規化: 同名は同じカード。本文・ID は最新の収録版を採用し、古い ID は別名として控える。

収録の新旧は data/cards/catalog/product_dates.txt（公式商品一覧の発売年月）で決める。
表記揺れ（かっこ内の注釈、空白、色の順、進化の括弧、パワーの「+」）と、多色カードの旧注釈
（「マナゾーンに置く時、このカードはタップして置く」）は normalize_text / normalize_meta で吸収する。
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from ..base.store import REPO

DATA = REPO / "data" / "cards"
_OLD_MULTI = re.compile(r"(?:このカードを)?マナゾーンに置く(?:時|場合)[、,]?\s*(?:この|その)?カードはタップして置く[。.]?")
_PAREN = re.compile(r"[（(][^）)]*[）)]")
_PRINTING = re.compile(r"\s*[（(][^（）()]*\d+\s*/\s*[^（）()]*[）)]\s*$")


def name_key(n: str) -> str:
    """同名判定用のカード名。名前の末尾に付いた収録番号（「(DM26EX4 ㊙6/㊙25)」「(DMR16真 44/54)」）を除く。
    シークレット版などは原文の名前に収録番号が付くが、同じカードなので最新版の別名として扱う。"""
    return _PRINTING.sub("", n)


def normalize_text(t: str) -> str:
    """表記揺れを吸収した本文（比較用）。注釈のカッコ内、空白・中黒、多色の旧注釈を除く。"""
    t = unicodedata.normalize("NFKC", t)
    t = _OLD_MULTI.sub("", t)
    t = _PAREN.sub("", t).replace("とき", "時")
    return re.sub(r"[\s　・･]", "", t)


def normalize_meta(card: dict) -> tuple:
    """型・文明・コスト・パワーの表記揺れを吸収した比較用の組。"""
    ctype = re.sub(r"[（(][^）)]*[）)]", "", unicodedata.normalize("NFKC", card.get("card_type", "")))
    civs = tuple(sorted(c for c in re.split(r"[/／]", card.get("civilization", "")) if c))
    power = str(card.get("power", "")).rstrip("+＋")
    return ctype, civs, str(card.get("cost", "")), power


@lru_cache(maxsize=1)
def product_rank() -> dict[str, int]:
    """商品コード → 新しさの順位（小さいほど新しい）。発売年月（product_dates.txt）の降順。
    発売日を持たない商品（プロモ、アート、コロコロ付録など）は最も古い扱いで、最新版には選ばれにくい。"""
    dates: dict[str, str] = {}
    for line in (DATA / "catalog" / "product_dates.txt").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            code, ym, *_ = line.split()
            dates[code] = ym
    order = sorted(dates, key=lambda c: (dates[c], c), reverse=True)
    return {c: i for i, c in enumerate(order)}


@lru_cache(maxsize=1)
def canonical_index() -> dict[str, dict]:
    """カード名 → {"id": 最新版の ID, "text": 最新の本文, "aliases": 古い ID, "text_variants": 正規化後の本文の種類数}。"""
    rank = product_rank()
    best: dict[str, tuple] = {}
    olds: dict[str, list[str]] = {}
    variants: dict[str, set] = {}
    for f in sorted((DATA / "raw" / "by_product").glob("*.jsonl")):
        prod = f.stem
        r = rank.get(prod, len(rank))
        for line in f.read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            n = d.get("name")
            if not n:
                continue
            n = name_key(n)
            variants.setdefault(n, set()).add(normalize_text(d["text"]))
            key = (r, d["id"])
            if n not in best or key < best[n][0]:
                if n in best:
                    olds.setdefault(n, []).append(best[n][1]["id"])
                best[n] = (key, d)
            else:
                olds.setdefault(n, []).append(d["id"])
    return {n: {"id": d["id"], "text": d["text"], "product": d.get("product"), "aliases": sorted(set(olds.get(n, []))),
                "text_variants": len(variants[n])} for n, (_, d) in best.items()}


@lru_cache(maxsize=1)
def alias_to_canonical() -> dict[str, str]:
    """どの ID（古い版を含む）からでも、最新の ID を引く。"""
    out = {}
    for v in canonical_index().values():
        out[v["id"]] = v["id"]
        for a in v["aliases"]:
            out[a] = v["id"]
    return out
