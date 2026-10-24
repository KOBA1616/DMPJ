"""絶望神サガループを、手で方策を書かずに1人回しAIが見つけられるかの検証。

test_saga_loop.py は手書きの方策でループを回す試験。ここは次の3つを確かめる:
1. 検出器がサガの周回（山札-1・墓地+1）を骨格の回帰として見つけ、再生で確かめられる
2. 1人回しAI（TurnSearch）が、ループを山札1枚まで削り、ドラゲリオン→シャコガイルの置換勝利まで自力で辿り着く
3. 部品を固定して残りを探す combo_search が、欠けた1枚（ドラゲリオン）を見つける
"""
from pathlib import Path

import yaml

from dmsim import scenario as sc
from dmsim.combo_search import search_setup
from dmsim.loop import LoopDetector, is_burn, verify
from dmsim.solitaire import play_game

from test_saga_loop import DRAG, IWASHIN, SAGA, SHAKO, saga_policy

MANA = ["dm01-080", "dm01-080", "dm01-027"]


def spec(deck_left, **p0):
    base = {"hand": [SAGA, "T001", "T001", "T001", "T001", "T001"], "mana": MANA,
            "graveyard": [SAGA, "T001", "T001", "T001"]}
    return {"p0": {**base, **p0}, "p1": {}, "deck_size": 40, "deck_left": [deck_left, 40], "seed": 1}


def test_detector_sees_saga_cycle(rules):
    eng = sc.build(rules, spec(10))
    det = LoopDetector(me=0, period="in_turn", report_all=True)
    cert = None
    while cert is None:
        d = eng.advance()
        cert = det.observe(eng)
        if cert is None:
            eng.answer(saga_policy(eng, d))
    assert cert.delta == {"deck:0": -1, "graveyard:0": 1}
    assert is_burn(cert.delta, 0)
    assert not cert.win_by                       # 山札を削るだけでは勝ちにならない
    assert verify(eng, cert, times=2).verified == 2


def test_ai_takes_replacement_win_with_shakogairu_on_board(rules):
    eng = sc.build(rules, spec(30, bz=[SHAKO]))
    res, _ = play_game(rules, None, None, 1, max_turn=1, start=eng, lock_rounds=0)
    assert (res.kind, res.kill_turn) == ("effect", 1)
    assert any(lp["kind"] == "burn" for lp in res.loops)   # ループとして山札を削ってから決めた


def test_ai_does_not_deck_itself_without_a_payoff(rules):
    eng = sc.build(rules, spec(30))
    res, e = play_game(rules, None, None, 1, max_turn=1, start=eng, lock_rounds=0)
    assert res.lost is None and res.error is None
    assert len(e.s.zones["deck"][0]) > 1


def test_ai_finds_dragellion_route_from_the_hand(rules):
    """サガ→山札を1枚まで削る→ドラゲリオン（墓地から超無限進化）→メテオバーンでシャコガイル→イワシンで最後のドロー。"""
    eng = sc.build(rules, spec(35, hand=[SAGA, DRAG, "T001", "T001", "T001", "T001"],
                               graveyard=[SAGA, IWASHIN, SHAKO] + ["T001"] * 12))
    res, e = play_game(rules, None, None, 1, max_turn=1, start=eng, lock_rounds=0, budget=2500)
    assert (res.kind, res.kill_turn) == ("effect", 1)
    assert len(e.s.zones["deck"][0]) == 1


def test_combo_search_finds_the_missing_piece(rules):
    setup = yaml.safe_load((Path(__file__).parent / "saga_setup.yaml").read_text(encoding="utf-8"))
    pool = [DRAG, "T001", "dm01-027", "dm01-080", SAGA]
    res = search_setup(rules, setup, "hand", pool, slots=1, turns=1, games=1, budget=400)
    assert res[0].extra == (DRAG,) and res[0].rate == 1.0
    assert all(c.rate == 0.0 for c in res[1:])
