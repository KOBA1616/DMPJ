"""Phase 26-1: 等価手の集約（単一選択）のテスト。

検証する性質:
- グループ採番（option_groups）と encode_options の "grp" が意味キーと一致
- グループ確率 = メンバーの softmax 確率の合計（総和は 1 に保存される）
- act（集約 ON）はグループ確率で選び、代表インデックスとグループ logp を返す
- loss_and_grads（集約 ON）の勾配が有限差分と一致し、logp がグループ確率になる
- 集約 OFF / 複数選択 / grp 無し（Rust 軌跡）では従来経路と完全一致する
"""
import types

import numpy as np
import pytest

from dmsim.ai.encode import (GLOB, OPT_NUM, TOK_NUM, encode_options,
                             option_groups)
from dmsim.ai.model import Model, group_log_probs


def _stub_eng():
    return types.SimpleNamespace(s=types.SimpleNamespace(cards=[]))


def _st(n_tok=1):
    return {"tok_defn": np.ones(n_tok, np.int32),
            "tok_num": np.zeros((n_tok, TOK_NUM), np.float32),
            "tok_zone": np.zeros(n_tok, np.int32),
            "glob": np.zeros(GLOB, np.float32)}


def _op(grp=None, mn=1, mx=1, n=4):
    op = {"opt_defn": np.arange(1, n + 1, dtype=np.int32),
          "opt_num": np.zeros((n, OPT_NUM), np.float32),
          "min": mn, "max": mx, "kind": "choose_cards"}
    if grp is not None:
        op["grp"] = np.asarray(grp, np.int32)
    return op


def _softmax(scores):
    z = scores - scores.max()
    pr = np.exp(z)
    return pr / pr.sum()


# ---- グループ採番 ----

def test_option_groups_first_occurrence():
    grp = option_groups(["a", "b", "a", "c", "b", "a"])
    assert grp.tolist() == [0, 1, 0, 2, 1, 0]
    assert option_groups(["x"]).tolist() == [0]
    assert option_groups([]).tolist() == []


def test_encode_options_grp_matches_keys():
    decision = {"options": [{"key": "shield:1"}, {"key": "shield:2"},
                            {"key": "shield:1"}, {"key": "pass"}],
                "min": 1, "max": 1, "kind": "choose_shields"}
    op = encode_options(_stub_eng(), decision, vocab=None)
    assert op["grp"].tolist() == [0, 1, 0, 2]


def test_encode_options_missing_key_is_singleton():
    decision = {"options": [{"key": "a"}, {}, {}],
                "min": 1, "max": 1, "kind": "choose_cards"}
    op = encode_options(_stub_eng(), decision, vocab=None)
    assert op["grp"].tolist() == [0, 1, 2]


# ---- グループ確率の数学 ----

def test_group_log_probs_uniform():
    reps, glp = group_log_probs(np.zeros(4), [0, 0, 1, 2])
    assert reps == [0, 2, 3]
    assert np.allclose(np.exp(glp), [0.5, 0.25, 0.25])


def test_group_log_probs_sum_of_members():
    rng = np.random.default_rng(0)
    for _ in range(20):
        scores = rng.standard_normal(9)
        grp = np.array([0, 0, 1, 2, 1, 0, 3, 3, 2])
        reps, glp = group_log_probs(scores, grp)
        pr = _softmax(scores.astype(np.float64))
        for gi, g in enumerate(sorted(set(grp.tolist()))):
            expect = pr[grp == g].sum()
            assert np.exp(glp[gi]) == pytest.approx(expect, rel=1e-9)
        # 総和保存: グループ確率の合計は 1
        assert np.exp(glp).sum() == pytest.approx(1.0, rel=1e-9)
        # 代表は各グループの最小インデックス
        for gi, g in enumerate(sorted(set(grp.tolist()))):
            assert reps[gi] == int(np.nonzero(grp == g)[0][0])


# ---- act ----

def test_act_aggregate_logp_is_group_logp():
    model = Model(16, seed=3)
    st, op = _st(), _op(grp=[0, 0, 1, 1])
    scores = model.forward(st, op)[0].astype(np.float64)
    pr = _softmax(scores)
    rng = np.random.default_rng(42)
    for _ in range(30):
        choice, logp, _ = model.act(st, op, rng, aggregate=True)
        assert len(choice) == 1
        assert choice[0] in (0, 2)  # 必ず代表が返る
        g = 0 if choice[0] == 0 else 1
        expect = np.log(pr[np.asarray([0, 0, 1, 1]) == g].sum())
        assert logp == pytest.approx(expect, rel=1e-5)


def test_act_aggregate_greedy_picks_best_group_rep():
    model = Model(16, seed=3)
    st, op = _st(), _op(grp=[0, 0, 1, 1])
    scores = model.forward(st, op)[0].astype(np.float64)
    reps, glp = group_log_probs(scores, op["grp"])
    choice, logp, _ = model.act(st, op, np.random.default_rng(0),
                                greedy=True, aggregate=True)
    assert choice == [reps[int(np.argmax(glp))]]
    assert logp == 0.0


def test_act_off_unchanged():
    """集約 OFF は従来の PL サンプリングと（同じ rng で）完全一致する。"""
    model = Model(16, seed=3)
    st, op = _st(), _op(grp=[0, 0, 1, 1])
    scores, _, count_logits, _ = model.forward(st, op)
    rng1, rng2 = np.random.default_rng(7), np.random.default_rng(7)
    choice, logp, _ = model.act(st, op, rng1, aggregate=False)
    exp_choice, exp_logp = Model._pl_sample(scores, 1, rng2, False)
    assert choice == exp_choice
    assert logp == pytest.approx(exp_logp)


def test_act_multi_select_not_aggregated():
    """複数選択（max > 1）の決定では集約 ON でも従来経路と一致する。"""
    model = Model(16, seed=3)
    st, op = _st(), _op(grp=[0, 0, 1, 1], mn=0, mx=2)
    rng1, rng2 = np.random.default_rng(11), np.random.default_rng(11)
    c1 = model.act(st, op, rng1, aggregate=True)
    c2 = model.act(st, op, rng2, aggregate=False)
    assert c1[0] == c2[0]
    assert c1[1] == pytest.approx(c2[1])


def test_act_no_grp_falls_back():
    """grp が無い op（Rust 収集の軌跡形式）でも集約 ON で従来経路になる。"""
    model = Model(16, seed=3)
    st, op = _st(), _op(grp=None)
    rng1, rng2 = np.random.default_rng(11), np.random.default_rng(11)
    c1 = model.act(st, op, rng1, aggregate=True)
    c2 = model.act(st, op, rng2, aggregate=False)
    assert c1[0] == c2[0]
    assert c1[1] == pytest.approx(c2[1])


# ---- loss_and_grads ----

def _fd_check(model, batch, aggregate):
    """Wo1[0,0] に対する解析勾配と有限差分の一致（Wo1 は方策ヘッド専用）。"""
    loss0, grads = model.loss_and_grads(batch, aggregate=aggregate)
    eps = 1e-3
    orig = float(model.p["Wo1"][0, 0])
    model.p["Wo1"][0, 0] = orig + eps
    lp, _ = model.loss_and_grads(batch, aggregate=aggregate)
    model.p["Wo1"][0, 0] = orig - eps
    lm, _ = model.loss_and_grads(batch, aggregate=aggregate)
    model.p["Wo1"][0, 0] = orig
    numeric = (lp - lm) / (2 * eps)
    assert grads["Wo1"][0, 0] == pytest.approx(numeric, rel=0.05, abs=1e-5)
    return loss0


def test_loss_aggregate_gradient_finite_difference():
    model = Model(16, seed=3)
    st, op = _st(), _op(grp=[0, 0, 1, 1])
    batch = [{"st": st, "op": op, "choice": [2], "ret": 1.0}]
    _fd_check(model, batch, aggregate=True)
    _fd_check(model, batch, aggregate=False)


def test_loss_aggregate_group_invariance():
    """同じグループ内のどの選択肢を記録しても、集約 ON の損失は同じ。

    （ラベルの揺れが消えることの直接の確認。OFF では一般に異なる。）
    """
    model = Model(16, seed=3)
    st, op = _st(), _op(grp=[0, 0, 1, 1])

    def loss_for(choice, aggregate):
        batch = [{"st": st, "op": op, "choice": [choice], "ret": 1.0}]
        return model.loss_and_grads(batch, aggregate=aggregate)[0]

    assert loss_for(2, True) == pytest.approx(loss_for(3, True))
    assert loss_for(0, True) == pytest.approx(loss_for(1, True))


def test_loss_aggregate_logp_value():
    """集約 ON の損失に使われる logp がグループ確率の log であること。

    ret を価値ヘッドの予測に一致させると adv = 0 で損失は価値項のみに
    なるため、代わりに ret=1 の損失と手計算を比べる。
    """
    model = Model(16, seed=3)
    st, op = _st(), _op(grp=[0, 0, 1, 1])
    scores, value, _, _ = model.forward(st, op)
    pr = _softmax(scores.astype(np.float64))
    glp = np.log(pr[[0, 1]].sum())  # choice=1 はグループ 0
    adv = 1.0 - value
    expect = -glp * adv + 0.5 * (value - 1.0) ** 2
    batch = [{"st": st, "op": op, "choice": [1], "ret": 1.0}]
    loss, _ = model.loss_and_grads(batch, aggregate=True)
    assert loss == pytest.approx(expect, rel=1e-5)


def test_bc_aggregate_group_invariance():
    model = Model(16, seed=3)
    st, op = _st(), _op(grp=[0, 0, 1, 1])

    def loss_for(choice):
        batch = [{"st": st, "op": op, "choice": [choice]}]
        return model.bc_loss_and_grads(batch, aggregate=True)[0]

    assert loss_for(2) == pytest.approx(loss_for(3))
    assert loss_for(0) == pytest.approx(loss_for(1))


# ---- 実ゲームでの統合（収集→学習が集約 ON で回る） ----

@pytest.fixture(scope="module", autouse=True)
def _full_cards():
    import os
    saved = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    yield
    if saved is not None:
        os.environ["DMSIM_SKIP_CONVERTED"] = saved


@pytest.fixture(scope="module")
def rules():
    from dmsim.cards.defs import load_rules
    return load_rules()


@pytest.fixture(scope="module")
def deck():
    from tools.bench_2p import load_deck
    return load_deck("data/decks/saga.yaml")


def test_collect_and_train_with_aggregation(rules, deck):
    from dmsim.ai.encode import Vocab
    from dmsim.ai.selfplay import collect_games
    vocab = Vocab(rules)
    model = Model(len(vocab), seed=1)
    batch, _winners = collect_games(rules, vocab, model, deck, deck,
                                    games=2, seed=5, aggregate=True)
    assert len(batch) > 50
    # 単一選択の決定では、記録された choice が必ずグループ代表になっている
    checked = 0
    for item in batch:
        op = item["op"]
        if op["min"] == 1 and op["max"] == 1 and len(item["choice"]) == 1:
            grp = op["grp"]
            c = item["choice"][0]
            assert c == int(np.nonzero(grp == grp[c])[0][0])
            checked += 1
    assert checked > 0
    loss, grads = model.loss_and_grads(batch, aggregate=True)
    assert np.isfinite(loss)
    assert all(np.isfinite(g).all() for g in grads.values())
