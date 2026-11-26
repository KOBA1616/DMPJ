"""Phase 27': 能力ブロック注意モデル（AbAttnModel）のテスト。

- CardFeatures: 遅延生成（使う定義だけ）、ツインパクトのブロック列
- AbAttnModel: 前向き計算と act（集約 ON を含む）、BC 損失の勾配を
  有限差分で照合（新規パラメータ群を中心に）、保存→読み込みの往復
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dmsim.ai.encode import Vocab, encode_options, encode_state  # noqa: E402
from dmsim.ai.model_abattn import AbAttnModel, CardFeatures  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
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
def vocab(rules):
    return Vocab(rules)


@pytest.fixture(scope="module")
def features(rules, vocab):
    return CardFeatures(rules, vocab)


@pytest.fixture(scope="module")
def deck():
    return load_deck("data/decks/saga.yaml")


def test_features_lazy_and_twinpact(features, vocab, rules):
    assert features.cached_indices() == []  # 生成前は空
    idx = vocab.idx("dm22ex2-021")  # 絶望神サガ
    blocks, header = features.get(idx)
    assert blocks.ndim == 2 and blocks.shape[1] == features.block_dim
    assert header.shape == (features.header_dim,)
    assert features.cached_indices() == [idx]  # 使った定義だけ
    # ツインパクト（面を持つカード）は両面の能力がブロック列に入る
    tp = next(d for d, cd in rules.cards.items()
              if getattr(cd, "faces", None))
    b2, _ = features.get(vocab.idx(tp))
    n_face_ab = sum(len(getattr(u, "abilities", None) or [])
                    for u in rules.cards[tp].faces)
    assert len(b2) >= n_face_ab >= 1


@pytest.fixture(scope="module")
def model(features, vocab):
    return AbAttnModel(features, len(vocab), seed=3)


def _one_batch(rules, vocab, model, deck):
    eng = Engine.new_game(rules, [deck, deck], 42, 0)
    rng = np.random.default_rng(0)
    for _ in range(12):
        d = eng.advance()
        if d is None:
            break
        st = encode_state(eng, d["player"], vocab, privileged=True)
        op = encode_options(eng, d, vocab)
        choice, _logp, _v = model.act(st, op, rng, aggregate=True)
        if len(choice) >= 1:
            return [{"st": st, "op": op, "choice": sorted(choice),
                     "ret": 1.0}]
        eng.answer(sorted(choice))
    raise AssertionError("バッチを作れなかった")


def test_forward_and_act(rules, vocab, model, deck):
    batch = _one_batch(rules, vocab, model, deck)
    scores, value, count_logits, _ = model.forward(
        batch[0]["st"], batch[0]["op"])
    assert scores.shape == (len(batch[0]["op"]["opt_defn"]),)
    assert np.isfinite(scores).all() and np.isfinite(value)
    assert "emb" not in model.p and "Wblk" in model.p


def test_bc_grads_finite_diff(rules, vocab, model, deck):
    batch = _one_batch(rules, vocab, model, deck)
    _loss, grads = model.bc_loss_and_grads(batch, aggregate=True)
    # 新規パラメータ群から満遍なく数点ずつ照合する
    # Wpv は特権価値専用分岐のため、価値に触れない BC 損失では
    # 勾配がゼロになるのが正しい（Model と同じ）。照合は REINFORCE
    # 側のテストで非ゼロだけ確認する。
    keys = ["Wblk", "cb_q", "qpool", "Wcard", "Whdr", "ba0q", "ba1k",
            "Wcq", "Wck", "Ws", "W1", "Wo1", "zemb"]
    rng = np.random.default_rng(0)
    for k in keys:
        g = grads[k]
        assert np.abs(g).sum() > 0, f"{k} の勾配がゼロ"
        for _ in range(3):
            ij = tuple(int(rng.integers(0, s)) for s in g.shape)
            orig = model.p[k][ij]
            eps = 1e-3
            model.p[k][ij] = orig + eps
            model._card_cache.clear()
            lp, _ = model.bc_loss_and_grads(batch, aggregate=True)
            model.p[k][ij] = orig - eps
            model._card_cache.clear()
            lm, _ = model.bc_loss_and_grads(batch, aggregate=True)
            model.p[k][ij] = orig
            model._card_cache.clear()
            fd = (lp - lm) / (2 * eps)
            assert abs(fd - g[ij]) < 5e-3 + 5e-2 * abs(g[ij]), \
                f"{k}{ij} 解析勾配 {g[ij]:.5f} vs 有限差分 {fd:.5f}"


def test_reinforce_loss_runs(rules, vocab, model, deck):
    batch = _one_batch(rules, vocab, model, deck)
    loss, grads = model.loss_and_grads(batch, aggregate=True)
    assert np.isfinite(loss)
    assert np.abs(grads["Wblk"]).sum() > 0
    # 特権分岐は Wv1 の特権列（初期ゼロ）から勾配が流れ始める設計
    # （Model の docstring 参照）。初回は特権列側が非ゼロであること。
    from dmsim.ai.model import H_CTX
    assert np.abs(grads["Wv1"][:, H_CTX:]).sum() > 0
    model.step(grads, lr=1e-3)
    # step 後も forward が動く（キャッシュ版が上がっている）
    scores, value, _c, _ = model.forward(batch[0]["st"], batch[0]["op"])
    assert np.isfinite(scores).all()


def test_save_load_roundtrip(rules, vocab, model, deck, tmp_path):
    batch = _one_batch(rules, vocab, model, deck)
    s0, v0, _c, _ = model.forward(batch[0]["st"], batch[0]["op"])
    path = str(tmp_path / "abattn.npz")
    model.save(path)
    m2 = AbAttnModel.load(path, vocab, rules=rules)
    s1, v1, _c, _ = m2.forward(batch[0]["st"], batch[0]["op"])
    assert np.allclose(s0, s1) and abs(v0 - v1) < 1e-6
    # rules 無しでもスナップショットから復元できる（生成済み定義のみ）
    m3 = AbAttnModel.load(path, vocab)
    s2, _v2, _c, _ = m3.forward(batch[0]["st"], batch[0]["op"])
    assert np.allclose(s0, s2)
