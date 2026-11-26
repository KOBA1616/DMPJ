"""Phase 26-4: 属性ベクトルと属性表現モデル（AttrModel）のテスト。

- 属性行列: 形、PAD 行、既知カードの意味特徴
- AttrModel: 前向き計算、Wattr への勾配（有限差分との照合）、
  保存→読み込みの往復で出力が一致すること
- ID 表現（Model）側は従来テスト（test_ai.py 等）で担保する
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dmsim.ai.attributes import build_attribute_matrix  # noqa: E402
from dmsim.ai.encode import Vocab, encode_options, encode_state  # noqa: E402
from dmsim.ai.model import Model  # noqa: E402
from dmsim.ai.model_attr import AttrModel, load_any  # noqa: E402
from dmsim.cards.defs import load_rules  # noqa: E402
from dmsim.engine.core import Engine  # noqa: E402
from tools.bench_2p import load_deck  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _full_cards():
    # conftest の DMSIM_SKIP_CONVERTED=1 を rules 読込より先に外す
    # （属性は全カードが対象。test_ai.py と同じ流儀）
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
def attr_pack(rules, vocab):
    return build_attribute_matrix(rules, vocab)


def test_matrix_shape_and_pad(attr_pack, vocab):
    attr, names = attr_pack
    assert attr.shape == (len(vocab), len(names))
    assert attr.shape[1] > 200  # 設計上の想定規模（内訳は docs 参照）
    assert np.all(attr[0] == 0)  # PAD 行はゼロ
    assert np.isfinite(attr).all()
    # 全カードが何らかの属性を持つ（基本ブロックがあるため）
    assert (np.abs(attr[1:]).sum(axis=1) > 0).all()


def test_known_card_semantics(attr_pack, vocab, rules):
    attr, names = attr_pack
    d = dict(zip(names, attr[vocab.idx("dm22ex2-021")]))  # 絶望神サガ
    assert d["has_creature"] == 1.0
    assert d["civ_water"] == 1.0 and d["civ_darkness"] == 1.0
    assert d["op_draw"] > 0          # ドロー効果
    assert d["verb_revival"] > 0     # 墓地→バトルゾーンの蘇生
    assert d["verb_self_discard"] > 0  # 手札→墓地の自己捨て
    assert d["race_ゴッド"] == 1.0
    # バニラ（能力なし）カードは効果 op を持たない
    vanilla = None
    for defn in vocab.ids:
        cd = rules.cards[defn]
        if not cd.abilities and not cd.keywords and not cd.faces:
            vanilla = defn
            break
    assert vanilla is not None
    dv = dict(zip(names, attr[vocab.idx(vanilla)]))
    assert dv["n_abilities"] == 0
    assert dv["op_move"] == 0 and dv["op_draw"] == 0


def _one_batch(rules, vocab, model, deck):
    """実際の対戦から (st, op, choice) を1つ作る。"""
    eng = Engine.new_game(rules, [deck, deck], 42, 0)
    rng = np.random.default_rng(0)
    for _ in range(12):
        d = eng.advance()
        if d is None:
            break
        st = encode_state(eng, d["player"], vocab)
        op = encode_options(eng, d, vocab)
        choice, _logp, _v = model.act(st, op, rng)
        if len(choice) >= 1:
            return [{"st": st, "op": op, "choice": sorted(choice),
                     "ret": 1.0}]
        eng.answer(sorted(choice))
    raise AssertionError("バッチを作れなかった")


@pytest.fixture(scope="module")
def deck():
    return load_deck("data/decks/saga.yaml")


def test_attr_model_forward_and_act(rules, vocab, attr_pack, deck):
    attr, _names = attr_pack
    m = AttrModel(attr, seed=3)
    assert "emb" not in m.p and "Wattr" in m.p
    batch = _one_batch(rules, vocab, m, deck)
    scores, value, count_logits, _ = m.forward(batch[0]["st"],
                                               batch[0]["op"])
    assert scores.shape == (len(batch[0]["op"]["opt_defn"]),)
    assert np.isfinite(scores).all() and np.isfinite(value)


def test_attr_model_wattr_grad_finite_diff(rules, vocab, attr_pack, deck):
    # 照合は BC 損失で行う。REINFORCE 損失はベースライン（価値）を
    # 定数として扱う解析勾配のため、素の有限差分とは一致しない
    # （ID 表現の Model でも同じ性質）。
    attr, _names = attr_pack
    m = AttrModel(attr, seed=3)
    batch = _one_batch(rules, vocab, m, deck)
    _loss, grads = m.bc_loss_and_grads(batch)
    assert "emb" not in grads
    g = grads["Wattr"]
    assert np.abs(g).sum() > 0
    # 有限差分で数点だけ照合する
    rng = np.random.default_rng(0)
    for _ in range(6):
        i = int(rng.integers(0, g.shape[0]))
        j = int(rng.integers(0, g.shape[1]))
        orig = m.p["Wattr"][i, j]
        eps = 1e-3
        m.p["Wattr"][i, j] = orig + eps
        lp, _ = m.bc_loss_and_grads(batch)
        m.p["Wattr"][i, j] = orig - eps
        lm, _ = m.bc_loss_and_grads(batch)
        m.p["Wattr"][i, j] = orig
        fd = (lp - lm) / (2 * eps)
        assert abs(fd - g[i, j]) < 5e-3 + 5e-2 * abs(g[i, j]), \
            f"Wattr[{i},{j}] 解析勾配 {g[i, j]:.5f} vs 有限差分 {fd:.5f}"


def test_attr_model_save_load_roundtrip(rules, vocab, attr_pack, deck,
                                        tmp_path):
    attr, names = attr_pack
    m = AttrModel(attr, seed=3)
    m.attr_names = names
    batch = _one_batch(rules, vocab, m, deck)
    s0, v0, _c, _ = m.forward(batch[0]["st"], batch[0]["op"])
    path = str(tmp_path / "attr_model.npz")
    m.save(path)
    m2 = load_any(path)
    assert isinstance(m2, AttrModel)
    assert m2.attr_names == names
    s1, v1, _c, _ = m2.forward(batch[0]["st"], batch[0]["op"])
    assert np.allclose(s0, s1) and abs(v0 - v1) < 1e-6


def test_id_model_still_loads_via_load_any(rules, vocab, tmp_path):
    m = Model(len(vocab), seed=3)
    path = str(tmp_path / "id_model.npz")
    m.save(path)
    m2 = load_any(path)
    assert type(m2) is Model
