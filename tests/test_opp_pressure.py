from dmsim.eval.opp_pressure import opp_pressure


class E:
    def __init__(s, z): s.z = z
    def zlist(s, zone, p): return [0] * s.z[(zone, p)]


def test_pressure_counts_opp_decrease():
    full = E({("mana", 1): 6, ("deck", 1): 30, ("shield", 1): 5})
    low = E({("mana", 1): 2, ("deck", 1): 30, ("shield", 1): 5})
    assert opp_pressure(full, 0) == 0
    assert opp_pressure(low, 0) == 4
