"""Phase 3: dmcore.run_batch（一括実行）の検証。

- "first" 方策は決定的なので、駆動方式（RustSession で1手ずつ）と結果が一致する。
- "random" 方策は完走し、勝者と手数が妥当な範囲に収まる。
"""
import pytest

dmcore = pytest.importorskip("dmcore")

from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine import rustcore  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _full_cards():
    # conftest が立てる DMSIM_SKIP_CONVERTED=1 のままだと converted の札が読まれず、
    # サガデッキの札が unknown card になる。rules より先に外す（定義順に実行される）。
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


def _driven_first(rules, deck, seed, first):
    """RustSession を '最小数を先頭から' 方策で駆動した結果（バッチの first と同じ定義）。"""
    sess = rustcore.RustSession.open(
        rules, {"decks": [deck, deck], "seed": seed, "first_player": first})
    decisions = 0
    while True:
        d = sess.decision()
        if d is None:
            break
        sess.apply(list(range(d["min"])))
        decisions += 1
    res = sess.result()
    return {"winner": res["winner"], "turn": res["turn"], "decisions": decisions}


def test_batch_first_matches_driven(rules, deck):
    states = [rustcore.new_game(rules, [deck, deck], 700 + g, g % 2) for g in range(4)]
    got = rustcore.run_batch(rules, states, policy="first", seed=1)
    for g, r in enumerate(got):
        exp = _driven_first(rules, deck, 700 + g, g % 2)
        assert r == exp, f"game {g}: batch={r} driven={exp}"


def test_batch_random_completes(rules, deck):
    states = [rustcore.new_game(rules, [deck, deck], 900 + g, g % 2) for g in range(10)]
    got = rustcore.run_batch(rules, states, policy="random", seed=42)
    assert len(got) == 10
    for r in got:
        assert "error" not in r, r
        assert r["winner"] in (0, 1)
        assert 20 <= r["decisions"] <= 2000
        assert r["turn"] >= 1
