"""Phase 10: torch 版モデル（model_torch）の検証。torch が無い環境では skip。

- numpy 版 Model と同じ重みで loss と勾配が一致すること（意味論のパリティ）
- act が妥当な選択を返すこと、save/load の往復、train_iters で学習が回ること
"""
import os
import random

import numpy as np
import pytest

torch = pytest.importorskip("torch")


@pytest.fixture(scope="module", autouse=True)
def _full_rules():
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    yield
    if old is not None:
        os.environ["DMSIM_SKIP_CONVERTED"] = old


@pytest.fixture(scope="module")
def env():
    from dmsim.cards.defs import load_rules
    from dmsim.ai.encode import Vocab
    from tools.bench_2p import load_deck
    rules = load_rules()
    return rules, Vocab(rules), load_deck("data/decks/saga.yaml")


def _batch(rules, vocab, model, deck, games=2, seed=3):
    from dmsim.ai.selfplay import collect_games
    batch, _ = collect_games(rules, vocab, model, deck, deck, games, seed=seed)
    return batch


def test_torch_matches_numpy_loss_and_grads(env):
    from dmsim.ai.model import Model
    from dmsim.ai.model_torch import TorchModel
    rules, vocab, deck = env
    np_model = Model(len(vocab), seed=7)
    batch = _batch(rules, vocab, np_model, deck)
    assert batch
    t_model = TorchModel(len(vocab), seed=99)
    with torch.no_grad():
        for k, v in np_model.p.items():
            t_model.t[k].copy_(torch.as_tensor(v))
    loss_np, grads_np = np_model.loss_and_grads(batch)
    loss_t, grads_t = t_model.loss_and_grads(batch)
    assert abs(loss_np - loss_t) < 1e-3 * max(1.0, abs(loss_np))
    for k in grads_np:
        assert np.allclose(grads_np[k], grads_t[k], atol=1e-4), k


def test_torch_act_and_save_load(env, tmp_path):
    from dmsim.ai.model_torch import TorchModel
    rules, vocab, deck = env
    m = TorchModel(len(vocab), seed=1)
    batch = _batch(rules, vocab, m, deck, games=1)
    assert batch  # act が妥当な選択を返して対戦が進んだ
    path = str(tmp_path / "m.npz")
    m.save(path)
    m2 = TorchModel.load(path)
    for k in m.t:
        assert torch.equal(m.t[k].detach(), m2.t[k].detach())
    # numpy 版でも読み込める（保存形式が同一）
    from dmsim.ai.model import Model
    nm = Model.load(path)
    assert np.allclose(nm.p["emb"], m.p["emb"])


def test_torch_train_iters_runs(env):
    from dmsim.ai.model_torch import TorchModel
    from dmsim.ai.selfplay import train_iters
    rules, vocab, deck = env
    m = TorchModel(len(vocab), seed=0)
    hist = train_iters(rules, vocab, m, deck, deck, iters=2, games_per_iter=2,
                       seed=0, log=lambda *a: None)
    assert len(hist) == 2 and all(np.isfinite(h["loss"]) for h in hist)
