"""語彙パイロット第11弾（2026-10-31）の検証。

キリフダッシュ（rejects: kirifudash）: 攻撃の終わりに、その攻撃でシールドをブレイクして
いれば、手札のこのカードを代替コストで召喚してもよい。
- 新イベント attack_end（when の broke: true で「その攻撃中にブレイクした」を指定）
- op play_self {cost, civs?} が代替コストの play を積む
"""
from conftest import answer, setup


def drive_attack(e, want_kirifudash):
    """攻撃を宣言し、キリフダッシュの確認が出たら yes と答える。確認が出たかを返す。"""
    seen = False
    for _ in range(40):
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if "yes" in keys:
            seen = True
            e.answer([keys.index("yes") if want_kirifudash else keys.index("no")])
        elif d["kind"] == "pay_mana":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        if any(e.s.cards[c].defn == "T046" for c in e.bz_tops(0)):
            break
        if d["kind"] == "charge":   # 次のターンに入ったら打ち切る
            break
    return seen


def test_kirifudash_after_break(rules):
    e = setup(rules, {"bz": ["T001"], "hand": ["T046"], "mana": ["T005"]}, {})
    answer(e, "charge", "pass")
    d = e.advance()
    assert d is not None and d["kind"] == "attack"
    e.answer([[o["key"] for o in d["options"]].index("attack:T001:player")])
    assert drive_attack(e, True) is True
    assert any(e.s.cards[c].defn == "T046" for c in e.bz_tops(0))     # 代替コスト1で召喚された
    assert e.s.cards[e.s.zones["mana"][0][0]].tapped                # 火マナを払った


def test_kirifudash_not_offered_without_break(rules):
    e = setup(rules, {"bz": ["T001"], "hand": ["T046"], "mana": ["T005"]},
              {"bz": ["T004"]})                                        # 相手はブロッカー
    answer(e, "charge", "pass")
    d = e.advance()
    assert d is not None and d["kind"] == "attack"
    e.answer([[o["key"] for o in d["options"]].index("attack:T001:player")])
    # ブロックされてブレイクしないので、キリフダッシュの確認は出ない
    assert drive_attack(e, True) is False
    assert not any(e.s.cards[c].defn == "T046" for c in e.bz_tops(0))
