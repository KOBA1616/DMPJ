"""第245弾: 見た4枚から無料召喚 → ブロッカー付与 → 次の自ターン開始時に手札へ（遅延 var 参照）。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def _drive(e, stop, cast, cap=400):
    for _ in range(cap):
        if stop():
            return True
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        play = next((i for i, k in enumerate(keys) if k == "play:T663"), None)
        if d["kind"] == "main" and play is not None and not cast["done"]:
            cast["done"] = True
            e.answer([play])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return stop()


def test_summon_blocker_and_delayed_return():
    # 山札は T664 のみ（シャッフル後も上4枚はすべて対象）。マナ5枚で T663 を唱える
    e = setup(_rules(),
              {"hand": ["T663"], "mana": ["T030"] * 5, "deck": ["T664"] * 8},
              {"deck": ["T002"] * 8}, deck_size=8)
    assert len(e.zlist("deck", 0)) == 11                    # 指定8枚＋フィラー3枚
    cast = {"done": False}
    # 残りの順序決め（order_cards）の時点で召喚と付与は完了している。その場でブロッカーを確認する
    # （ターン終了を跨ぐと end_of_turn の付与は失効して観測できない）
    seen = {}
    for _ in range(60):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "order_cards":
            cr = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T664")
            seen["blocker"] = "blocker" in e.chars_ro(cr)["keywords"]
            seen["cr"] = cr
            e.answer(list(range(len(keys))))
            break
        play = next((i for i, k in enumerate(keys) if k == "play:T663"), None)
        if d["kind"] == "main" and play is not None and not cast["done"]:
            cast["done"] = True
            e.answer([play])
        elif d["kind"] == "yes_no":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert seen.get("blocker"), "このターン、ブロッカーを得ていない"
    cr = seen["cr"]
    ok = _drive(e, lambda: any(e.s.cards[c].defn == "T663" for c in e.zlist("graveyard", 0)), cast)
    assert ok
    assert len(e.zlist("deck", 0)) == 10                    # 4枚見て1枚召喚、残り3枚は下へ戻る（純減は召喚の1枚だけ）
    # 次の自分のターンのはじめに手札に戻る
    ok = _drive(e, lambda: any(e.s.cards[c].defn == "T664" for c in e.zlist("hand", 0)), cast)
    assert ok, "次の自ターン開始時に手札へ戻らなかった"
    assert not any(e.s.cards[c].defn == "T664" for c in e.zlist("bz", 0))
