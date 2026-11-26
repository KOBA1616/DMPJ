"""Phase 12: TurnSearch の order_fn（方策による候補の並べ替え）の検証。

並べ替えは探索の完全性を保つこと、枝刈り（cap）は候補を絞ることを確認する。
方策の並べ替えで勝ち筋を見落とさないことが要点（tools/policy_order_compare.py
の測定では、枝刈り cap=2 では勝ち筋を逃すこともあわせて確認済み）。
"""
import os
from pathlib import Path

import pytest
import yaml

os.environ.setdefault("DMSIM_RUST", "0")

from dmsim.ai.demo import policy_order_fn  # noqa: E402
from dmsim.ai.encode import Vocab  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.engine import scenario as sc  # noqa: E402
from dmsim.search.turn import TurnSearch  # noqa: E402

SPEC = yaml.safe_load(
    (Path(__file__).parent / "saga_loop_first_setup.yaml")
    .read_text(encoding="utf-8"))


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


def test_order_fn_reorders_and_caps(rules):
    vocab = Vocab(rules)
    model = Model(len(vocab), seed=0)
    eng = sc.build(rules, SPEC)
    d = eng.advance()
    while d is not None and len(d["options"]) < 3:
        eng.answer([0])
        d = eng.advance()
    assert d is not None
    from dmsim.search.turn import candidates
    from dmsim.search.leaf_eval import Weights
    cands = candidates(eng, d, Weights(), cap=6)
    if len(cands) > 1:
        out = policy_order_fn(model, vocab)(eng, d, list(cands))
        assert sorted(map(tuple, out)) == sorted(map(tuple, cands))
        capped = policy_order_fn(model, vocab, cap=1)(eng, d, list(cands))
        assert len(capped) == 1 and capped[0] in cands


def test_search_with_policy_order_still_finds_win(rules):
    vocab = Vocab(rules)
    model = Model(len(vocab), seed=0)
    eng = sc.build(rules, SPEC)
    ts = TurnSearch(0, 1500, order_fn=policy_order_fn(model, vocab))
    leaf, _ = ts.run(eng)
    r = leaf.s.result
    assert r is not None and r.get("winner") == 0
