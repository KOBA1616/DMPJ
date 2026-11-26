"""Phase 13: 価値ヘッドの読み出し（state_value）と局面コーパスの煙テスト。"""
import os

import pytest

os.environ.setdefault("DMSIM_RUST", "0")

from dmsim.ai.demo import state_value  # noqa: E402
from dmsim.ai.encode import Vocab, encode_state  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402
from tools.leaf_compare import agreement, collect_positions  # noqa: E402
from dmsim.search.leaf_eval import Weights, evaluate  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _full_cards():
    saved = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    yield
    if saved is not None:
        os.environ["DMSIM_SKIP_CONVERTED"] = saved


@pytest.fixture(scope="module")
def rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


def test_state_value_in_range(rules):
    vocab = Vocab(rules)
    model = Model(len(vocab), seed=0)
    deck = load_deck("data/decks/saga.yaml")
    eng = Engine.new_game(rules, [deck, deck], 3, 0)
    eng.advance()
    v = state_value(model, encode_state(eng, 0, vocab))
    assert -1.0 <= v <= 1.0


def test_corpus_and_agreement_smoke(rules):
    deck = load_deck("data/decks/saga.yaml")
    positions = collect_positions(rules, deck, deck, 4, 5)
    assert positions, "対戦から局面が集まること"
    w = Weights()
    a = agreement(positions,
                  lambda e, me: evaluate(e, me, w) - evaluate(e, 1 - me, w))
    assert 0.0 <= a <= 1.0
