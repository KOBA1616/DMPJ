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
