"""語彙パイロット第40弾（フェーズ17-1）: 手札破棄の置換（discard_replacement 単独17件）。

「相手のクリーチャーの能力または呪文によって、このクリーチャーが自分の手札から捨てられる時、
墓地に置くかわりに出してもよい」は、既存の replace では「相手の効果によって」を表せず未対応だった。
移動イベントに、その移動を起こした効果の解決者 `by` を記録し（ops の env["you"] から付与）、
when に `by: opp` と書けるようにした。状況起因処理やコスト支払いなど効果解決者を伴わない移動には
by が付かないので、「相手の効果」扱いにはならない。
"""
from conftest import setup


def _settle(e, done, drive=None, max_steps=200):
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


def _drive(caster_defn, victim_defn=None):
    st = {"played": False}

    def drive(e, d, keys):
        if d["kind"] == "main" and d["player"] == 0 and not st["played"]:
            k = f"play:{caster_defn}"
            if k in keys:
                st["played"] = True
                e.answer([keys.index(k)])
                return True
        if d["kind"] == "pay_mana" and d["player"] == 0:
            e.answer(list(range(d["min"])))
            return True
        if d["kind"] == "choose_replacement":
            hit = [i for i, k in enumerate(keys) if "replace:" in k]
            if hit:   # 置換する（出す）
                e.answer([hit[0]])
                return True
        if d["kind"] == "choose_cards" and victim_defn:
            hit = [i for i, o in enumerate(d["options"]) if o.get("name") and victim_defn in str(o.get("key", ""))]
            hit = [i for i, k in enumerate(keys) if victim_defn in k]
            if hit:
                e.answer([hit[0]])
                return True
        return False
    return drive


def test_discard_by_opponent_effect_can_be_replaced_with_put(rules):
    """相手の呪文で捨てられる時は、かわりに出せる（by: opp）。"""
    e = setup(rules, {"hand": ["T117"], "mana": ["T008"] * 4},
              {"hand": ["T116"]})
    victim = next(c for c in e.zlist("hand", 1) if e.s.cards[c].defn == "T116")
    assert _settle(e, lambda: e.s.cards[victim].zone == "bz", _drive("T117", "T116"), 200)
    assert e.s.cards[victim].zone == "bz"
    assert victim not in e.zlist("graveyard", 1)


def test_discard_by_own_spell_is_not_replaced(rules):
    """自分の呪文で自分が捨てる時は置換が発火しない（by: you）。墓地に行く。"""
    e = setup(rules, {"hand": ["T118", "T116"], "mana": ["T008"] * 2}, {})
    victim = next(c for c in e.zlist("hand", 0) if e.s.cards[c].defn == "T116")
    assert _settle(e, lambda: e.s.cards[victim].zone == "graveyard", _drive("T118", "T116"), 200)
    assert e.s.cards[victim].zone == "graveyard"
    assert victim not in e.zlist("bz", 0)
