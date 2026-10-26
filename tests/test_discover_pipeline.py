"""discover_pipeline のマクロ／ミクロ分離の検証。

重い探索は回さず、学習の計算と狙いの切り替えだけを確かめる。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from discover_pipeline import (MacroPlanner, MicroPolicy, classify_win,  # noqa: E402
                               deck_bucket, learn_preferences)

from conftest import setup  # noqa: E402

SAGA, SHAKO, DRAG, IWA = "dm22ex2-021", "dmrp03-s03", "dm22ex1-007", "dmrp03-036"
MANA = ["dm01-080", "dm01-080", "dm01-027"]


def test_learn_preferences_rates():
    records = (
        [{"kind": "choose_cards", "options": ["a", "b"], "chosen": ["a"]}] * 3
        + [{"kind": "choose_cards", "options": ["a", "b"], "chosen": ["b"]}]
        + [{"kind": "main", "options": ["play:x"], "chosen": ["play:x"]}]  # 出現1回は捨てる
    )
    pref = learn_preferences(records)
    assert pref["global"]["choose_cards"]["a"] == 0.75
    assert pref["global"]["choose_cards"]["b"] == 0.25
    assert pref["global"]["main"] == {}


def test_learn_preferences_by_bucket():
    records = (
        [{"kind": "choose_cards", "options": ["a", "b"], "chosen": ["a"], "bucket": "thick"}] * 3
        + [{"kind": "choose_cards", "options": ["a", "b"], "chosen": ["b"], "bucket": "thin"}] * 3
    )
    pref = learn_preferences(records)
    assert pref["by_bucket"]["thick"]["choose_cards"]["a"] == 1.0
    assert pref["by_bucket"]["thin"]["choose_cards"]["b"] == 1.0
    assert deck_bucket(5) == "thin" and deck_bucket(12) == "mid" and deck_bucket(30) == "thick"


def test_micro_prefers_learned_key():
    micro = MicroPolicy({"main": {"play:x": 0.9, "pass": 0.1}})   # v1 形式も読める
    d = {"kind": "main", "player": 0, "min": 1, "max": 1,
         "options": [{"key": "pass"}, {"key": "play:x"}]}
    assert micro.prefer(None, d) == [1]


def test_macro_intent_transitions(rules):
    macro = MacroPlanner()
    # 部品なし → 整える（山札を守る設定になっている）
    eng = setup(rules, {"hand": ["T001"], "mana": MANA, "graveyard": []})
    intent = macro.plan(eng)
    assert intent.name == "setup" and intent.burn_stock is False
    # サガが手札にあっても、墓地の準備がなければまだ整える
    eng = setup(rules, {"hand": [SAGA], "mana": MANA, "graveyard": []})
    assert macro.plan(eng).name == "setup"
    # 起点＋墓地の準備＋闇マナ → ループ導入
    eng = setup(rules, {"hand": [SAGA], "mana": MANA, "graveyard": [SAGA]})
    assert macro.plan(eng).name == "enter_loop"
    # キル部品が揃い山札が薄い → リーサル実行
    eng = setup(rules, {"hand": [SAGA, DRAG], "mana": MANA, "graveyard": [IWA, SHAKO]},
                deck_left=[6, 20])
    assert macro.plan(eng).name == "execute"


def test_classify_win():
    assert classify_win("opp_deck_out") == "opp_deck_out"
    assert classify_win("shield_zero") == "shield_zero"
    assert classify_win(None, verified=True) == "effect"     # 置換勝利など効果で勝つ
    assert classify_win(None, verified=False) == "resource"


def test_learn_preferences_by_context_win_by():
    records = (
        [{"kind": "choose_cards", "options": ["a", "b"], "chosen": ["a"],
          "bucket": "thin", "win_by": "effect"}] * 3
        + [{"kind": "choose_cards", "options": ["a", "b"], "chosen": ["b"],
            "bucket": "thin", "win_by": "shield_zero"}] * 3
    )
    pref = learn_preferences(records)
    # 同じ山札の厚さでも、勝ち方が違えば文脈ごとの選好は分かれる
    assert pref["by_context"]["effect|thin"]["choose_cards"]["a"] == 1.0
    assert pref["by_context"]["shield_zero|thin"]["choose_cards"]["b"] == 1.0
    assert MicroPolicy(pref, win_by="effect").win_by == "effect"


def test_macro_bruce_route_enters_loop_without_grave_prep(rules):
    # サガ1枚でも、イザナギ（掘る役）とブルース（戻す呪文面）が手札にあれば導入へ
    eng = setup(rules, {"hand": [SAGA, "dmbd17-009", "dm22ex1-025"],
                        "mana": MANA, "graveyard": ["T001"] * 3})
    intent = MacroPlanner().plan(eng)
    assert intent.name == "enter_loop" and "ブルース" in intent.note


def test_micro_context_overrides_by_win_by(rules):
    # 山札が薄い局面で、勝ち方が違えば同じ決定でも選好が逆転する
    records = (
        [{"kind": "choose_cards", "options": ["a", "b"], "chosen": ["a"],
          "bucket": "thin", "win_by": "effect"}] * 3
        + [{"kind": "choose_cards", "options": ["a", "b"], "chosen": ["b"],
            "bucket": "thin", "win_by": "shield_zero"}] * 3
    )
    pref = learn_preferences(records)
    eng = setup(rules, {"hand": ["T001"], "mana": MANA, "graveyard": []}, deck_left=[5, 20])
    d = {"kind": "choose_cards", "player": 0, "min": 1, "max": 1,
         "options": [{"key": "a"}, {"key": "b"}]}
    assert MicroPolicy(pref, win_by="effect").prefer(eng, d) == [0]
    assert MicroPolicy(pref, win_by="shield_zero").prefer(eng, d) == [1]


def test_macro_setup_protects_deck_only_for_effect_win(rules):
    # 置換勝利（effect）: 自分の山札が命綱なので setup で守る
    eng = setup(rules, {"hand": ["T001"], "mana": MANA, "graveyard": []})
    eff = MacroPlanner(win_by="effect").plan(eng)
    assert eff.name == "setup" and eff.burn_stock is False and eff.weights.deck_keep == 18
    # 相手を削る型: 自分の山札の消耗は許す
    opp = MacroPlanner(win_by="opp_deck_out").plan(eng)
    assert opp.name == "setup" and opp.burn_stock is True and opp.weights.deck_keep == 2
    # 特徴にも勝ち方が入る
    assert MacroPlanner(win_by="shield_zero").features(eng)["win_by"] == "shield_zero"


def test_micro_candidates_without_pipeline_no_recursion():
    """MicroPolicy を Pipeline を経ずに差し込んでも再帰しない（v1 の不具合の回帰防止）。"""
    import dmsim.solitaire as sol
    micro = MicroPolicy({"main": {"play:x": 0.9, "pass": 0.1}})
    d = {"kind": "main", "player": 0, "min": 1, "max": 1,
         "options": [{"key": "pass"}, {"key": "play:x"}]}
    orig = sol.candidates
    sol.candidates = micro.candidates
    try:
        out = micro.candidates(None, d, None)
    finally:
        sol.candidates = orig
    assert out[0] == [1]
