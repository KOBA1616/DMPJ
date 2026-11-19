"""第243弾: rush op + 終極宣言の無トリガー召喚（dm23ex3-or2 の形）。"""
from tests.conftest import setup


def _rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def test_final_declaration_no_trigger_summon_and_rush():
    # T659 が場にあり、墓地に T660（出た時ドローのアビス）。ターン開始に宣言できる
    e = setup(_rules(), {"bz": ["T659"], "graveyard": ["T660"], "hand": ["T001"]}, {"bz": ["T002"]})
    t660 = next(c for c in e.zlist("graveyard", 0) if e.s.cards[c].defn == "T660")
    h0 = len(e.zlist("hand", 0))
    declared = summoned = False
    attack_keys = []
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "yes_no":   # 宣言の may
            e.answer([0])
            declared = True
        elif d["kind"] == "choose_cards" and keys:
            e.answer([0])           # T660 を選ぶ
        elif d["kind"] == "attack":
            attack_keys = keys
            break
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if t660 in e.zlist("bz", 0):
            summoned = True
    assert declared and summoned
    # 出た時ドローはトリガーしない（手札は宣言前と同数のはず: チャージ等をしていない前提で増えていない）
    assert len(e.zlist("hand", 0)) == h0
    # rush: 出たターンでもプレイヤーは攻撃できるが、クリーチャーは攻撃できない
    assert "attack:T660:player" in attack_keys
    assert not any(k.startswith("attack:T660:T002") for k in attack_keys)
