"""自立発見ランナー（dmsim/discovery/auto.py）: 簡単な種盤面から勝ちを見つけ、検証・縮約して保存し、同じ盤面は重複させない。"""
import json

import pytest

from dmsim import load_rules, scenario
from dmsim.discovery.auto import AutoConfig, mutate, run
from dmsim.discovery.loopspec import LoopSpec

AL, EM, HG = "dmx12b-031", "dm23bd7-022", "dm16-007"
SEED = {"p0": {"hand": [EM, "T013"], "bz": [AL], "mana": [HG] * 4 + ["dm01-080"], "shield": ["T013"] * 9}, "p1": {"bz": ["T001"]},
        "filler": "T013", "seed": 1, "deck_size": 10}


def test_runner_saves_a_verified_loopspec_and_dedups(tmp_path):
    rules = load_rules()
    cfg = AutoConfig(pool=[EM, AL, HG], seeds=[SEED, json.loads(json.dumps(SEED))], width=50, rate_seeds=3, seconds=8, out_dir=tmp_path)
    stats = run(rules, cfg, log=lambda *_: None)
    files = sorted(tmp_path.glob("*.json"))
    assert stats["wins"] >= 2 and len(files) >= 1 and stats["dups"] >= 1       # 同じ盤面は署名で重複排除
    ls = LoopSpec.from_json(files[0].read_text())
    assert ls.source["auto"] and ls.source["win_rate"] == 1.0 and ls.kind == "deterministic"
    assert not scenario.deck_limit_violations(rules, ls.source["board"])


def test_runner_rejects_a_seed_board_over_the_four_copy_limit(tmp_path):
    bad = {"p0": {"hand": [EM] * 5}, "p1": {}, "filler": "T013"}
    with pytest.raises(ValueError):
        run(load_rules(), AutoConfig(pool=[EM], seeds=[bad], seconds=1, out_dir=tmp_path), log=lambda *_: None)


def test_mutations_stay_inside_zone_limits():
    import random
    rules = load_rules()
    cfg = AutoConfig(pool=[EM, AL], seeds=[SEED])
    cfg.max_zone = dict(cfg.max_zone, shield=9)
    rng = random.Random(3)
    s = SEED
    for _ in range(200):
        s = mutate(s, cfg, rng, rules)
        assert all(len(v) <= cfg.max_zone[z] for z, v in s["p0"].items())


def test_deck_mode_finds_a_win_from_the_normal_opening_and_saves_it(tmp_path):
    from dmsim.discovery import replay
    from dmsim.discovery.auto import build_game, run_decks
    rules = load_rules()
    cfg = AutoConfig(pool=[], seeds=[{"deck": ["T001"] * 40}], filler="T013", width=60, eval_seeds=2, max_turn=14, seconds=1, out_dir=tmp_path)
    stats = run_decks(rules, cfg, log=lambda *_: None)
    assert stats["winning_decks"] >= 1 and len(list(tmp_path.glob("*.json"))) == 1
    ls = LoopSpec.from_json(next(tmp_path.glob("*.json")).read_text())
    b = ls.source["board"]
    assert len(b["deck"]) == 40 and b["first_player"] in (0, 1) and ls.source["mode"] == "deck"
    steps = [(k, tuple(keys), tuple(idx)) for k, keys, idx in ls.source["steps"]]
    assert replay.replay_test(rules, steps, build=build_game)(b)          # 保存した手順は通常の開幕から再生すると勝つ


def test_deck_mode_rejects_an_illegal_seed_deck(tmp_path):
    from dmsim.discovery.auto import run_decks
    with pytest.raises(ValueError):
        run_decks(load_rules(), AutoConfig(pool=[], seeds=[{"deck": [EM] * 40}], seconds=1, out_dir=tmp_path), log=lambda *_: None)
