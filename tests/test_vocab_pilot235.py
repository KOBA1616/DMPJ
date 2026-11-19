"""第235弾: キズナコンプ（use_partner の any_number で [P] を好きな数使う）。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _attack_with_comp(e, plan, max_steps=160):
    """T637 で攻撃し、use_partner の提示に plan（使う defn の並び）どおり答える。"""
    plan = list(plan)
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and any(k.startswith("attack:T637") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("attack:T637"))])
        elif d["kind"] == "use_partner":
            if plan:
                want = plan.pop(0)
                e.answer([next(i for i, k in enumerate(keys) if want in k)])
            else:
                e.answer([])          # もう使わない
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        # 攻撃が終わる（次のチャージ/相手ターン）まで回したら十分
        if e.s.turn >= 2:
            return


def test_comp_uses_two_partners():
    e = setup(_rules(), {"bz": ["T637", "T638"]}, {"bz": ["T002"]})
    hand_before = len(e.zlist("hand", 0))
    _attack_with_comp(e, ["T638", "T637"])   # ドロー → 破壊 の順に使う
    assert len(e.zlist("hand", 0)) == hand_before + 1       # T638 の [P] で1ドロー
    assert "T002" in _defns(e, "graveyard", 1)              # T637 の [P] で破壊


def test_comp_decline_uses_none():
    e = setup(_rules(), {"bz": ["T637", "T638"]}, {"bz": ["T002"]})
    hand_before = len(e.zlist("hand", 0))
    _attack_with_comp(e, [])
    assert len(e.zlist("hand", 0)) == hand_before
    assert "T002" in _defns(e, "bz", 1)


def test_no_comp_no_partner_offer():
    # コンプを持たない T638 の攻撃では [P] の提示は出ない
    e = setup(_rules(), {"bz": ["T638"]}, {})
    seen = []
    for _ in range(40):
        d = e.advance()
        assert d is not None
        seen.append(d["kind"])
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and any(k.startswith("attack:T638") for k in keys):
            e.answer([next(i for i, k in enumerate(keys) if k.startswith("attack:T638"))])
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if e.s.turn >= 2:
            break
    assert "use_partner" not in seen
