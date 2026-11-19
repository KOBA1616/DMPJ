"""第233弾: ランチャーE（唱える時に種族クリーチャーを好きな数タップ）。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _cast(e, spell, tap_count, target=None, max_steps=140):
    """呪文を唱え、ランチャー選択で tap_count 体タップする。"""
    tapped_before = None
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith(f"play:{spell}") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith(f"play:{spell}"))])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "choose_cards" and tapped_before is None \
                and d.get("min") == 0 and all(k.startswith("bz:") for k in keys):
            tapped_before = True
            e.answer(list(range(tap_count)))     # ランチャー: 先頭から tap_count 体
        elif d["kind"] == "choose_cards":
            pk = next((i for i, k in enumerate(keys) if target and target in k), None)
            e.answer([pk] if pk is not None else list(range(d["min"])))
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if spell in _defns(e, "graveyard", 0):
            return
    raise AssertionError("spell did not resolve")


def test_launcher_count_breaks_shields():
    e = setup(_rules(), {"bz": ["T621", "T621"], "hand": ["T630"],
                         "mana": ["T551"] * 3}, {})
    before = len(e.zlist("shield", 1))
    _cast(e, "T630", tap_count=2)
    assert len(e.zlist("shield", 1)) == before - 2      # タップした2体につき1枚ずつ
    tapped = [c for c in e.zlist("bz", 0) if e.s.cards[c].tapped]
    assert len(tapped) == 2


def test_launcher_zero_taps_no_effect():
    e = setup(_rules(), {"bz": ["T621"], "hand": ["T630"],
                         "mana": ["T551"] * 3}, {})
    before = len(e.zlist("shield", 1))
    _cast(e, "T630", tap_count=0)
    assert len(e.zlist("shield", 1)) == before


def test_launcher_total_power_destroy():
    # T621（3000）×2 をタップ → 合計6000以下の T534（5000）を破壊できる
    e = setup(_rules(), {"bz": ["T621", "T621"], "hand": ["T631"],
                         "mana": ["T551"] * 3}, {"bz": ["T534"]})
    _cast(e, "T631", tap_count=2, target="T534")
    assert "T534" in _defns(e, "graveyard", 1)


def test_repeat_over_puts_same_name():
    # T621 を1体タップ → 山札から同名の T621 がもう1体出る
    e = setup(_rules(), {"bz": ["T621"], "hand": ["T632"], "deck": ["T621"],
                         "mana": ["T551"] * 3}, {})
    tapped = False
    for _ in range(60):
        if _defns(e, "bz", 0).count("T621") == 2:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and any(k.startswith("play:T632") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("play:T632"))])
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "choose_cards" and not tapped \
                and d.get("min") == 0 and all(k.startswith("bz:") for k in keys):
            tapped = True
            e.answer([0])            # ランチャーで1体タップ
        elif d["kind"] == "choose_cards" and d.get("min") == 0 and len(keys) == 1:
            e.answer([0])            # 同名の1体を出す
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert _defns(e, "bz", 0).count("T621") == 2
