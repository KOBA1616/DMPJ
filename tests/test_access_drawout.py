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


def test_drawout_pre_refill_line_with_trigger_order():
    """山札1枚・進化元にイワシン: 戻す効果より先にイワシンで引けば勝てる（dig_before 0）。"""
    r = load_rules()
    spec = {"p0": {"hand": ["dm22ex1-007"], "mana": ["dmex10-020"] * 4,
                   "graveyard": ["dmrp03-036"] * 8 + ["dmrp03-s03"] + ["dmex10-020"] * 10, "deck": ["dm22ex2-021"]},
            "p1": {}, "seed": 1, "deck_exact": [True, False]}
    e = scenario.build(r, spec, first_player=0)
    d = e.advance()
    while d["kind"] != "main":
        e.answer([[o["key"] for o in d["options"]].index("pass")]); d = e.advance()
    e.answer_by_keys(["play:dm22ex1-007"]); d = e.advance()
    keys = [o["key"] for o in d["options"]]
    e.answer([i for i, k in enumerate(keys) if "dmrp03-036" in k][:d["max"]])
    e.advance()
    out = A.drawout(e, "dmrp03-s03")
    assert out["pre"] == 1 and out["need_pre"] == 1 and out["ok_pre"] and out["dig_before"] == 0
    assert not out["ok_next"]   # 戻す効果の後では墓地の10枚が戻って届かない


def test_engine_lets_player_order_pending_triggers():
    """メテオバーンでイワシンを墓地に置き、墓地からシャコガイルを出すと、両方の誘発の順を選べ、イワシンが先なら勝つ。"""
    from dmsim.engine.view import result_of
    r = load_rules()
    spec = {"p0": {"hand": ["dm22ex1-007"], "mana": ["dmex10-020"] * 4,
                   "graveyard": ["dmrp03-036"] * 8 + ["dmrp03-s03"] + ["dmex10-020"] * 10, "deck": ["dm22ex2-021"]},
            "p1": {}, "seed": 1, "deck_exact": [True, False]}
    e = scenario.build(r, spec, first_player=0)
    d = e.advance(); seen = []
    for _ in range(60):
        if d is None or result_of(e):
            break
        keys = [o["key"] for o in d["options"]]
        seen.append(d["kind"])
        if d["kind"] in ("charge",):
            e.answer([keys.index("pass")])
        elif d["kind"] == "main":
            e.answer([keys.index("play:dm22ex1-007")] if "play:dm22ex1-007" in keys else [keys.index("pass")])
        elif d["kind"] == "choose_evo_source":
            e.answer([i for i, k in enumerate(keys) if "dmrp03-036" in k][:d["max"]])
        elif d["kind"] == "attack":
            e.answer([keys.index("attack:dm22ex1-007:player")])
        elif d["kind"] == "choose_cards" and any("dmrp03-s03" in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if "dmrp03-s03" in k)])
        elif d["kind"] == "choose_cards" and any("dmrp03-036" in k for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if "dmrp03-036" in k)])
        elif d["kind"] == "order_pending":
            e.answer([next(i for i, k in enumerate(keys) if "dmrp03-036" in k)])
        else:
            e.answer(list(range(d["min"])) if d["min"] else [0])
        d = e.advance()
    assert "order_pending" in seen
    assert result_of(e)["winner"] == 0 and result_of(e)["reason"] == "effect" and e.s.turn == 1


def test_continuous_score_gates_after_entry_and_counts_remaining(monkeypatch):
    from dmsim.search import route_goal as RG
    monkeypatch.setenv("DMSIM_DRAWOUT", "1")
    st = RG.load("saga_v3")
    e_idx = RG.entry_index(st)
    assert e_idx > 0 and RG.drawout_wins(st) == ["dmrp03-s03"]
    r, e = _eng(["dm22ex1-007"] * 3, [], [])
    # 入口に届いていない局面では入口より後ろの段の点・残りの減点は付かない
    v0 = RG.continuous_score(e, st, 0, 0, ["dmrp03-s03"], e_idx, False, 0.25)
    v1 = RG.continuous_score(e, st, 0, e_idx, ["dmrp03-s03"], e_idx, False, 0.25)
    assert v1 < sum(s.weight for s in st[:e_idx]) + 1e-9   # 入口後は残りの分だけ減点
    assert v0 <= sum(s.weight for s in st[:e_idx - 1]) + 1e-9


def test_remaining_pre_line_counts_chain_and_needs_win_in_grave():
    r = load_rules()
    from dmsim.search import access as A2
    assert A2.grave_discards(r, "dmrp03-036") and not A2.grave_discards(r, "dm22ex2-021")
    spec = {"p0": {"hand": ["dm22ex1-007"] + ["dmrp03-036"] * 2, "mana": ["dmex10-020"] * 4,
                   "graveyard": ["dmrp03-036"] * 8 + ["dmrp03-s03"] + ["dmex10-020"] * 10, "deck": ["dm22ex2-021"] * 3},
            "p1": {}, "seed": 1, "deck_exact": [True, False]}
    e = scenario.build(r, spec, first_player=0)
    # 山札3、手札に引いて捨てる札2枚（連鎖2）、墓地に引く札と勝ち手段: あと1手（進化元へ）で取れる → 残り 1
    assert A2.remaining(e, "dmrp03-s03") == max(0, 3 - 1 + 1 - 1 - 2) + 1
