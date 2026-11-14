from dmsim import load_rules
from dmsim.engine import scenario
from dmsim.search import access as A


def _eng(deck, grave, hand):
    r = load_rules()
    spec = {"p0": {"hand": hand, "graveyard": grave, "deck": deck, "mana": ["dm22ex2-021"] * 3}, "p1": {}, "seed": 1}
    return r, scenario.build(r, spec, first_player=0)


def test_draw_win_shape_from_data():
    r = load_rules()
    f = A.draw_win(r, "dmrp03-s03")
    assert f == {"k": 1, "refill": ["graveyard"], "scheduled": 5}
    assert A.draw_win(r, "dm22ex1-007") is None
    assert A.grave_draws(r, "dmrp03-036") == 1


def test_drawout_counts_refill_and_own_turn_draws():
    r, e = _eng(["dm22ex1-007"] * 3, ["dm22ex1-007"] * 2, ["dmrp03-036"] * 2)
    d = A.drawout(e, "dmrp03-s03")
    n = len(e.s.zones["deck"][0]) + len(e.s.zones["graveyard"][0])  # 場面づくりが山札を補う場合も数える
    assert d["need"] == n and d["own_turn"] == 2
    assert d["ok_next"] == (n <= 7) and d["dig_before"] == max(0, n - 7)
    r, e = _eng(["dm22ex1-007"] * 9, ["dm22ex1-007"] * 6, [])
    d = A.drawout(e, "dmrp03-s03")
    n = len(e.s.zones["deck"][0]) + len(e.s.zones["graveyard"][0])
    assert d["need"] == n and d["dig_before"] == n - 5 and not d["ok_same_turn"]


def test_route_drawout_switch_adds_pred_only_when_on():
    from dmsim.search import route_goal as RG
    off = RG.load("saga_v3", drawout=False)
    on = RG.load("saga_v3", drawout=True)
    assert not any("drawout" in p for st in off for p in st.preds)
    added = [p for st in on for p in st.preds if "drawout" in p]
    assert added == [{"drawout": "dmrp03-s03"}]   # 効果データでドロー置換の勝ち手段と読める札だけ


def test_route_drawout_pred_progress():
    from dmsim.search import route_goal as RG
    r, e = _eng(["dm22ex1-007"] * 3, ["dm22ex1-007"] * 2, ["dmrp03-036"] * 2)
    p = {"drawout": "dmrp03-s03"}
    n = len(e.s.zones["deck"][0]) + len(e.s.zones["graveyard"][0])
    f = RG._frac(e, p, 0, 0.25)
    assert f == (1.0 if n <= 7 else 1 - (n - 7) / n)
    assert RG.holds(e, p, 0) == (n <= 7)
