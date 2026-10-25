"""koba の一連の筋（タイフーン→サガ→手札通過でドラゲリオンを引く→山札2枚でイザナギ→コダマダンス→ドラゲリオン→勝ち）を
台本で再現する。台本は tools/loopcheck_full_chain.py。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from loopcheck_full_chain import trial  # noqa: E402


@pytest.mark.parametrize("pos", [(0, 1, 2), (3, 5, 7), (6, 9, 12)])
def test_full_chain_wins_by_replacement(rules, pos):
    e = trial(rules, pos)
    assert e.s.result and e.s.result["winner"] == 0 and e.s.result["reason"] == "effect"


def test_izanagi_free_cast_uses_the_spell_face_of_a_twinpact(rules):
    """イザナギの「コスト3以下の呪文を唱える」は、ツインパクトの呪文面で唱える（ブルースの呪文面で墓地のサガを出す）。
    サガ→蘇生でイザナギ→手札のブルース呪文面を踏み倒す→墓地のサガを出す→サガが再び場に出る（導入）。"""
    import loopcheck_full_chain as L
    from dmsim import scenario as sc
    BRUCE = "dmbd17-009"

    def pol(eng, d):
        keys = [o["key"] for o in d["options"]]
        dn = lambda o: eng.s.cards[o["cid"]].defn
        if d["kind"] == "main":
            j = next((j for j, o in enumerate(d["options"]) if o["key"] == "play:" + L.SAGA), None)
            return [j] if j is not None else [keys.index("pass")]
        if d["kind"] == "choose_cards" and eng.s.cards[d["options"][0]["cid"]].zone == "graveyard":
            names = [dn(o) for o in d["options"]]
            for w in (L.IZA, L.SAGA):
                if w in names:
                    return [names.index(w)]
        return L.policy(eng, d)

    spec = {"p0": {"hand": [L.SAGA, BRUCE, L.IZA], "mana": ["dm01-027", "dm01-027", "dm01-080"], "graveyard": ["T001"] * 3,
                   "deck": [L.DRAG, L.IWA, L.SHAKO, L.KODAMA]}, "p1": {}, "deck_size": 40, "deck_left": [20, 40], "seed": 1}
    e = sc.build(rules, spec)
    sagas_entered = 0
    for _ in range(60):
        d = e.advance()
        if d is None or e.s.result:
            break
        e.answer(pol(e, d))
        sagas_entered = max(sagas_entered, sum(1 for c in e.s.zones["bz"][0] if e.s.cards[c].defn == L.SAGA))
        if any(e.s.cards[c].defn == BRUCE for c in e.s.zones["graveyard"][0]) and sagas_entered:
            break
    bz = [e.s.cards[c].defn for c in e.s.zones["bz"][0]]
    gy = [e.s.cards[c].defn for c in e.s.zones["graveyard"][0]]
    assert BRUCE in gy and BRUCE not in bz     # 呪文面で唱えたので墓地へ（クリーチャーとして出ていない）
