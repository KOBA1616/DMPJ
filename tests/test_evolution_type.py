def test_evolution_cards_require_source(rules):
    """進化の行があるのに types に evolution が無い札は読み込み時に補う（抜けると進化元なしで出せてしまう）。"""
    bad = [i for i, c in rules.cards.items() if c.evolve_from and "evolution" not in c.types and not c.faces
           and not (c.neo or c.grave_evo or c.s_max)]
    assert bad == []
