"""保存した天門(初期型)の LoopSpec: 手順を再生すると勝つ（エンジンの変更で壊れていないことの回帰テスト）。"""
from pathlib import Path

from dmsim import load_rules
from dmsim.eval import replay
from dmsim.base.loopspec import LoopSpec

PATH = Path(__file__).parent.parent / "data" / "loops" / "tenmon_initial.json"


def _prepare(e):
    ts, fa = "dm23ex2-cho018", "dm31-025"
    dk = e.s.zones["deck"][0]
    e.s.zones["deck"][0][:] = sorted(dk, key=lambda c: (e.s.cards[c].defn != ts, e.s.cards[c].defn != fa))


def test_saved_tenmon_loopspec_replays_to_a_win_and_respects_the_four_copy_limit():
    rules = load_rules()
    ls = LoopSpec.from_json(PATH.read_text())
    board = ls.source["board"]
    from dmsim.engine import scenario
    assert not scenario.deck_limit_violations(rules, board)
    steps = [(k, tuple(keys), tuple(idx)) for k, keys, idx in ls.source["steps"]]
    assert replay.replay_test(rules, steps, _prepare)(board)
    assert ls.kind == "reroll"          # オリーブオイルのシャッフルで引くカードが運に左右される
    assert 0.3 < ls.source["win_rate_same_line"] < 0.7   # 同じ手順が通るシードの割合（200シードで測った値）
    assert LoopSpec.from_json(ls.to_json()).minimal == ls.minimal
    assert any(p.zone == "shield" and p.n == 10 for p in ls.goal)
