"""デッキ単位の再現性（多色カードは各文明をマナに1枚ずつ）。"""
from dmsim.discovery.reproducibility import play_ready_prob
from dmsim.defs import DATA


def test_multicolor_card_needs_every_civ_in_mana(rules):
    mono = ["T001"] * 40
    # T001 の文明に合わせて、単色デッキ（必要文明は常にそろう）と、狙うカードが3色のデッキを比べる
    K, D = "dm25ex3-028", "dm25ex3-055"
    import pathlib, tempfile
    import test_dmc_knight as t
    r = t._small_rules(pathlib.Path(tempfile.mkdtemp()))
    deck_ok = [K] * 4 + [D] * 4 + ["T001"] * 16 + ["T002"] * 8 + ["T003"] * 8
    p = play_ready_prob(r, deck_ok, K, turns=(3, 5, 7), n=400)
    assert p[3] <= p[5] <= p[7]                 # ターンが遅いほど高い
    deck_bad = [K] * 4 + ["T001"] * 36           # 他の文明のカードが無いデッキ
    q = play_ready_prob(r, deck_bad, K, turns=(7,), n=400)
    assert q[7] <= p[7]                          # 文明がそろいにくいデッキは低い
