"""語彙パイロット第144弾: パワーの合計制限つき選択（total_power_selection 系）。

セレクタに total_power_le / total_power_ge を付けると、「パワーの合計が N 以下／以上になるように
好きな数選ぶ」を1枚ずつ積み上げる選択で解決する（第38・39弾の total_cost_le/ge のパワー軸への一般化）。
合計に使うパワーは chars の現在パワー（常在型の修整込み）。
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


def _play_spell(e, st, spell="T171"):
    key = f"play:{spell}"

    def drive(e, d, keys):
        if d["kind"] == "main" and d["player"] == 0 and not st.get("played"):
            if key in keys:
                st["played"] = True
                e.answer([keys.index(key)])
                return True
        if d["kind"] == "pay_mana" and d["player"] == 0:
            e.answer([0])
            return True
        if d["kind"] == "choose_cards" and d["player"] == 0:
            return st["choose"](e, d)
        return False
    return drive


def _by_defn(e, player=1):
    return {e.cdef(c).id: c for c in e.zlist("bz", player)}


def test_total_power_le_selection(rules):
    """合計6000以下: パワー2000と2500を選ぶと、残りのパワー4000は候補から外れて選択が終わる。"""
    e = setup(rules, {"hand": ["T171"], "mana": ["T005"] * 7},
              {"bz": ["T001", "T109", "T112"]})
    by_power = {}
    for c in e.zlist("bz", 1):
        by_power[e.chars(c)["power"]] = c
    assert sorted(by_power) == [2000, 2500, 4000]
    picks = [by_power[2000], by_power[2500]]

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
    assert _settle(e, lambda: e.s.cards[by_power[2000]].zone == "graveyard"
                   and e.s.cards[by_power[2500]].zone == "graveyard", _play_spell(e, st), 200)
    assert e.s.cards[by_power[4000]].zone == "bz"     # 合計を超える4000は残る


def test_total_power_le_stop_at_zero(rules):
    """0枚で止めることもできる（何も破壊しない）。"""
    e = setup(rules, {"hand": ["T171"], "mana": ["T005"] * 7}, {"bz": ["T001"]})
    target = e.zlist("bz", 1)[0]

    def choose(e, d):
        e.answer([])
        return True

    st = {"choose": choose, "played": False}
    _settle(e, lambda: bool(st.get("played")) and e.s.step == "attack", _play_spell(e, st), 200)
    assert e.s.cards[target].zone == "bz"


def test_total_power_uses_current_power_with_static_boost(rules):
    """常在型のパワー修整が選択時の現在パワーに反映される。

    相手の場に T069（自分のクリーチャーすべて +1000）があると、相手クリーチャーの現在パワーは
    T001: 2000→3000、T005: 3000→4000、T109: 2500→3500 になる。合計6000以下では
    3000 を選んだ時点で残り（4000／3500）はどちらも予算外になり、選択は自動で終わる。
    印刷パワーで計算していたら 2000+3000=5000 で2体目も選べてしまうため、この結果にはならない。
    """
    e = setup(rules, {"hand": ["T171"], "mana": ["T005"] * 7},
              {"bz": ["T069", "T001", "T005", "T109"]})
    by_id = _by_defn(e)
    assert e.chars(by_id["T001"])["power"] == 3000
    assert e.chars(by_id["T005"])["power"] == 4000
    assert e.chars(by_id["T109"])["power"] == 3500

    def choose(e, d):
        idx = [i for i, o in enumerate(d["options"]) if o["cid"] == by_id["T001"]]
        assert idx, "選んだカードが候補に無い"
        e.answer(idx[:1])
        return True

    st = {"choose": choose}
    assert _settle(e, lambda: e.s.cards[by_id["T001"]].zone == "graveyard", _play_spell(e, st), 200)
    assert e.s.cards[by_id["T005"]].zone == "bz"     # 現在パワー4000は予算外（3000+4000>6000）
    assert e.s.cards[by_id["T109"]].zone == "bz"     # 現在パワー3500も予算外（3000+3500>6000）


def test_total_power_selection_respects_count_cap(rules):
    """合計10000以下・2体まで（T172）: 候補は2000+2500+4000で全て予算内でも、2体選んだ時点で選択が終わり3体目は残る。"""
    e = setup(rules, {"hand": ["T172"], "mana": ["T005"] * 7},
              {"bz": ["T001", "T109", "T112"]})
    targets = list(e.zlist("bz", 1))   # zlist は実リスト参照なのでコピーする（破壊で縮む）
    assert len(targets) == 3
    st = {"asks": 0}

    def choose(e, d):
        st["asks"] += 1
        e.answer([0])   # 常に先頭の候補を選ぶ（上限が無ければ3体目まで選んでしまう）
        return True

    st["choose"] = choose
    assert _settle(e, lambda: sum(1 for c in targets if e.s.cards[c].zone == "graveyard") == 2,
                   _play_spell(e, st, spell="T172"))
    destroyed = [c for c in targets if e.s.cards[c].zone == "graveyard"]
    remaining = [c for c in targets if e.s.cards[c].zone == "bz"]
    assert len(destroyed) == 2 and len(remaining) == 1, (
        f"2体までで止まらず: destroyed={len(destroyed)} remaining={len(remaining)} asks={st['asks']}")
    assert st["asks"] == 2   # 3回目の選択肢提示自体が無いこと
