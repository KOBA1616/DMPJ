"""台帳の全カードID（公式サイト 23,671 枚）が、正規化・取得URL・キャッシュ名でエラーなく通ることの保証。"""
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import analyze_ids  # noqa: E402
from dmsim.base.cardid import cache_name, canonical_id, detail_url, ledger_ids, normalize_id, resolve_id  # noqa: E402

ROWS = analyze_ids.load()
IDS = [i for _, i in ROWS]


def test_ledger_is_complete_and_unique():
    assert len(IDS) == 23671                              # 公式サイトの総数
    assert len({i.lower() for i in IDS}) == len(IDS)      # 大文字小文字を無視しても重複なし
    assert all(i.count("-") >= 1 and i.strip() == i for i in IDS)


def test_canonical_id_is_injective_and_lowercase():
    canon = [canonical_id(i) for i in IDS]
    assert len(set(canon)) == len(IDS)
    assert all(c == c.lower() for c in canon)


def test_every_id_builds_a_url_that_round_trips():
    for i in IDS:
        u = urlparse(detail_url(i))
        assert u.scheme == "https" and u.path == "/card/detail/"
        assert parse_qs(u.query)["id"] == [i], i          # + や $ を含むIDも元のまま届く


def test_cache_names_are_safe_and_distinct():
    names = [cache_name(i) for i in IDS]
    assert all(re.fullmatch(r"[A-Za-z0-9%._-]+\.html", n) for n in names)
    assert len({n.lower() for n in names}) == len(names)


def test_normalize_never_fails_on_ledger_ids():
    for i in IDS:
        normalize_id(i)                                   # 人が打つ表記の整形。例外を出さない


def test_resolve_id_returns_the_official_id_for_every_ledger_id():
    known = ledger_ids()
    assert len(known) == len(IDS)
    for i in IDS:
        assert resolve_id(i) == i and resolve_id(i.lower()) == i


def test_or01_and_or1_are_different_cards():
    assert resolve_id("dm23rp4x-OR01") != resolve_id("dm23rp4x-OR1")


def test_id_doc_is_up_to_date():
    analyze_ids.main(["--check"])
