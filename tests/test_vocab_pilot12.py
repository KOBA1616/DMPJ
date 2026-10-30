"""語彙パイロット第12弾（2026-10-31）の検証。

アビスラッシュ（rejects: abyss_rush）: キーワード abyss_rush は墓地で機能する常在型
（allow: summon_from_graveyard）に展開される。メインステップの選択肢に墓地のカードが
「:rush」付きで出て、召喚すると、そのターンは召喚酔いでもプレイヤーを攻撃でき、
ターンの終わりに山札の下に置かれる。
"""
from conftest import setup


def test_abyss_rush_full_cycle(rules):
    e = setup(rules, {"graveyard": ["T047"], "mana": ["T008", "T008", "T008"]}, {})
    d = e.advance()
    assert d is not None and d["kind"] == "main"
    keys = [o["key"] for o in d["options"]]
    assert "play:T047:rush" in keys                       # 墓地からの召喚が選択肢に出る
    e.answer([keys.index("play:T047:rush")])
    cid = next(c for c in e.s.zones["graveyard"][0] if e.s.cards[c].defn == "T047")
    saw_attack_offer = False
    for _ in range(80):
        if e.s.cards[cid].zone == "deck":
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and "attack:T047:player" in keys:
            saw_attack_offer = True                       # 召喚したターンにプレイヤーを攻撃できる
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert saw_attack_offer
    assert e.s.cards[cid].zone == "deck"                  # ターンの終わりに山札の下へ
    assert e.s.zones["deck"][0][-1] == cid                # 一番下
