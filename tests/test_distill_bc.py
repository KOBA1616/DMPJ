"""Phase 18: BC（模倣学習）損失のテスト。

- 損失と勾配が有限であること
- 価値ヘッド（wv2/bv2）に勾配が流れないこと（BC は価値に触れない）
- 解析勾配が数値勾配と一致すること
"""
import numpy as np
import pytest

from dmsim.ai.encode import Vocab
from dmsim.ai.model import Model
from dmsim.ai.selfplay import collect_games
from dmsim.cards.defs import load_rules
from tools.bench_2p import load_deck


@pytest.fixture(scope="module", autouse=True)
def _full_cards():
    import os
    saved = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    yield
    if saved is not None:
        os.environ["DMSIM_SKIP_CONVERTED"] = saved


@pytest.fixture(scope="module")
def batch(rules):
    vocab = Vocab(rules)
    model = Model(len(vocab), seed=1)
    deck = load_deck("data/decks/saga.yaml")
    items, _winners = collect_games(rules, vocab, model, deck, deck,
                                    games=1, seed=5)
    return items[:4]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_bc_loss_finite_and_value_head_untouched(batch):
    vocab_size = int(max(
        max(int(x) for x in it["st"]["tok_defn"]) for it in batch)) + 1
    model = Model(vocab_size, seed=2)
    loss, grads = model.bc_loss_and_grads(batch)
    assert np.isfinite(loss)
    assert all(np.isfinite(g).all() for g in grads.values())
    # BC は価値ヘッドに触れない
    assert not grads["wv2"].any() and not grads["bv2"].any()
    # 方策側には勾配が流れる（価値ヘッド以外に非ゼロがある）
    assert any(g.any() for k, g in grads.items() if k not in ("wv2", "bv2"))


def test_bc_grads_match_numerical(batch):
    vocab_size = int(max(
        max(int(x) for x in it["st"]["tok_defn"]) for it in batch)) + 1
    model = Model(vocab_size, seed=3)
    _loss, grads = model.bc_loss_and_grads(batch[:2])
    key, idx = "bk", (0,)
    orig = float(model.p[key][idx])
    eps = 1e-3
    model.p[key][idx] = orig + eps
    lp, _ = model.bc_loss_and_grads(batch[:2])
    model.p[key][idx] = orig - eps
    lm, _ = model.bc_loss_and_grads(batch[:2])
    model.p[key][idx] = orig
    num = (lp - lm) / (2 * eps)
    assert abs(num - float(grads[key][idx])) < 5e-2
