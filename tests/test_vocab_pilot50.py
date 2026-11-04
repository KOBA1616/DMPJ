"""語彙パイロット第50弾（フェーズ17）: 回数制限つき許可のマナ召喚版（ターン1回）。

第37弾の墓地版と同じ方式をマナゾーンからの召喚にも広げる:
- 常在型の許可は mod allow の {action: summon_from_mana, once: true}（発生源ごとにターン1回）。
- 効果で与える許可（modify の継続的効果）も、発生源カードに帰属して共有の1回になる
  （chars が継続的効果の mod を ce の src＝発生源カードへ帰属させる）。
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


def _bz(e, defn):
    return sum(1 for c in e.zlist("bz", 0) if e.s.cards[c].defn == defn)


def test_once_per_turn_mana_grant_static(rules):
    """許可獣（T144）がいる間、マナゾーンから1体だけ召喚できる。
    マナは十分あるのに、同じターンに2体目は選択肢に出ない。"""
    e = setup(rules, {"bz": ["T144"], "mana": ["T001"] * 6}, {})
    st = {"offered": 0, "opp_turn": False}

    def drive(e, d, keys):
        if d["kind"] == "charge" and d["player"] == 1:
            st["opp_turn"] = True
        if d["kind"] == "main" and d["player"] == 0 and "play:T001:msum" in keys:
            st["offered"] += 1
            e.answer([keys.index("play:T001:msum")])
            return True
        if d["kind"] == "pay_mana" and d["player"] == 0:
            e.answer([0])
            return True
        return False

    assert _settle(e, lambda: st["opp_turn"], drive, 200)
    assert st["offered"] == 1          # 選択肢が出たのは1回だけ
    assert _bz(e, "T001") == 1         # 召喚できたのは1体だけ


def test_once_grant_recovers_next_turn(rules):
    """次の自分のターンには、もう1体マナから召喚できる。"""
    e = setup(rules, {"bz": ["T144"], "mana": ["T001"] * 8}, {})

    def drive(e, d, keys):
        if d["kind"] == "main" and d["player"] == 0 and "play:T001:msum" in keys:
            e.answer([keys.index("play:T001:msum")])
            return True
        if d["kind"] == "pay_mana" and d["player"] == 0:
            e.answer([0])
            return True
        return False

    assert _settle(e, lambda: _bz(e, "T001") == 2, drive, 600)
    assert _bz(e, "T001") == 2


def test_once_per_turn_mana_grant_spell(rules):
    """呪文（T145）で与えた許可も、発生源を共有するターン1回になる。
    唱える前はマナ召喚の選択肢が出ず、唱えた後は1体だけ出せる（2体目には出ない）。"""
    e = setup(rules, {"hand": ["T145"], "mana": ["T001"] * 6}, {})
    st = {"pre_offered": False, "cast": False, "summoned": 0, "opp_turn": False}

    def drive(e, d, keys):
        if d["kind"] == "charge" and d["player"] == 1:
            st["opp_turn"] = True
        if d["kind"] == "main" and d["player"] == 0:
            if not st["cast"] and "play:T001:msum" in keys:
                st["pre_offered"] = True
            if not st["cast"] and "play:T145" in keys:
                st["cast"] = True
                e.answer([keys.index("play:T145")])
                return True
            if st["cast"] and "play:T001:msum" in keys:
                st["summoned"] += 1
                e.answer([keys.index("play:T001:msum")])
                return True
        if d["kind"] == "pay_mana" and d["player"] == 0:
            e.answer([0])
            return True
        return False

    assert _settle(e, lambda: st["opp_turn"], drive, 300)
    assert st["pre_offered"] is False   # 許可が無ければ選択肢は出ない
    assert st["cast"] is True
    assert st["summoned"] == 1          # 共有の1回だけ
    assert _bz(e, "T001") == 1
