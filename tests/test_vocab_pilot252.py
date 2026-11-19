"""第252弾: G・ブレイカー（相手も自分もシールドをすべてブレイクする）。"""
from tests.conftest import setup


def _cid(e, defn, player):
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _drive(e, choose_all=True, may_yes=True, stop=None, limit=600, cross=False):
    crossed_done = {"v": False}
    for _ in range(limit):
        if stop and stop(e):
            return
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_breaker":
            want = "breaks:all" if choose_all else "breaks:1"
            idx = keys.index(want) if want in keys else 0
            e.answer([idx])
        elif cross and not crossed_done["v"] and any(k.startswith("cross:") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("cross:"))])
            crossed_done["v"] = True
        elif any(k.startswith("play:") for k in keys) and d.get("player") == 0:
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:"))])
        else:
            a = next((i for i, k in enumerate(keys) if k.startswith("attack:")), None)
            if a is not None:
                e.answer([a])
            elif d["kind"] == "yes_no":
                e.answer([0] if may_yes else [1])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))


def test_g_breaker_breaks_all_both_sides():
    from dmsim.cards.defs import load_rules
    e = setup(load_rules(), {"bz": ["T683"]}, {"bz": ["T001"]})
    sh1 = len(e.zlist("shield", 1))
    sh0 = len(e.zlist("shield", 0))
    assert sh1 > 1 and sh0 > 1
    _drive(e, stop=lambda e: len(e.zlist("shield", 1)) == 0 and len(e.zlist("shield", 0)) == 0)
    assert len(e.zlist("shield", 1)) == 0            # 相手のシールドをすべてブレイク
    assert len(e.zlist("shield", 0)) == 0            # その後、自分のシールドもすべてブレイク


def test_g_breaker_single_break_choice():
    from dmsim.cards.defs import load_rules
    e = setup(load_rules(), {"bz": ["T683"]}, {"bz": ["T001"]})
    sh1 = len(e.zlist("shield", 1))
    sh0 = len(e.zlist("shield", 0))
    _drive(e, choose_all=False, stop=lambda e: len(e.zlist("shield", 1)) == sh1 - 1)
    assert len(e.zlist("shield", 1)) == sh1 - 1      # 通常の1枚ブレイクを選べる
    assert len(e.zlist("shield", 0)) == sh0          # 自分のシールドはブレイクしない


def test_gear_grants_g_breaker():
    from dmsim.cards.defs import load_rules
    e = setup(load_rules(), {"bz": ["T002"], "hand": ["T684"], "mana": ["T008"] * 10},
              {"bz": ["T001"]})
    host = _cid(e, "T002", 0)
    sh1 = len(e.zlist("shield", 1))
    _drive(e, cross=True,
           stop=lambda e: len(e.zlist("shield", 1)) == 0 and len(e.zlist("shield", 0)) == 0)
    gear = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T684")
    assert e.s.cards[gear].crossed[0] == host          # クロスできている（crossed はギア側が参照で持つ）
    assert len(e.zlist("shield", 1)) == 0
    assert len(e.zlist("shield", 0)) == 0
    assert sh1 > 1
