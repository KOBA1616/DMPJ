"""語彙パイロット第20弾（2026-10-31）の検証。

Zラッシュ（キーワード z_rush）: 自分のシールドが離れたら、ハイパーモードを解放する。
解放の期限（次の自分のターンのはじめまで）は第19弾の仕組みがそのまま処理する。
"""
from conftest import setup


def test_z_rush_releases_on_shield_leave(rules):
    e = setup(rules, {"bz": ["T060"], "shield": ["T001"]}, {"bz": ["T005"]})
    beast = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T060")
    assert not e.s.cards[beast].hyper
    # 相手がプレイヤーを攻撃してシールドをブレイクする（シールドが離れる）。
    # 解放は相手ターンに起きるので、自分のターンが来てもまだ解放されたままのはず
    broke = False
    for _ in range(40):
        if e.s.active == 0 and e.s.cards[beast].hyper:
            broke = True
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and d["player"] == 1 and "attack:T005:player" in keys:
            e.answer([keys.index("attack:T005:player")])
        elif d["kind"] == "yes_no":      # S・トリガー等の確認は使わない
            e.answer([keys.index("no")] if "no" in keys else list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert broke, "シールドが離れてもハイパーモードが解放されなかった（または自分のターンのはじめに解けてしまった）"
    # 解放されている間は、攻撃時にカードを引ける
    hand_before = len(e.zlist("hand", 0))
    drew = False
    for _ in range(60):
        if len(e.zlist("hand", 0)) > hand_before:
            drew = True
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and d["player"] == 0 and "attack:T060:player" in keys:
            e.answer([keys.index("attack:T060:player")])
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")] if "no" in keys else list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert drew
