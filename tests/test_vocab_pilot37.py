"""語彙パイロット第37弾（フェーズ15）: 回数制限つき許可（ターン1回）。

他者への許可の mod allow に {action: summon_from_graveyard, once: true} と書くと、
発生源ごとにターン1回だけ墓地召喚の選択肢が出る（cost_may の once と同じ使用記録方式）。
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


def test_once_per_turn_graveyard_grant(rules):
    """許可獣がいる間、墓地から1体だけ召喚できる。マナが足りていても2体目は同じターンに出せない
    （制限が無ければ、2体目の選択肢が出てこのドライブが続けて召喚してしまう）。"""
    e = setup(rules, {"bz": ["T113"], "graveyard": ["T008", "T008"], "mana": ["T008"] * 6}, {})
    st = {"offered_first": False, "opp_turn": False}

    def bz_t008():
        return sum(1 for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T008")

    def drive(e, d, keys):
        if d["kind"] == "charge" and d["player"] == 1:
            st["opp_turn"] = True
        if d["kind"] == "main" and d["player"] == 0 and "play:T008:rush" in keys:
            st["offered_first"] = True
            e.answer([keys.index("play:T008:rush")])
            return True
        if d["kind"] == "pay_mana" and d["player"] == 0:
            e.answer([0])
            return True
        return False

    # P0 のターンが終わる（相手のチャージ決定が出る）まで進める
    assert _settle(e, lambda: st["opp_turn"], drive, 200)
    assert st["offered_first"] is True        # 最初は選択肢が出る
    assert bz_t008() == 1                     # 召喚できたのは1体だけ


def test_once_grant_recovers_next_turn(rules):
    """次の自分のターンには、もう1体召喚できる。"""
    e = setup(rules, {"bz": ["T113"], "graveyard": ["T008", "T008"], "mana": ["T008"] * 6}, {})
    st = {"summons": 0, "turn1_done": False}

    def bz_t008():
        return sum(1 for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T008")

    def drive(e, d, keys):
        if d["kind"] == "charge" and d["player"] == 0 and e.s.turn >= 3:
            st["turn1_done"] = True
        if d["kind"] == "main" and d["player"] == 0 and "play:T008:rush" in keys:
            before = bz_t008()
            e.answer([keys.index("play:T008:rush")])
            st["summons"] = before + 1
            return True
        if d["kind"] == "pay_mana" and d["player"] == 0:
            e.answer([0])
            return True
        return False

    assert _settle(e, lambda: bz_t008() == 2, drive, 600)
    assert bz_t008() == 2
