"""カードIDの正規化。公式カード詳細ページの ID（例: dmrp01-001, dm22ex2-021, dmrp03-s03）をカードの正本の名前にする。

表記ゆれ（弾の表記 "DMRP1" "DMRP-01" "DM22-EX2"、カード番号 "1" "001" "S3"）を同じ ID にそろえる:
  normalize_id("DMRP1-5")      -> "dmrp01-005"
  normalize_id("DMRP-03 S3")   -> "dmrp03-s03"
  normalize_id("DM22-EX2 21")  -> "dm22ex2-021"
  set_code("DMRP1")            -> "dmrp01"
弾の表記: 英字+数字だけ（DM-06, DMRP1）は数字を2桁にする。途中に英字が入るもの（DM22-EX2, DMR16G）はそのまま。
カード番号: 数字は3桁、先頭に英字が付くもの（S3, W2）は 英字+2桁。
"""
from __future__ import annotations

import re

_SET_SIMPLE = re.compile(r"^([a-z]+)(\d+)$")
_NUM = re.compile(r"^([a-z]*)(\d+)$")
_ID = re.compile(r"^[a-z]+\d+[a-z]*\d*-[a-z]?\d+$")


def set_code(s: str) -> str:
    s = re.sub(r"[\s_\-]+", "", s.strip().lower())
    m = _SET_SIMPLE.match(s)
    if m:
        return f"{m.group(1)}{int(m.group(2)):02d}"
    return s


def card_number(n: str) -> str:
    n = re.sub(r"[\s_\-]+", "", n.strip().lower())
    m = _NUM.match(n)
    if not m:
        raise ValueError(f"bad card number: {n!r}")
    letters, digits = m.groups()
    return f"{letters}{int(digits):02d}" if letters else f"{int(digits):03d}"


def normalize_id(s: str) -> str:
    """"DMRP1-5" "DMRP-01 S3" "dm22ex2-021" などを公式の ID に直す。区切りは最後の '-' か空白。"""
    parts = s.split()
    if len(parts) >= 2:
        left, right = " ".join(parts[:-1]), parts[-1]
    elif "-" in s:
        left, right = s.rsplit("-", 1)
    else:
        raise ValueError(f"cannot split card id: {s!r}")
    return f"{set_code(left)}-{card_number(right)}"


def is_official_id(s: str) -> bool:
    return bool(_ID.match(s))


def pack_ids(set_: str, count: int, first: int = 1) -> list[str]:
    """弾 1 つ分の通常カード番号の ID（例: pack_ids("DMRP1", 3) -> dmrp01-001..003）。"""
    sc = set_code(set_)
    return [f"{sc}-{n:03d}" for n in range(first, first + count)]
