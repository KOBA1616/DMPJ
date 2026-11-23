"""Phase 4: エンコーダ／モデル／自己対戦の煙テスト。"""
import numpy as np
import pytest

from dmsim.ai.encode import GLOB, OPT_NUM, TOK_NUM, Vocab, encode_options, encode_state
from dmsim.ai.model import Model
from dmsim.ai.selfplay import collect_games, evaluate
from dmsim.cards.defs import load_rules
from dmsim.engine.core import Engine
from tools.bench_2p import load_deck


@pytest.fixture(scope="module", autouse=True)
def _full_cards():
    # conftest の DMSIM_SKIP_CONVERTED=1 を rules 読込より先に外す（定義順に実行される）
    import os
    saved = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    yield
    if saved is not None:
        os.environ["DMSIM_SKIP_CONVERTED"] = saved


@pytest.fixture(scope="module")
def rules():
    return load_rules()


@pytest.fixture(scope="module")
def deck():
    return load_deck("data/decks/saga.yaml")


def test_encode_shapes(rules, deck):
    vocab = Vocab(rules)
    eng = Engine.new_game(rules, [deck, deck], 3, 0)
    d = eng.advance()
    st = encode_state(eng, d["player"], vocab)
    assert st["tok_num"].shape[1] == TOK_NUM
    assert st["tok_defn"].shape[0] == st["tok_num"].shape[0] == st["tok_zone"].shape[0]
    assert st["glob"].shape == (GLOB,)
    op = encode_options(eng, d, vocab)
    assert op["opt_num"].shape == (len(d["options"]), OPT_NUM)
    assert op["min"] == d["min"] and op["max"] == d["max"]


def test_model_act_and_grads(rules, deck):
    vocab = Vocab(rules)
    model = Model(len(vocab), seed=1)
    batch, winners = collect_games(rules, vocab, model, deck, deck, games=2, seed=5)
    assert len(batch) > 50  # 2局で100超の決定がある
    assert all(w in (0, 1) for w in winners)
    loss, grads = model.loss_and_grads(batch[:32])
    assert np.isfinite(loss)
    assert all(np.isfinite(g).all() for g in grads.values())
    model.step(grads)
    choice, logp, value = model.act(batch[0]["st"], batch[0]["op"],
                                    np.random.default_rng(0))
    assert len(choice) >= batch[0]["op"]["min"]
    assert np.isfinite(logp) and np.isfinite(value)


def test_evaluate_returns_rate(rules, deck):
    vocab = Vocab(rules)
    model = Model(len(vocab), seed=2)
    r = evaluate(rules, vocab, model, deck, deck, games=2, seed=77)
    assert r["games"] == 2
    assert 0.0 <= r["win_rate"] <= 1.0
    assert r["wins"] + r["losses"] + r["draws"] == 2


def test_model_save_load(rules, tmp_path):
    vocab = Vocab(rules)
    model = Model(len(vocab), seed=3)
    path = str(tmp_path / "m.npz")
    model.save(path)
    m2 = Model.load(path)
    for k in model.p:
        assert np.allclose(model.p[k], m2.p[k])


def test_evaluate_vs_greedy(rules, deck):
    vocab = Vocab(rules)
    model = Model(len(vocab), seed=4)
    r = evaluate(rules, vocab, model, deck, deck, games=2, seed=78, opponent="greedy")
    assert r["opponent"] == "greedy"
    assert r["wins"] + r["losses"] + r["draws"] == 2


def test_attn_model_train_step(rules, deck):
    from dmsim.ai.model_attn import AttnModel
    from dmsim.ai.selfplay import collect_games_parallel
    vocab = Vocab(rules)
    model = AttnModel(len(vocab), seed=6)
    batch, winners = collect_games(rules, vocab, model, deck, deck, games=1, seed=9)
    loss, grads = model.loss_and_grads(batch[:16])
    assert np.isfinite(loss)
    assert "attn_q" in grads and np.isfinite(grads["attn_q"]).all()
    model.step(grads)
    # 並列収集（attn のパラメータ引き継ぎ）
    b2, w2 = collect_games_parallel(rules, vocab, model, deck, deck, games=2,
                                    seed=3, workers=2)
    assert len(w2) == 2 and len(b2) > 50
