"""語彙パイロット第35弾（フェーズ13）:
「攻撃するかわりにタップして使う」起動型能力は既存の kind: activate（攻撃ステップで提示）で表せる。
今回の拡張は DM24 系の複合コスト: cost に tap_mana: N（マナゾーンのタップされていないカードを N 枚追加でタップ）。
"""
from conftest import setup


def _settle(e, done, drive=None, max_steps=120):
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


def test_compound_activate_cost(rules):
    """複合コスト: 攻撃ステップで activate を選び、マナ2枚をタップしてドローする（攻撃はしない）。"""
    e = setup(rules, {"bz": ["T109"], "mana": ["T005"] * 3}, {})
    cid = e.zlist("bz", 0)[0]
    state = {}

    def drive(e, d, keys):
        if d["kind"] == "attack" and d["player"] == 0 and not state.get("used"):
            hit = [i for i, k in enumerate(keys) if k.startswith("activate:T109")]
            if hit:
                state["used"] = True
                state["hand_before"] = len(e.zlist("hand", 0))
                e.answer([hit[0]])
                return True
        if d["kind"] == "choose_cards" and d["player"] == 0:
            e.answer(list(range(d["min"])))
            return True
        return False

    assert _settle(e, lambda: len(e.zlist("hand", 0)) == state.get("hand_before", -99) + 1 and state.get("used"),
                   drive, 200)
    assert e.s.cards[cid].tapped                                    # 本体はタップされた
    tapped_mana = [m for m in e.zlist("mana", 0) if e.s.cards[m].tapped]
    assert len(tapped_mana) == 2                                     # マナ2枚がコストでタップ
    assert len(e.zlist("shield", 1)) == 5                            # 攻撃はしていない


def test_compound_activate_needs_untapped_mana(rules):
    """マナが足りない時は activate 選択肢が出ない（攻撃はできる）。"""
    e = setup(rules, {"bz": ["T109"], "mana": ["T005"]}, {})
    seen = {}

    def drive(e, d, keys):
        if d["kind"] == "attack" and d["player"] == 0:
            seen["activate"] = any(k.startswith("activate:T109") for k in keys)
            seen["attack"] = any(k.startswith("attack:T109") for k in keys)
            if "pass" in keys:
                e.answer([keys.index("pass")])
                return True
        return False

    _settle(e, lambda: "activate" in seen, drive, 120)
    assert seen["attack"] is True
    assert seen["activate"] is False


def test_plain_activate_still_works(rules):
    """単独コスト（tap: self のみ）の従来型も攻撃ステップで使える。"""
    e = setup(rules, {"bz": ["T110"], "mana": ["T001"] * 3}, {})
    cid = e.zlist("bz", 0)[0]
    state = {}

    def drive(e, d, keys):
        if d["kind"] == "attack" and d["player"] == 0 and not state.get("used"):
            hit = [i for i, k in enumerate(keys) if k.startswith("activate:T110")]
            if hit:
                state["used"] = True
                state["hand_before"] = len(e.zlist("hand", 0))
                e.answer([hit[0]])
                return True
        return False

    assert _settle(e, lambda: len(e.zlist("hand", 0)) == state.get("hand_before", -99) + 1 and state.get("used"),
                   drive, 200)
    assert e.s.cards[cid].tapped
