"""カードIDの正規化。公式カード詳細ページの ID（例: dmrp01-001, dm22ex2-021, dmrp03-s03）をカードの正本の名前にする。

表記ゆれ（弾の表記 "DMRP1" "DMRP-01" "DM22-EX2"、カード番号 "1" "001" "S3"）を同じ ID にそろえる:
  normalize_id("DMRP1-5")      -> "dmrp01-005"
  normalize_id("DMRP-03 S3")   -> "dmrp03-s03"
  normalize_id("DM22-EX2 21")  -> "dm22ex2-021"
  set_code("DMRP1")            -> "dmrp01"
弾の表記: 英字+数字だけ（DM-06, DMRP1）は数字を2桁にする。途中に英字が入るもの（DM22-EX2, DMR16G）はそのまま。
カード番号: 数字は3桁、先頭に英字が付くもの（S3, W2）は 英字+2桁（足りない桁だけ 0 で埋める。CHO005 は CHO005 のまま）。
数字の後ろにも英字が付く番号（SEC001CHO, 001X, 01B）は整形せず、小文字にして公式のまま使う。
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote
from .store import REPO

_SET_SIMPLE = re.compile(r"^([a-z]+)(\d+)$")
_NUM = re.compile(r"^([a-z]*)(\d+)$")
_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")      # 小文字英数字を - でつないだもの（dm22rp2x-045、promoy21-sp3d01、24-s010 など公式IDの形はさまざま）


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
        return n        # SEC001CHO, 001X, m001STAR のように末尾にも文字がある番号は、公式のまま（小文字）で使う
    letters, digits = m.groups()
    return f"{letters}{digits.zfill(2)}" if letters else digits.zfill(3)   # 桁数が足りない時だけ 0 で埋める（CHO005 は CHO005 のまま）


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


def canonical_id(official: str) -> str:
    """台帳の公式IDを正本のIDにする。小文字にするだけ（整形しない）。
    normalize_id は人が打つ表記ゆれ（DMRP1-5 など）を吸収するための整形で、OR01 と OR1 のように公式で別物のIDを同じにしてしまうため、
    台帳のIDには使わない。全台帳IDで衝突しないことはテストで保証する（tests/test_ledger_ids.py）。"""
    return official.strip().lower()


LEDGER_IDS = REPO / "data" / "cards" / "ledger_ids.txt"


@lru_cache(maxsize=1)
def ledger_ids() -> dict[str, str]:
    """公式サイトの台帳にある全ID（data/cards/ledger_ids.txt: 商品<TAB>ID）。小文字 → 公式のID。"""
    out = {}
    for line in LEDGER_IDS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out[line.split("\t")[1].lower()] = line.split("\t")[1]
    return out


def resolve_id(s: str) -> str:
    """人が打ったIDを公式のIDにする。台帳にそのままあればそれ（大文字小文字は問わない）、なければ normalize_id で整形する。"""
    known = ledger_ids()
    return known.get(s.strip().lower()) or known.get(normalize_id(s)) or normalize_id(s)


DETAIL_URL = "https://dm.takaratomy.co.jp/card/detail/?id={id}"


def detail_url(official: str) -> str:
    """カード詳細ページのURL。IDに + や $ が含まれるものがある（+ はそのままだと空白になる）ので、パーセントエンコードする。"""
    return DETAIL_URL.format(id=quote(official, safe="-"))


def cache_name(official: str) -> str:
    """HTMLキャッシュのファイル名（ID中の記号をパーセントエンコード）。"""
    return quote(official, safe="-") + ".html"


def is_official_id(s: str) -> bool:
    return bool(_ID.match(s))


def pack_ids(set_: str, count: int, first: int = 1) -> list[str]:
    """弾 1 つ分の通常カード番号の ID（例: pack_ids("DMRP1", 3) -> dmrp01-001..003）。"""
    sc = set_code(set_)
    return [f"{sc}-{n:03d}" for n in range(first, first + count)]
