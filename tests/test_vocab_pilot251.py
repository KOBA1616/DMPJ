"""第251弾: 攻撃の中止（cancel_attack op）。"""
from tests.conftest import setup


def _cid(e, defn, player):
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _drive(e, may_yes=True, stop=None, limit=400):
    for _ in range(limit):
        if stop and stop(e):
            return
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
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


def test_discard_cancels_attack():
    from dmsim.cards.defs import load_rules
    e = setup(load_rules(), {"bz": ["T002"]}, {"bz": ["T680"], "hand": ["T001"]})
    atk = _cid(e, "T002", 0)
    sh0 = len(e.zlist("shield", 1))
    _drive(e, may_yes=True, stop=lambda e: e.s.cards[atk].tapped and len(e.zlist("graveyard", 1)) == 1)
    assert len(e.zlist("shield", 1)) == sh0          # ブレイクされていない
    assert len(e.zlist("graveyard", 1)) == 1         # 捨てた手札が墓地にある
    assert e.s.cards[atk].tapped                     # 攻撃クリーチャーはタップしたまま


def test_destroy_self_cancels_player_attack():
    from dmsim.cards.defs import load_rules
    e = setup(load_rules(), {"bz": ["T002"]}, {"bz": ["T681"]})
    kiku = _cid(e, "T681", 1)
    sh0 = len(e.zlist("shield", 1))
    _drive(e, may_yes=True, stop=lambda e: e.s.cards[kiku].zone == "graveyard")
    assert e.s.cards[kiku].zone == "graveyard"
    assert len(e.zlist("shield", 1)) == sh0


def test_no_cancel_when_creature_attacked():
    from dmsim.cards.defs import load_rules
    e = setup(load_rules(), {"bz": ["T002"]}, {"bz": ["T681", "T001"]})
    tgt = _cid(e, "T001", 1)
    kiku = _cid(e, "T681", 1)
    atk = _cid(e, "T002", 0)
    phase = {"p1_attacked": False}
    for _ in range(600):
        if e.s.cards[atk].zone == "graveyard":
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and d.get("player") == 1 and not phase["p1_attacked"]:
            a = next(i for i, k in enumerate(keys) if k.startswith("attack:T001"))
            e.answer([a])                            # P1 の T001 が攻撃してタップする
            phase["p1_attacked"] = True
        elif d["kind"] == "attack" and d.get("player") == 0 and phase["p1_attacked"]:
            a = next((i for i, k in enumerate(keys) if k.startswith("attack:") and k.endswith(":T001")), None)
            if a is not None:
                e.answer([a])                        # タップした T001 を攻撃する
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert e.s.cards[atk].zone == "graveyard"        # バトルは行われ、弱い攻撃側が破壊された（中止されていない）
    assert e.s.cards[tgt].zone == "bz"
    assert e.s.cards[kiku].zone == "bz"              # 菊の誘発は出なかった


def test_jtornado_decline_cancels_own_attack():
    from dmsim.cards.defs import load_rules
    e = setup(load_rules(), {"bz": ["T682", "T682"]}, {"bz": ["T001"]})
    sh0 = len(e.zlist("shield", 1))
    atks = [c for c in e.zlist("bz", 0) if e.s.cards[c].controller == 0]
    _drive(e, may_yes=False, stop=lambda e: any(e.s.cards[c].tapped for c in atks))
    assert len(e.zlist("shield", 1)) == sh0          # 自分の攻撃が中止された


def test_jtornado_accept_lets_attack_through():
    from dmsim.cards.defs import load_rules
    e = setup(load_rules(), {"bz": ["T682", "T682"]}, {"bz": ["T001"]})
    sh0 = len(e.zlist("shield", 1))
    _drive(e, may_yes=True, stop=lambda e: len(e.zlist("shield", 1)) < sh0)
    assert len(e.zlist("shield", 1)) == sh0 - 1      # バウンスしたので攻撃は通り、ブレイクした
    mine = [c for c in e.zlist("bz", 0) if e.s.cards[c].controller == 0]
    assert len(mine) == 1                            # もう1体は手札に戻った
