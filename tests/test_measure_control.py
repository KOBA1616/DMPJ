"""測定器の陽性対照（docs/measurement-tiers.md）。既知コンボを正しく測れていることを、新しい測定器ごとに確かめる。
1) 到達層: 厳密計算の素引き確率が、小さな例で全列挙と一致する。
2) 到達層の実測: 追加のドロー効果が無いコンボ（knight_dmc）の通常の開幕の実測が、計算値とほぼ一致する。
3) 実行層: 既知コンボ（knight_dmc）は仕込み済み開始から4ターン以内にほぼ必ずキルでき、連続スコアが通常の開幕より明確に高い。"""
import itertools
import os
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from dmsim.eval.reach import cards_ceiling, reach_prob  # noqa: E402


def test_reach_prob_matches_enumeration():
    deck = ["A", "A", "B", "X", "X", "X"]
    for need, n in (({"A": 1}, 2), ({"A": 2, "B": 1}, 4), ({"A": 1, "B": 1}, 3)):
        hit = tot = 0
        for comb in itertools.combinations(range(len(deck)), n):
            tot += 1
            c = [deck[i] for i in comb]
            hit += all(c.count(k) >= v for k, v in need.items())
        assert abs(reach_prob(deck, need, n) - hit / tot) < 1e-12
    assert reach_prob(deck, {"A": 3}, 6) == 0.0


@pytest.fixture(scope="module")
def knight():
    import exec_tier
    from dmsim.autofix import Knobs, Rule, harness_measure
    from dmsim.autofix.batch import default_board, default_need
    from dmsim.autofix.tune import _score
    from dmsim.cards.defs import load_rules
    from dmsim.eval.progress import ProgressSpec
    from dmsim.search.leaf_parts import load_specs
    from dmsim.eval.measure import load_deck
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)     # 実カード（converted.yaml 含む）が要る。他のテストへ影響しないよう戻す
    try:
        rules = load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old
    combos = {c["id"]: c for c in yaml.safe_load((ROOT / "data/known_combos/combos.yaml").read_text(encoding="utf-8"))["combos"]}
    t = next(x for x in yaml.safe_load((ROOT / "data/autofix/targets.yaml").read_text(encoding="utf-8"))["targets"] if x["combo"] == "knight_dmc")
    c, deck = combos["knight_dmc"], load_deck(t["deck"])
    need = default_need(c)
    out = {"ceil": cards_ceiling(deck, need, 4)}
    for label, cold in (("cold", True), ("exec", False)):
        spec, _ = exec_tier.exec_spec(rules, t, deck, cold=cold)
        m = harness_measure(rules, deck, ["T001"] * 40, list(range(1, 9)), spec, ProgressSpec(board=default_board(c), cards=need),
                            load_specs()["knight_dmc"], max_turn=4)(Knobs())
        n = len(m["kill"])
        out[label] = {"kill": sum(x is not None and x <= 4 for x in m["kill"]) / n, "cards": sum(x is not None and x <= 4 for x in m["cards"]) / n,
                      "score": sum(_score(m, Rule())) / n}
    return out


def test_cold_reach_matches_analytic(knight):
    assert abs(knight["cold"]["cards"] - knight["ceil"]) < 0.3      # 16局の二項ゆらぎ(2σ≈0.24)を見込んだ許容


def test_exec_tier_positive_control(knight):
    assert knight["exec"]["kill"] >= 0.9
    assert knight["exec"]["score"] > knight["cold"]["score"] + 1.0
