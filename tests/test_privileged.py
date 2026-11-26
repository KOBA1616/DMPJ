"""Phase 26-3: トラッカー特徴と特権価値ヘッドのテスト。

検証する性質:
- トラッカーは公開情報の決定的集計で、実状態と一致する（特に共有
  ゾーンであるバトルゾーンを owner 基準で正しく数える）
- 特権情報（相手の手札）は局面 dict に明示的に分離され、方策の
  スコアには一切影響しない（価値にだけ影響しうる）
- 旧形式の npz（トラッカー列・特権列なし）がそのまま読め、移行後の
  出力が「新規分をゼロにしたモデル」と完全一致する
- 特権分岐へ勾配が流れ、学習で Wpv がゼロから動く
"""
import numpy as np
import pytest

from dmsim.ai.encode import (COST_BUCKETS, TRACK, Vocab, encode_options,
                             encode_state, tracker_features)
from dmsim.ai.model import H_CTX, H_PRIV, Model
from dmsim.ai.selfplay import collect_games
from dmsim.cards.defs import load_rules
from dmsim.engine.core import Engine
from tools.bench_2p import load_deck


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


@pytest.fixture(scope="module")
def vocab(rules):
    return Vocab(rules)


def _play_random(eng, steps, seed=3):
    import random
    rng = random.Random(seed)
    for _ in range(steps):
        if eng.s.result is not None:
            break
        d = eng.advance()
        if d is None:
            break
        n = len(d["options"])
        k = rng.randint(d["min"], min(d["max"], n))
        eng.answer(sorted(rng.sample(range(n), k)))


def test_tracker_shape_and_start(rules, deck, vocab):
    eng = Engine.new_game(rules, [deck, deck], 3, 0)
    d = eng.advance()
    me = d["player"]
    st = encode_state(eng, me, vocab)
    assert st["track"].shape == (TRACK,)
    # ゲーム開始直後: 未見プール = 山札＋シールドの枚数と一致
    expect = (len(eng.s.zones["deck"][me])
              + len(eng.s.zones["shield"][me])) / 40.0
    assert st["track"][COST_BUCKETS * 2] == pytest.approx(expect)
    # 相手の公開カードはまだ無い
    assert st["track"][COST_BUCKETS * 4 + 1] == 0.0
    assert st["track"][TRACK - 1] == 0.0  # 自分のバトルゾーンは空


def test_tracker_midgame_matches_state(rules, deck, vocab):
    eng = Engine.new_game(rules, [deck, deck], 11, 0)
    _play_random(eng, 40)
    s = eng.s
    for me in (0, 1):
        op = 1 - me
        tr = tracker_features(eng, me, vocab)
        unseen = sum(1 for z in ("deck", "shield")
                     for cid in s.zones[z][me]
                     if s.cards[cid].owner == me)
        assert tr[COST_BUCKETS * 2] == pytest.approx(unseen / 40.0)
        pub = sum(1 for z in ("graveyard", "mana")
                  for cid in s.zones[z][op])
        pub += sum(1 for cid in s.zones["bz"][0]
                   if s.cards[cid].owner == op)
        pub += sum(1 for c in s.cards for u in c.under
                   if s.cards[u].owner == op)
        assert tr[COST_BUCKETS * 4 + 1] == pytest.approx(pub / 40.0)
        own_bz = sum(1 for cid in s.zones["bz"][0]
                     if s.cards[cid].owner == me)
        assert tr[TRACK - 1] == pytest.approx(own_bz / 10.0)
        # 各ヒストグラム単独の総和は総数以下（ツインパクトは両帯に数える）
        assert tr[0:COST_BUCKETS].sum() <= unseen / 40.0 + 1e-6
        assert tr[COST_BUCKETS:COST_BUCKETS * 2].sum() <= unseen / 40.0 + 1e-6
        b = COST_BUCKETS * 2 + 1
        assert tr[b:b + COST_BUCKETS].sum() <= pub / 40.0 + 1e-6
        assert tr[b + COST_BUCKETS:b + COST_BUCKETS * 2].sum() \
            <= pub / 40.0 + 1e-6


def test_privileged_encode_matches_opponent_hand(rules, deck, vocab):
    eng = Engine.new_game(rules, [deck, deck], 5, 0)
    d = eng.advance()
    me = d["player"]
    op = 1 - me
    st = encode_state(eng, me, vocab)
    assert "priv_defn" not in st  # 既定では特権情報を含めない
    stp = encode_state(eng, me, vocab, privileged=True)
    expect = sorted(vocab.idx(eng.s.cards[cid].defn)
                    for cid in eng.s.zones["hand"][op])
    assert sorted(int(x) for x in stp["priv_defn"]) == expect
    assert stp["priv_num"].shape == (len(expect),
                                     stp["tok_num"].shape[1])


def test_policy_scores_invariant_to_privileged(rules, deck, vocab):
    eng = Engine.new_game(rules, [deck, deck], 5, 0)
    d = eng.advance()
    me = d["player"]
    st = encode_state(eng, me, vocab)
    stp = encode_state(eng, me, vocab, privileged=True)
    op = encode_options(eng, d, vocab)
    model = Model(len(vocab), seed=4)
    s0, v0, c0, _ = model.forward(st, op)
    s1, v1, c1, _ = model.forward(stp, op)
    assert np.allclose(s0, s1) and np.allclose(c0, c1)
    assert v0 == v1  # Wpv がゼロ初期化のため価値もまだ一致する
    # 特権分岐を学習済みの状態にしても、方策と個数は不変で価値だけ動く
    rng = np.random.default_rng(0)
    model.p["Wpv"] = (rng.standard_normal(model.p["Wpv"].shape)
                      * 0.5).astype(np.float32)
    model.p["Wv1"][:, H_CTX:] = (rng.standard_normal(
        (model.p["Wv1"].shape[0], H_PRIV)) * 0.5).astype(np.float32)
    s2, v2, c2, _ = model.forward(stp, op)
    assert np.allclose(s0, s2) and np.allclose(c0, c2)
    assert v2 != v1


def test_old_npz_loads_with_identical_outputs(rules, deck, vocab, tmp_path):
    from dmsim.ai.encode import GLOB
    from dmsim.ai.model import H_TOK
    from dmsim.ai.encode import ZONES
    eng = Engine.new_game(rules, [deck, deck], 5, 0)
    d = eng.advance()
    st = encode_state(eng, d["player"], vocab, privileged=True)
    op = encode_options(eng, d, vocab)

    src = Model(len(vocab), seed=6)
    # 参照モデル: 新規分（トラッカー列・特権列・特権分岐）をゼロにしたもの
    ref = Model(len(vocab), seed=7)
    for k in ref.p:
        ref.p[k] = src.p[k].copy()
    zw = len(ZONES) * H_TOK + GLOB
    ref.p["Wc"][:, zw:] = 0.0
    ref.p["Wv1"][:, H_CTX:] = 0.0
    ref.p["Wpv"][:] = 0.0
    ref.p["bpv"][:] = 0.0
    # 旧形式 npz: Wpv/bpv を落とし、Wc/Wv1 を旧幅に切り詰める
    old = {}
    for k, v in src.p.items():
        if k in ("Wpv", "bpv"):
            continue
        if k == "Wc":
            v = v[:, :zw]
        if k == "Wv1":
            v = v[:, :H_CTX]
        old[k] = v
    path = str(tmp_path / "old.npz")
    np.savez(path, **old)
    m2 = Model.load(path)
    s_ref, v_ref, c_ref, _ = ref.forward(st, op)
    s2, v2, c2, _ = m2.forward(st, op)
    assert np.allclose(s_ref, s2)
    assert np.allclose(c_ref, c2)
    assert v_ref == pytest.approx(v2)


def test_privileged_grads_flow(rules, deck, vocab):
    from dmsim.ai.model import H_CTX
    model = Model(len(vocab), seed=8)
    batch, _w = collect_games(rules, vocab, model, deck, deck, games=1,
                              seed=9, privileged=True)
    assert any("priv_defn" in it["st"] and len(it["st"]["priv_defn"])
               for it in batch)
    loss, grads = model.loss_and_grads(batch[:24])
    assert np.isfinite(loss)
    assert all(np.isfinite(g).all() for g in grads.values())
    # 初期状態（Wv1 の特権列がゼロ）では勾配はまず Wv1 の特権列へ流れる
    assert np.abs(grads["Wv1"][:, H_CTX:]).sum() > 0
    model.step(grads)
    assert np.abs(model.p["Wv1"][:, H_CTX:]).sum() > 0
    # Wv1 の特権列が動いた後は Wpv へも勾配が流れる
    _loss2, grads2 = model.loss_and_grads(batch[:24])
    assert np.abs(grads2["Wpv"]).sum() > 0
