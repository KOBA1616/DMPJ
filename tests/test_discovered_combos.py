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
    r = rc.run_one(rules, le.load("akashic_hd2_v1"), 1)
    assert r["stage1"] and r["stage2"] and r["via"] == "loop" and r["win_turn"] == 1


def _names(e, z, p):
    return sorted(e.s.cards[c].defn for c in e.zlist(z, p))


def test_akashic_hd2_one_lap_follows_rules_605_2f_and_810(rules):
    """1周を手で回す。唱えた呪文（ツインパクトの呪文面）は解決後に墓地へ（605.2f）、
    墓地のツインパクトはクリーチャーとして選べる（810.1/810.3）。"""
    import sys
    sys.path.insert(0, "tests")
    from conftest import answer, setup
    e = setup(rules, {"bz": ["dm23ex2-009"], "hand": ["dmrp07-009", "dm23bd7-035"], "graveyard": ["dm23bd7-035"]},
              {}, deck_size=20)
    opp_mana = len(e.zlist("mana", 1))
    answer(e, "charge", "pass")
    answer(e, "main", "play:dmrp07-009:1:free")          # アカシック3 で無償詠唱（H.D.2. の面）
    answer(e, "choose_mode", "mode:1")                     # 相手を選ぶ
    d = e.advance()                                        # 解決して次のメイン
    assert d["kind"] == "main"
    assert len(e.zlist("mana", 1)) == opp_mana + 2
    assert _names(e, "graveyard", 0) == ["dm23bd7-035", "dmrp07-009"]   # 605.2f
    from conftest import find_option
    e.answer([find_option(d, "play:dm23bd7-035:1:free")])  # 訪れる魔の時刻
    d = e.advance()
    while d is not None and d["kind"] != "main":
        e.answer(list(range(len(d["options"]))) if d["kind"] == "choose_cards" else [0])
        d = e.advance()
    assert _names(e, "hand", 0) == ["dm23bd7-035", "dmrp07-009"]        # 墓地のツインパクト2枚をクリーチャーとして回収
    assert _names(e, "graveyard", 0) == ["dm23bd7-035"]
