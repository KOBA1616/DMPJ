"""既知ループの再発見率の指標（dmsim/eval/known_loops.py）。"""
from dmsim.cards.defs import load_rules
from dmsim.eval import known_loops as K


def test_known_loops_measure(monkeypatch):
    monkeypatch.delenv("DMSIM_SKIP_CONVERTED", raising=False)
    m = K.measure(load_rules(only_approved=False), names=("akashic", "jashin_abyss"), max_nodes=800, laps_max=1, tries=2)
    by = {r["name"]: r for r in m["rows"]}
    assert by["akashic"]["why"] == "no_origin"     # 攻撃を選べない盤面は合成手の対象外
    assert by["jashin_abyss"]["found"]
    assert (m["found"], m["total"]) == (1, 2)
