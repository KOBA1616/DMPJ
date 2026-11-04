"""組の候補の自動選択（効果データの入出力のつなぎ）。"""
import pathlib
import tempfile

import test_dmc_knight as t
from dmsim.discovery import candidates as cd


def _rules():
    return t._small_rules(pathlib.Path(tempfile.mkdtemp()))


def test_card_io_reads_zone_writes_and_consumers():
    r = _rules()
    k, d = cd.card_io(r, t.K), cd.card_io(r, t.D)
    assert {"shield", "graveyard", "hand"} <= k["writes_to"]
    assert "shield" in d["consumes_to"] and "graveyard" in d["reads_zones"]


def test_candidate_pairs_link_knight_to_dmc_and_ignore_vanilla():
    r = _rules()
    pairs = cd.candidate_pairs(r, [t.K, t.D, "T001"])
    ab = [p for p in pairs if (p["a"], p["b"]) == (t.K, t.D)]
    assert ab and "to:shield" in ab[0]["links"]
    assert all("T001" not in (p["a"], p["b"]) for p in pairs)       # 無関係な（バニラの）カードは候補に出ない
    assert not [p for p in pairs if (p["a"], p["b"]) == (t.D, t.K)]  # 騎士は DMC の出力で誘発しない


def test_discover_combos_confirms_the_candidate_with_the_engine():
    r = _rules()
    got = cd.discover_combos(r, [t.K, t.D, "T001"], base={"mana": [t.D] * 3}, opp={"bz": ["T001"]},
                             places=("hand", "graveyard"), seeds=(1,))
    assert len(got) == 1 and (got[0]["a"], got[0]["b"]) == (t.K, t.D)
    assert {(w["place_a"], w["place_b"]) for w in got[0]["works"]} == {("hand", "hand"), ("hand", "graveyard")}
