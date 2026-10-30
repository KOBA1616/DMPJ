"""語彙パイロット第8弾（2026-10-31）の検証。

op `mekurade`（rejects: mekurade）: 山札の上からN枚（既定3）を見て、条件に合う1枚を
コストを支払わずに使ってもよい。残りは好きな順序で山札の下に置く。
"""
from conftest import answer, setup


def set_top(e, p, defns):
    """山札の先頭を指定した並びにする（テストの都合）。"""
    deck = e.s.zones["deck"][p]
    picked = []
    for name in defns:
        cid = next(c for c in deck if e.s.cards[c].defn == name and c not in picked)
        picked.append(cid)
    rest = [c for c in deck if c not in picked]
    e.s.zones["deck"][p][:] = picked + rest


def drive_until(e, pred, limit=80):
    for _ in range(limit):
        if pred():
            return
        d = e.advance()
        assert d is not None
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    assert pred()


def test_mekurade_plays_one_and_bottoms_rest(rules):
    e = setup(rules, {"hand": ["T042"], "mana": ["T001", "T001", "T001"], "deck": ["T005", "T003", "T001"]}, {})
    set_top(e, 0, ["T005", "T003", "T001"])   # 見える3枚: 対象は T005（火・コスト3）と T001（自然・コスト2）
    answer(e, "charge", "pass")
    answer(e, "main", "play:T042")
    d = e.advance()
    while d is not None and d["kind"] != "choose_cards":
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
        d = e.advance()
    assert d is not None
    assert len(d["options"]) == 2, [o["key"] for o in d["options"]]   # 対象は T005 と T001 の2枚
    pick = next(i for i, o in enumerate(d["options"]) if o["key"].startswith("deck:T005"))
    e.answer([pick])
    # 使ったカードが場に出て、残りも山札の下に置かれるまで進める
    drive_until(e, lambda: any(e.s.cards[c].defn == "T005" for c in e.bz_tops(0))
                and "T003" in [e.s.cards[c].defn for c in e.s.zones["deck"][0][-2:]])
    deck = e.s.zones["deck"][0]
    assert sorted(e.s.cards[c].defn for c in deck[-2:]) == ["T001", "T003"]   # 残り2枚は山札の下へ


def test_mekurade_decline_bottoms_all_looked(rules):
    e = setup(rules, {"hand": ["T042"], "mana": ["T001", "T001", "T001"], "deck": ["T005", "T003", "T001"]}, {})
    set_top(e, 0, ["T005", "T003", "T001"])
    top4 = e.s.zones["deck"][0][3]
    answer(e, "charge", "pass")
    answer(e, "main", "play:T042")
    d = e.advance()
    while d is not None and d["kind"] != "choose_cards":
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
        d = e.advance()
    assert d is not None
    e.answer([])   # 使わない（0枚）
    # 残り3枚の並び替え（order_cards）が出るので、先頭の指定どおりに置く
    drive_until(e, lambda: e.s.zones["deck"][0][0] == top4)
    deck = e.s.zones["deck"][0]
    assert [e.s.cards[c].defn for c in deck[-3:]] == ["T005", "T003", "T001"] or \
           sorted(e.s.cards[c].defn for c in deck[-3:]) == ["T001", "T003", "T005"]


def test_mekurade_use_is_summon_not_put(rules):
    """メクレイドで「使う」のは召喚（／詠唱）: 召喚によって出た時の誘発が働く。
    move で「出す」（reason: put）では summon イベント自体が発生しない。"""
    e = setup(rules, {"hand": ["T042"], "mana": ["T001", "T001", "T001"],
                      "deck": ["T043", "T003", "T001"]}, {})
    set_top(e, 0, ["T043", "T003", "T001"])
    hand0 = len(e.s.zones["hand"][0])
    answer(e, "charge", "pass")
    answer(e, "main", "play:T042")
    d = e.advance()
    while d is not None and d["kind"] != "choose_cards":
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
        d = e.advance()
    assert d is not None
    pick = next(i for i, o in enumerate(d["options"]) if o["key"].startswith("deck:T043"))
    e.answer([pick])
    drive_until(e, lambda: len(e.s.zones["hand"][0]) == hand0 + 1)   # 召喚時ドロー
    cid = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T043")
    assert e.s.cards[cid].entered_turn == 1   # 出たターン（＝召喚したターン）に召喚酔いの印が付く
