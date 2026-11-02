"""語彙パイロット第41弾（フェーズ17-2）: 「能力が書かれていない」フィルタ（vanilla）。

《アクア提督 ザ・ミスター》の「カードに能力が書かれていないクリーチャー」が reject 原因
（no_ability_filter）だった。filter に vanilla を追加: その面の定義に能力・キーワードが無く、
進化・NEO 等の書かれた仕組みも持たないカードに一致する（印刷された特性で判定し、付与は見ない）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dmsim import scenario  # noqa: E402


def test_vanilla_filter_takes_only_no_ability_creatures(rules):
    """山札の上3枚（バニラ／キーワード持ち／能力持ち）から、バニラだけが手札に加わる。"""
    e = scenario.build(rules, {
        "p0": {"hand": ["T119"], "mana": ["T001"] * 5, "deck": ["T001", "T002", "T008"]},
        "p1": {},
        "filler": "T005", "seed": 1, "deck_size": 20, "deck_exact": [True, False],
    })
    st = {"played": False}

    def drive(e, d, keys):
        if d["kind"] == "main" and d["player"] == 0 and not st["played"] and "play:T119" in keys:
            st["played"] = True
            e.answer([keys.index("play:T119")])
            return True
        if d["kind"] == "pay_mana" and d["player"] == 0:
            e.answer(list(range(d["min"])))
            return True
        return False

    for _ in range(300):
        hand_defns = [e.s.cards[c].defn for c in e.zlist("hand", 0)]
        if st["played"] and "T001" in hand_defns:
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if drive(e, d, keys):
            continue
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))

    hand_defns = [e.s.cards[c].defn for c in e.zlist("hand", 0)]
    deck_defns = [e.s.cards[c].defn for c in e.zlist("deck", 0)]
    assert hand_defns == ["T001"]            # バニラ（試験用ダミー）だけが手札へ
    assert sorted(deck_defns) == ["T002", "T008"]   # キーワード持ち・能力持ちは山札の下へ残った
    assert any(e.s.cards[c].defn == "T119" for c in e.zlist("bz", 0))
