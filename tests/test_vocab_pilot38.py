"""語彙パイロット第38弾（フェーズ16）: コストの合計制限つき選択（total_cost_selection 系39件）。

セレクタに total_cost_le / total_cost_ge を付けると、「コストの合計が N 以下／以上になるように
好きな数選ぶ」を1枚ずつ積み上げる選択で解決する。
"""
from conftest import setup


def _settle(e, done, drive=None, max_steps=150):
    for _ in range(max_steps):
        if done():
            return True
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if drive and drive(e, d, keys):
            continue
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    return done()


def _play_spell(e, st):
    def drive(e, d, keys):
        if d["kind"] == "main" and d["player"] == 0 and not st.get("played"):
            if "play:T114" in keys:
                st["played"] = True
                e.answer([keys.index("play:T114")])
                return True
        if d["kind"] == "pay_mana" and d["player"] == 0:
            e.answer([0])
            return True
        if d["kind"] == "choose_cards" and d["player"] == 0:
            return st["choose"](e, d)
        return False
    return drive


def test_total_cost_le_selection(rules):
    """合計6以下: コスト2と3を選ぶと、残りのコスト5は候補から外れて選択が終わる。"""
    e = setup(rules, {"hand": ["T114"], "mana": ["T005"] * 7},
              {"bz": ["T001", "T109", "T112"]})
    by_cost = {}
    for c in e.zlist("bz", 1):
        by_cost[e.chars(c)["cost"]] = c
    picks = [by_cost[2], by_cost[3]]

    def choose(e, d):
        want = picks.pop(0) if picks else None
        if want is None:
            e.answer([])
            return True
        idx = [i for i, o in enumerate(d["options"]) if o["cid"] == want]
        assert idx, "選んだカードが候補に無い"
        e.answer(idx[:1])
        return True

    st = {"choose": choose}
    assert _settle(e, lambda: e.s.cards[by_cost[2]].zone == "graveyard"
                   and e.s.cards[by_cost[3]].zone == "graveyard", _play_spell(e, st), 200)
    assert e.s.cards[by_cost[5]].zone == "bz"     # 合計を超える5は残る


def test_total_cost_le_stop_at_zero(rules):
    """0枚で止めることもできる（何も破壊しない）。"""
    e = setup(rules, {"hand": ["T114"], "mana": ["T005"] * 7}, {"bz": ["T001"]})
    target = e.zlist("bz", 1)[0]

    def choose(e, d):
        e.answer([])
        return True

    st = {"choose": choose, "played": False}
    _settle(e, lambda: bool(st.get("played")) and e.s.step == "attack", _play_spell(e, st), 200)
    assert e.s.cards[target].zone == "bz"
