"""カードIDの正規化と、実カードが公式の形式のIDで管理されていること。"""
import pytest

from dmsim.cardid import is_official_id, normalize_id, pack_ids, set_code


@pytest.mark.parametrize("raw,want", [
    ("DMRP1-5", "dmrp01-005"), ("DMRP-03 S3", "dmrp03-s03"), ("DM22-EX2 21", "dm22ex2-021"),
    ("dm22ex2-021", "dm22ex2-021"), ("DM-06 57", "dm06-057"), ("DMEX-17 W2", "dmex17-w02"),
    ("DM-01-110", "dm01-110"), ("dmr16g-054", "dmr16g-054"),
])
def test_normalize_id(raw, want):
    assert normalize_id(raw) == want and is_official_id(want)


def test_pack_ids():
    assert pack_ids("DMRP1", 3) == ["dmrp01-001", "dmrp01-002", "dmrp01-003"]
    assert set_code("DMRP-01") == set_code("dmrp1") == "dmrp01"


def test_all_real_cards_are_managed_by_their_official_id(rules):
    for cd in rules.cards.values():
        if cd.source:
            assert is_official_id(cd.id), cd.id
            assert normalize_id(cd.id) == cd.id
            assert cd.source.get("official") == cd.id, cd.id


def test_fetch_parse_splits_set_notation_from_name():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import fetch_cards
    page = ("<title>三冠王者 ドツキング(DMRP01 1/93) | デュエル・マスターズ</title><table><tr><th>カードの種類</th><td>クリーチャー</td></tr>"
            "<tr><th>文明</th><td>ゼロ</td></tr><tr><th>コスト</th><td>6</td></tr><tr><th>特殊能力</th><td>W・ブレイカー</td></tr></table>")
    row = fetch_cards.parse("dmrp01-001", page)
    assert row["name"] == "三冠王者 ドツキング" and row["set_notation"] == "DMRP01 1/93" and row["cost"] == "6"


def test_ids_with_letters_in_the_number_keep_their_digits():
    assert normalize_id("dm26ex4-CHO005") == "dm26ex4-cho005" and is_official_id("dm26ex4-cho005")
    assert normalize_id("DM26-EX4 CHO5") == "dm26ex4-cho05"
