"""語彙パイロット第6弾（2026-10-30）の検証。

opt_reduce の拡張: 支払い時の行動（do）を伴うコスト軽減（rejects: summon_time_cost）。
- do: {select, min, max, move_to?, shuffle?} … 「減らす」を選んだら、支払いの前に select で燃料を選ぶ。
  move_to があれば選んだカードをそこへ動かす（見せるだけなら move_to なし）。
- per: true なら軽減量は amount × 燃料の件数。floor で下限（「コストは１より少なくならない」）。
従来の then（ターン終了時の処理、B・A・D / J・O・E）はそのまま。
"""
from conftest import answer, setup


def drive(e, plan, limit=60):
    """plan: {decision_kind: [[answer keys or indices], ...]} 同じ種類の判断が続く場合はキューで順に使う。"""
    plan = {k: list(v) for k, v in plan.items()}
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        queue = plan.get(d["kind"])
        if not queue:
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
            continue
        want = queue.pop(0)
        ans = []
        for w in want:
            ans.append(keys.index(w) if isinstance(w, str) else w)
        e.answer(sorted(set(ans)))
        if not any(plan.values()):
            plan.clear()
        if not plan:
            # 残りは pass で流して召喚の解決まで進める
            for _ in range(limit):
                d = e.advance()
                if d is None or d["kind"] in ("main", "attack"):
                    return
                keys = [o["key"] for o in d["options"]]
                e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
            return
    raise AssertionError("drive did not finish")


def test_reveal_evolution_reduces_cost(rules):
    """手札の進化クリーチャーを見せると5→3で召喚できる。見せたカードは手札に残る。"""
    e = setup(rules, {"hand": ["T038", "T017"], "mana": ["T005", "T001", "T001"]}, {})
    answer(e, "charge", "pass")
    drive(e, {"main": [["play:T038"]], "choose_cards": [["reduce"]]})
    # 燃料の選択（進化クリーチャー）と支払いが自動で進み、場に出ている
    assert any(e.s.cards[c].defn == "T038" for c in e.bz_tops(0))
    assert any(e.s.cards[c].defn == "T017" for c in e.zlist("hand", 0))   # 見せただけ


def test_discard_reduces_cost(rules):
    """手札を1枚捨てると6→3で召喚できる。捨てたカードは墓地へ行く。"""
    e = setup(rules, {"hand": ["T039", "T002"], "mana": ["T001", "T001", "T001"]}, {})
    answer(e, "charge", "pass")
    drive(e, {"main": [["play:T039"]], "choose_cards": [["reduce"]]})
    assert any(e.s.cards[c].defn == "T039" for c in e.bz_tops(0))
    assert any(e.s.cards[c].defn == "T002" for c in e.zlist("graveyard", 0))


def test_per_card_reduction_with_floor(rules):
    """墓地の呪文を山札に戻した枚数だけ軽減（1枚につき-1、下限1）。"""
    e = setup(rules, {"hand": ["T040"], "mana": ["T010", "T001", "T001", "T001", "T001"],
                      "graveyard": ["T003", "T003", "T003"]}, {})
    answer(e, "charge", "pass")
    drive(e, {"main": [["play:T040"]], "choose_cards": [["reduce"], [0, 1]]})   # 呪文2枚を戻す → 7-2=5
    assert any(e.s.cards[c].defn == "T040" for c in e.bz_tops(0))
    left = [c for c in e.zlist("graveyard", 0) if e.s.cards[c].defn == "T003"]
    assert len(left) == 1                                                  # 2枚は山札へ戻った
