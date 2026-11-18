"""第229弾: bio_k（バイオ・K）イディオム。

attack_end（プレイヤーへの攻撃がブロックされなかった）で手札から捨てて効果を使う。
"""
from tests.conftest import setup


def _drive_attack(e, attacker, bio_check, max_steps=160):
    """attacker でプレイヤーを攻撃させ、bio_check(e) が真になるまで進める。"""
    for _ in range(max_steps):
        if bio_check(e):
            return
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack":
            ak = next((k for k in keys if k == f"attack:{attacker}:player"), None)
            e.answer([keys.index(ak)] if ak else [keys.index("pass")])
        elif kind == "yes_no":
            e.answer([0])                       # バイオ・Kを使う
        elif kind == "choose_one":
            nk = next((k for k in keys if k == "num:2"), None)
            e.answer([keys.index(nk)] if nk is not None else [0])
        elif kind == "choose_cards":
            pk = next((i for i, k in enumerate(keys) if "T613" in k), None)
            e.answer([pk] if pk is not None else list(range(d["min"])))
        elif kind == "block":
            e.answer([keys.index("no_block")])
        elif kind == "choose_shields":
            e.answer(list(range(d["min"])))
        elif kind == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("bio_k did not resolve")


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def test_bio_k_draw_up_to_2():
    e = setup(_rules(), {"bz": ["T613"], "hand": ["T610"]}, {})
    _drive_attack(e, "T613", lambda e: len(_defns(e, "hand", 0)) == 2)
    assert "T610" in _defns(e, "graveyard", 0)          # 捨てた
    assert len(_defns(e, "hand", 0)) == 2               # 2枚引いた


def test_bio_k_grant_double_breaker():
    # 付与はブレイクの前に解決するので、この攻撃で2枚ブレイクできる
    e = setup(_rules(), {"bz": ["T614"], "hand": ["T611"]}, {})
    shields_before = len(e.zlist("shield", 1))
    for _ in range(160):
        if len(e.zlist("shield", 1)) == shields_before - 2:
            break
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack":
            e.answer([keys.index("attack:T614:player")])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif d["kind"] == "choose_breaker":
            bk = next((k for k in keys if k == "breaks:2"), None)
            assert bk is not None, "W・ブレイカーがブレイク数に反映されていない"
            e.answer([keys.index(bk)])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert "T611" in _defns(e, "graveyard", 0)
    assert len(e.zlist("shield", 1)) == shields_before - 2   # 2枚ブレイクした


def test_bio_k_search_same_name():
    e = setup(_rules(), {"bz": ["T615"], "hand": ["T612"], "deck": ["T613"]}, {})
    _drive_attack(e, "T615", lambda e: "T613" in _defns(e, "hand", 0))
    assert "T613" in _defns(e, "hand", 0)               # 攻撃クリーチャーと同名を手札へ
    assert "T612" in _defns(e, "graveyard", 0)


def test_bio_k_not_when_blocked():
    # ブロックされたら誘発しない（相手にブロッカーを置く）
    e = setup(_rules(), {"bz": ["T613"], "hand": ["T610"]},
              {"bz": ["T004"]})
    blocked = []
    for _ in range(120):
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack":
            e.answer([keys.index("attack:T613:player")])
        elif d["kind"] == "block":
            bk = next((k for k in keys if "T004" in k), None)
            if bk is not None:
                blocked.append(True)
                e.answer([keys.index(bk)])
            else:
                e.answer([keys.index("no_block")])
        elif d["kind"] == "yes_no":
            e.answer([1])   # 万一出たら使わない（誘発したこと自体を下で否定する）
            blocked.append("triggered")
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if blocked and e.s.turn >= 2:
            break
    assert blocked and blocked[0] is True
    assert "triggered" not in blocked                   # バイオ・Kは誘発しなかった
    assert "T610" in _defns(e, "hand", 0)


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()
