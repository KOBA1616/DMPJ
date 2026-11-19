"""第245弾の登録形: dm26ex2-046 断罪のロスト・サイン（ラウンド279）。"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules
from dmsim.scenario import build


def test_registered_form():
    rules = load_rules()
    assert "dm26ex2-046" in rules.cards
    # 山札は対象クリーチャー（dm26ex2-…の代わりに登録済みのロスト・クルセイダー）を混ぜる:
    # ここでは converted 内のロスト・クルセイダー creature を1種使う
    crus = None
    for cid, c in rules.cards.items():
        if "creature" in c.types and any("ロスト・クルセイダー" in r for r in c.races) and cid != "dm26ex2-046":
            crus = cid
            break
    assert crus, "ロスト・クルセイダーのクリーチャーが converted に無い"
    e = build(rules, {"p0": {"hand": ["dm26ex2-046"], "mana": ["T030"] * 5, "deck": [crus] * 8},
                      "p1": {"deck": ["T002"] * 8}, "filler": "T001", "seed": 1, "deck_size": 8})
    cast = {"done": False}
    seen = {}
    for _ in range(80):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "order_cards":
            cr = next(c for c in e.zlist("bz", 0) if e.s.cards[c].defn == crus)
            seen["blocker"] = "blocker" in e.chars_ro(cr)["keywords"]
            seen["cr"] = cr
            e.answer(list(range(len(keys))))
            break
        play = next((i for i, k in enumerate(keys) if k == "play:dm26ex2-046"), None)
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
    assert seen.get("blocker"), "登録形: ブロッカーが付いていない"
    # 次の自分のターンのはじめに手札に戻る（召喚した個体そのものを追う: CIP ドローで同名が手札に来るため）
    cr = seen["cr"]
    for _ in range(200):
        if cr in e.zlist("hand", 0):
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert cr in e.zlist("hand", 0)
    assert cr not in e.zlist("bz", 0)
