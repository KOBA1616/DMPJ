"""discover_pipeline のマクロ／ミクロ分離の検証。

重い探索は回さず、学習の計算と狙いの切り替えだけを確かめる。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from discover_pipeline import MacroPlanner, MicroPolicy, learn_preferences  # noqa: E402

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
    assert pref["choose_cards"]["a"] == 0.75
    assert pref["choose_cards"]["b"] == 0.25
    assert pref["main"] == {}


def test_micro_prefers_learned_key():
    micro = MicroPolicy({"main": {"play:x": 0.9, "pass": 0.1}})
    d = {"kind": "main", "player": 0, "min": 1, "max": 1,
         "options": [{"key": "pass"}, {"key": "play:x"}]}
    assert micro.prefer(None, d) == [1]


def test_macro_intent_transitions(rules):
    macro = MacroPlanner()
    # 部品なし → 整える
    eng = setup(rules, {"hand": ["T001"], "mana": MANA, "graveyard": []})
    assert macro.plan(eng).name == "setup"
    # サガが手札にある → ループ導入
    eng = setup(rules, {"hand": [SAGA], "mana": MANA, "graveyard": []})
    assert macro.plan(eng).name == "enter_loop"
    # キル部品が揃い山札が薄い → リーサル実行
    eng = setup(rules, {"hand": [SAGA, DRAG], "mana": MANA, "graveyard": [IWA, SHAKO]},
                deck_left=[6, 20])
    assert macro.plan(eng).name == "execute"
