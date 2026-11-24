"""発見の還元（Phase 11）: 探索の発見を教材化する仕組みの検証。

数値の主張（教材で実行率が上がるか）は tools/demo_train.py の対照実験で
測るものとし、ここでは仕組み（発見→記録→学習に混ぜる）が正しく回ることと、
記録した教材が実際に勝ち切る手順であることを確認する。
サガ局面は素の状態でも勝ちやすい（未学習で実行率 0.88〜1.00）ため、
実行率の大小はここでは主張しない。
"""
import os
from pathlib import Path

import pytest
import yaml

os.environ.setdefault("DMSIM_RUST", "0")

from dmsim.ai.demo import execution_rate, record_demo  # noqa: E402
from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.selfplay import train_iters  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
from dmsim.search import loop_first as lf  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402

SPEC = yaml.safe_load(
    (Path(__file__).parent / "saga_loop_first_setup.yaml")
    .read_text(encoding="utf-8"))


@pytest.fixture(scope="module", autouse=True)
def _full_cards():
    # サガデッキには converted のカードが含まれるため、conftest の
    # DMSIM_SKIP_CONVERTED=1 を rules 読込より先に外す（test_ai と同じ方式）
    saved = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    yield
    if saved is not None:
        os.environ["DMSIM_SKIP_CONVERTED"] = saved


@pytest.fixture(scope="module")
def rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


@pytest.fixture(scope="module")
def finding(rules):
    import dmsim.search.turn as T
    old = T.REPEAT_FIRST
    T.REPEAT_FIRST = False          # 探索が自分でループを回す経路を切る
    try:
        eng = sc.build(rules, SPEC)
        found = lf.two_stage(eng, 0, discover_budget=1500, seek_budget=1500,
                             first_win_only=False)
    finally:
        T.REPEAT_FIRST = old
    winners = [f for f in found if f.wins]
    assert winners, "前提: 探索で勝ち筋が見つかること"
    f = max(winners, key=lambda g: max(w["cycles"] for w in g.wins))
    return f, max(w["cycles"] for w in f.wins)


def test_record_demo_wins_and_teaches(rules, finding):
    f, cycles = finding
    vocab = Vocab(rules)
    items = record_demo(rules, vocab, f, cycles, budget=400)
    assert len(items) >= 10                       # 手順として十分な長さ
    assert all(it["ret"] == 1.0 for it in items)  # 勝ち手順なので報酬は +1
    assert all(0 <= min(it["choice"]) and
               max(it["choice"]) < len(it["op"]["opt_defn"])
               for it in items if it["choice"])
    # 教材を混ぜて学習が回る（自己対戦バッチと同形式であることの確認）
    deck = load_deck("data/decks/saga.yaml")
    model = Model(len(vocab), seed=0)
    hist = train_iters(rules, vocab, model, deck, deck, 2, 2,
                       seed=0, demo=items, log=lambda h: None)
    assert len(hist) == 2


def test_execution_rate_is_measurable(rules, finding):
    f, _ = finding
    vocab = Vocab(rules)
    model = Model(len(vocab), seed=0)
    r = execution_rate(rules, vocab, model, f.start, trials=4, seed=7)
    assert 0.0 <= r <= 1.0
