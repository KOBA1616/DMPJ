"""語彙パイロット第45弾（フェーズ17-6）: 無月の門（mugon_gate 単独18件）。

表現: 手札/墓地で機能する誘発型能力（zone: hand と zone: graveyard の2つ）＋ op: summon_on。
- when は「自分の魔導具が出た時」、if で下に重ねる枚数の実現可能性を門番する
- summon_on は parts（ゾーンごとの枚数とフィルタ）どおりに選ばせ、移動イベントの
  stack_on / stack_more で重ねて召喚する。召喚酔いとタップ状態は通常の召喚どおり
  （summon_on_fix が進化用の _stack の副作用を直す）
"""
from conftest import answer, setup


def _play_madogu_and_drive(e):
    """手札の試作魔導具（T127）を出し、無月の門の解決まで進める。"""
    answer(e, "charge", "pass")
    d = e.advance()
    keys = [o["key"] for o in d["options"]]
    e.answer([keys.index("play:T127")])
    log = []
    for _ in range(60):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        log.append(d["kind"])
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "may":
            e.answer([keys.index("yes") if "yes" in keys else 0])
            continue
        if d["kind"] == "summon_on":
            e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "order_pending":
            e.answer([0])
            continue
        if d["kind"] in ("attack",) or (d["kind"] == "charge" and d["player"] == 1):
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return log


def _gate(e):
    tops = [c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T126"]
    return tops[0] if tops else None


def test_mugon_summon_from_hand(rules):
    """手札の門番が、魔導具が出た時に 2+2 の上に無償召喚される。"""
    e = setup(rules, {"bz": ["T127", "T127"], "graveyard": ["T127", "T127"],
                      "hand": ["T126", "T127"], "mana": ["T127", "T127"]}, {})
    _play_madogu_and_drive(e)
    g = _gate(e)
    assert g is not None
    assert len(e.s.cards[g].under) == 4                       # 選んだ4枚が下に重なっている
    assert e.s.cards[g].tapped is False                       # タップして出ない
    assert e.s.cards[g].entered_turn != -1                    # 通常の召喚として召喚酔いする（進化と違い -1 にならない）


def test_mugon_summon_from_graveyard(rules):
    """墓地にある門番も同じように召喚できる。"""
    e = setup(rules, {"bz": ["T127", "T127"], "graveyard": ["T127", "T127", "T126"],
                      "hand": ["T127"], "mana": ["T127", "T127"]}, {})
    _play_madogu_and_drive(e)
    g = _gate(e)
    assert g is not None
    assert len(e.s.cards[g].under) == 4


def test_mugon_follower_enters_tapped(rules):
    """無月の門を使った時、追随者が墓地からタップして出る（mugon_used イベント）。"""
    e = setup(rules, {"bz": ["T127", "T127"], "graveyard": ["T127", "T127", "T128"],
                      "hand": ["T126", "T127"], "mana": ["T127", "T127"]}, {})
    _play_madogu_and_drive(e)
    fol = [c for c in e.zlist("bz", 0) if e.s.cards[c].defn == "T128"]
    assert len(fol) == 1
    assert e.s.cards[fol[0]].tapped is True


def test_mugon_needs_full_parts(rules):
    """墓地の魔導具が足りなければ門は開かない（誘発の if で門番）。"""
    e = setup(rules, {"bz": ["T127", "T127"], "graveyard": ["T127"],
                      "hand": ["T126", "T127"], "mana": ["T127", "T127"]}, {})
    _play_madogu_and_drive(e)
    assert _gate(e) is None
    assert any(e.s.cards[c].defn == "T126" for c in e.zlist("hand", 0))
