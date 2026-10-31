"""語彙パイロット第14弾（2026-10-31）の検証。

スマッシュ・バースト（rejects: smash_burst）: op cast_face {face} を新規実装した。
ツインパクトのクリーチャーが攻撃する時、カードをバトルゾーンに置いたまま
呪文面をコストを支払わずに唱えられる。カードは動かず、墓地にも行かない。
"""
from conftest import setup


def test_smash_burst_casts_spell_face_in_place(rules):
    e = setup(rules, {"bz": ["T001", "T051"], "hand": []}, {"shield": ["T003"]})
    atk = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T051")
    hand0 = len(e.zlist("hand", 0))
    burst_asked = False
    for _ in range(20):
        if burst_asked and len(e.zlist("hand", 0)) == hand0 + 1:
            break
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and "attack:T051:player" in keys:
            e.answer([keys.index("attack:T051:player")])
        elif d["kind"] == "yes_no":
            burst_asked = True
            e.answer([keys.index("yes")])      # 唱える
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert burst_asked                                       # 攻撃時に唱えるか聞かれた
    assert len(e.zlist("hand", 0)) == hand0 + 1              # 呪文面の効果（1ドロー）が解決した
    assert e.s.cards[atk].zone == "bz"                       # カードはバトルゾーンに残る
    assert atk not in e.zlist("graveyard", 0)                # 墓地には行かない
