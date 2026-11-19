"""第230弾: no_leave {by_opp_spell: true}（相手の呪文の効果では離れない）。"""
from tests.conftest import setup


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _cast_destroy(e, caster, target_defn, max_steps=120, spell="T006"):
    """破壊呪文を唱えて target を選ぶ（候補が1体だけなら選択は自動解決される）。"""
    for _ in range(max_steps):
        if spell in _defns(e, "graveyard", caster):
            return
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith(f"play:{spell}") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith(f"play:{spell}"))])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "choose_cards":
            pk = next((i for i, k in enumerate(keys) if target_defn in k), None)
            e.answer([pk] if pk is not None else list(range(d["min"])))
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("destroy spell did not resolve")


def _settle(e, steps=10):
    for _ in range(steps):
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))


def test_self_protected_from_opponent_spell():
    e = setup(_rules(), {"bz": ["T617"]},
              {"hand": ["T006"], "mana": ["T551", "T551", "T551"]})
    _cast_destroy(e, 1, "T617")
    _settle(e)
    assert "T617" in _defns(e, "bz", 0)          # 相手の呪文では離れない
    assert "T617" not in _defns(e, "graveyard", 0)


def test_ally_protected_but_granter_not():
    e = setup(_rules(), {"bz": ["T618", "T619"]},
              {"hand": ["T006"], "mana": ["T551", "T551", "T551"]})
    _cast_destroy(e, 1, "T619")
    _settle(e)
    assert "T619" in _defns(e, "bz", 0)          # 味方のアビスは守られる


def test_granter_itself_not_protected():
    e = setup(_rules(), {"bz": ["T618", "T619"]},
              {"hand": ["T006"], "mana": ["T551", "T551", "T551"]})
    _cast_destroy(e, 1, "T618")
    _settle(e)
    assert "T618" in _defns(e, "graveyard", 0)   # other: true なので本人は対象外


def test_own_spell_still_works():
    e = setup(_rules(), {"bz": ["T617"], "hand": ["T620"],
                         "mana": ["T551", "T551", "T551"]}, {})
    _cast_destroy(e, 0, "T617", spell="T620")
    _settle(e)
    assert "T617" in _defns(e, "graveyard", 0)   # 自分の呪文では離れる


def test_opponent_ability_still_works():
    # 相手のクリーチャーの能力（cause_kind=ability）では離れる
    e = setup(_rules(), {"bz": ["T617"]},
              {"hand": ["T621"], "mana": ["T551", "T551", "T551"]})
    for _ in range(120):
        if "T617" in _defns(e, "graveyard", 0):
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:T621") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T621"))])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "choose_cards":
            pk = next((i for i, k in enumerate(keys) if "T617" in k), None)
            e.answer([pk] if pk is not None else list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "T617" in _defns(e, "graveyard", 0)


def test_battle_loss_still_destroys():
    e = setup(_rules(), {"bz": ["T617"]}, {"bz": ["T397"]})
    cid = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T617")
    for _ in range(120):
        if "T617" in _defns(e, "graveyard", 0):
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and d["player"] == 1:
            e.s.cards[cid].tapped = True        # 攻撃される側をタップ状態にする
            ak = next((k for k in keys if "T617" in k), None)
            e.answer([keys.index(ak)] if ak else [keys.index("pass")])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "T617" in _defns(e, "graveyard", 0)   # バトル敗北では離れる


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()
