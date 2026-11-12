"""窓口 play_api（S3）と eval.api.run_eval（S4）の約束（ロードマップ P0-2）。"""
import pytest

from dmsim.defs import load_rules
from dmsim.eval.api import Candidate, EvalSettings, run_eval
from dmsim.play_api import API_VERSION, InfoLevel, PlayConfig, play
from dmsim.solitaire import play_game


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _deck(rules):
    ids = sorted(rules.cards)[:10]
    return tuple(i for i in ids for _ in range(4))


def test_default_is_fair_and_versioned():
    cfg = PlayConfig()
    assert cfg.version == API_VERSION
    assert play.__defaults__[0] is InfoLevel.FAIR
    with pytest.raises(ValueError):
        PlayConfig(mode="nope")


def test_same_input_same_output(rules):
    d = _deck(rules)
    cfg = PlayConfig(deck=d, opp_deck=("T001",) * 40, seed=3, max_turn=2, budget=20, n_det=2)
    a, b = play(None, cfg, rules=rules), play(None, cfg, rules=rules)
    assert (a.kill_turn, a.nodes, a.actions) == (b.kill_turn, b.nodes, b.actions)
    assert a.info is InfoLevel.FAIR and a.version == API_VERSION


def test_cheat_game_matches_play_game(rules):
    d = _deck(rules)
    cfg = PlayConfig(deck=d, opp_deck=("T001",) * 40, seed=5, max_turn=2, budget=20)
    r = play(None, cfg, InfoLevel.CHEAT, rules=rules)
    g, eng = play_game(rules, list(d), ["T001"] * 40, 5, max_turn=2, budget=20)
    assert (r.game.kill_turn, r.game.nodes, r.actions) == (g.kill_turn, g.nodes, list(eng.log))


def test_chain_and_beam_need_explicit_cheat(rules):
    from dmsim.engine.core import Engine
    e = Engine.new_game(rules, [list(_deck(rules)), ["T001"] * 40], 1, 0)
    with pytest.raises(NotImplementedError):
        play(e, PlayConfig(mode="beam", width=2, max_turn=1))
    r = play(e, PlayConfig(mode="beam", width=2, max_turn=1), InfoLevel.CHEAT)
    assert r.mode == "beam" and r.info is InfoLevel.CHEAT


def test_run_eval_uses_fair_cell(rules):
    st = EvalSettings(opp_deck=("T001",) * 40, levels=(InfoLevel.FAIR, InfoLevel.CHEAT), max_turn=2, base_budget=10, n_det=2,
                      register_fair=True)
    r = run_eval(rules, Candidate(deck=_deck(rules)), st, 1)
    assert r.cell_key == "d|fair|x1.0" and r.games == 2 and r.version == 1
    assert set(r.win_rate_by_turn) == {1, 2} and r.reproducibility is None
    from dmsim.eval import fair_runner
    fair_runner.register()
