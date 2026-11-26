"""Phase 7: Rust 埋め込み方策（dmcore.run_batch_model）の検証。

- エンコードのパリティ: Rust 側 encode_state_features / encode_options_features が
  Python の encode_state / encode_options と（浮動小数点の誤差内で）一致する。
- run_batch_model: 軌跡つきで完走し、軌跡を Python の学習にそのまま渡せる。
"""
import json

import numpy as np
import pytest

dmcore = pytest.importorskip("dmcore")

from dmsim.ai.encode import Vocab, encode_options, encode_state  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine import rustcore  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from dmsim.engine.play import random_policy, run  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _full_cards():
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


def _midgame_states(rules, deck, games=2):
    """ランダム方策で回した対戦から、決定直前の (state_json, decision, player) を集める。"""
    import random as _random
    out = []
    for g in range(games):
        eng = Engine.new_game(rules, [deck, deck], 600 + g, g % 2)
        pol = random_policy(_random.Random(9 + g))
        for _ in range(30):
            d = eng.advance()
            if d is None:
                break
            out.append((eng.s.to_json(), d, d["player"]))
            eng.answer(pol(eng, d))
    return out


def test_encode_parity(rules, deck):
    vocab = Vocab(rules)
    bundle = rustcore._bundle_json(rules)
    samples = _midgame_states(rules, deck)
    assert len(samples) >= 20
    for state_json, d, player in samples[::7]:
        eng = Engine(rules, rustcore.state_from_json(state_json))
        exp = encode_state(eng, player, vocab)
        got = json.loads(dmcore.encode_state_features(bundle, state_json, player, json.dumps(vocab.ids)))
        assert got["tok_defn"] == exp["tok_defn"].tolist()
        assert got["tok_zone"] == exp["tok_zone"].tolist()
        assert np.allclose(got["tok_num"], exp["tok_num"], atol=1e-5)
        assert np.allclose(got["glob"], exp["glob"], atol=1e-5)
        expo = encode_options(eng, d, vocab)
        goto = json.loads(dmcore.encode_options_features(
            bundle, state_json, json.dumps(d), json.dumps(vocab.ids)))
        assert goto["opt_defn"] == expo["opt_defn"].tolist()
        assert np.allclose(goto["opt_num"], expo["opt_num"], atol=1e-5)
        assert goto["min"] == expo["min"] and goto["max"] == expo["max"]


def test_run_batch_model_collects(rules):
    # 現行 saga.yaml は Rust 未対応カード（dm23bd7-030）を含むため、
    # rustcore.new_game を使うこのテストは全カード plain な legacy デッキを使う
    # （Phase 25 の tests/test_batch2.py と同じ扱い）。
    deck = load_deck("data/decks/saga_legacy.yaml")
    vocab = Vocab(rules)
    model = Model(len(vocab), seed=1)
    states = [rustcore.new_game(rules, [deck, deck], 800 + g, g % 2) for g in range(4)]
    results = rustcore.run_batch_model(rules, states, model, vocab.ids, seed=3)
    assert len(results) == 4
    total_traj = 0
    for r in results:
        assert "error" not in r, r.get("error")
        assert r["winner"] in (0, 1)
        assert len(r["traj"]) == r["decisions"]
        total_traj += len(r["traj"])
    assert total_traj > 200
    # 軌跡は Python の学習にそのまま渡せる（先頭要素で勾配計算が回る）
    batch = []
    r0 = results[0]
    w = r0["winner"]
    for t in r0["traj"][:16]:
        batch.append({"st": t["st"], "op": t["op"], "choice": t["choice"],
                      "ret": 1.0 if w == t["player"] else -1.0})
    loss, grads = model.loss_and_grads(batch)
    assert np.isfinite(loss)
    assert all(np.isfinite(g).all() for g in grads.values())
