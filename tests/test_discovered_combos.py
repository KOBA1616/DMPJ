"""システムが見つけた新規コンボ（data/discovered_combos/combos.yaml）の記録と入口局面の検査。"""
from pathlib import Path

import pytest
import yaml

from dmsim.eval import loop_entry as le
from dmsim.eval import ruler_control as rc



@pytest.fixture(scope="module")
def rules():
    import os
    from dmsim.cards.defs import load_rules
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)   # オルゼキアは converted.yaml 側
    try:
        return load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old


PATH = Path("data/discovered_combos/combos.yaml")


def test_records_have_entry_and_parts_in_deck():
    combos = yaml.safe_load(PATH.read_text(encoding="utf-8"))["combos"]
    assert sum(c["counted"] for c in combos) >= 1
    for c in combos:
        ls = le.load(Path(c["entry"]).stem)
        deck = le.deck_of(ls)
        for p in c["parts"]:
            assert deck.count(p["id"]) >= p["n"]


def test_akashic_hd2_entry_wins_by_loop(rules):
    r = rc.run_one(rules, le.load("akashic_hd2"), 1)
    assert r["stage1"] and r["stage2"] and r["via"] == "loop" and r["win_turn"] == 1
