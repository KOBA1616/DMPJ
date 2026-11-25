"""注意機構つきモデル（Phase 6）。

Model（ゾーン別プーリング）のトランクを差し替え、カードトークン同士の
自己注意（2ヘッド）を1層入れる。カード同士の関係（進化元・バトルの相手・
ブロッカーと攻撃側など）をプーリング前に混ぜられるのが狙い。
ヘッド（方策/価値/個数）と学習則は Model と共通。
"""
from __future__ import annotations

import numpy as np

from .encode import TOK_NUM, ZONES
from .model import D_EMB, H_CTX, H_TOK, Model, _tanh, full_glob

HEADS = 2
DH = H_TOK // HEADS


class AttnModel(Model):
    def __init__(self, vocab_size: int, seed: int = 0):
        super().__init__(vocab_size, seed=seed)
        rng = np.random.default_rng(seed + 777)
        s = lambda *shape: (rng.standard_normal(shape) * 0.1).astype(np.float32)
        extra = {
            "zemb": s(len(ZONES), H_TOK),
            "attn_q": s(H_TOK, H_TOK), "attn_k": s(H_TOK, H_TOK),
            "attn_v": s(H_TOK, H_TOK), "attn_o": s(H_TOK, H_TOK),
        }
        self.p.update(extra)
        for k, v in extra.items():
            self._adam_m[k] = np.zeros_like(v)
            self._adam_v[k] = np.zeros_like(v)

    def _trunk(self, st: dict):
        p = self.p
        emb_tok = p["emb"][st["tok_defn"]]
        x = np.concatenate([emb_tok, st["tok_num"]], axis=1)
        h0 = _tanh(x @ p["W1"].T + p["b1"])                    # [T, H]
        h = h0 + p["zemb"][st["tok_zone"]]
        T = h.shape[0]
        if T == 0:
            zone_vecs = np.zeros((len(ZONES), H_TOK), np.float32)
            ctx_in = np.concatenate([zone_vecs.reshape(-1), full_glob(st)])
            ctx = _tanh(ctx_in @ p["Wc"].T + p["bc"])
            return ctx, (x, h0, h, None, ctx_in, ctx)
        Q = (h @ p["attn_q"].T).reshape(T, HEADS, DH).transpose(1, 0, 2)
        K = (h @ p["attn_k"].T).reshape(T, HEADS, DH).transpose(1, 0, 2)
        V = (h @ p["attn_v"].T).reshape(T, HEADS, DH).transpose(1, 0, 2)
        S = Q @ K.transpose(0, 2, 1) / np.sqrt(DH)
        S = S - S.max(axis=-1, keepdims=True)
        A = np.exp(S)
        A /= A.sum(axis=-1, keepdims=True)
        O = (A @ V).transpose(1, 0, 2).reshape(T, H_TOK)       # [T, H]
        att = O @ p["attn_o"].T
        h2 = _tanh(h + att)
        zone_vecs = np.zeros((len(ZONES), H_TOK), np.float32)
        for z in range(len(ZONES)):
            m = st["tok_zone"] == z
            if m.any():
                zone_vecs[z] = h2[m].mean(axis=0)
        ctx_in = np.concatenate([zone_vecs.reshape(-1), full_glob(st)])
        ctx = _tanh(ctx_in @ p["Wc"].T + p["bc"])
        cache = (x, h0, h, (Q, K, V, A, O, h2), ctx_in, ctx)
        return ctx, cache

    def _trunk_backward(self, grads, st: dict, tcache, dctx):
        x, h0, h, attn, ctx_in, ctx = tcache
        p = self.p
        dctx_in = (dctx * (1 - ctx ** 2)) @ p["Wc"]
        grads["Wc"] += (dctx * (1 - ctx ** 2))[:, None] * ctx_in[None, :]
        grads["bc"] += dctx * (1 - ctx ** 2)
        dzone = dctx_in[:len(ZONES) * H_TOK].reshape(len(ZONES), H_TOK)
        T = h.shape[0]
        if attn is None:
            self._token_backward(grads, st, x, h0, np.zeros_like(h0))
            return
        Q, K, V, A, O, h2 = attn
        dh2 = np.zeros_like(h2)
        for z in range(len(ZONES)):
            m = st["tok_zone"] == z
            if m.any():
                dh2[m] += dzone[z] / m.sum()
        dpre = dh2 * (1 - h2 ** 2)                             # h2 = tanh(h + att)
        datt = dpre
        dh = dpre.copy()
        dO = datt @ p["attn_o"]
        grads["attn_o"] += datt.T @ O
        dOh = dO.reshape(T, HEADS, DH).transpose(1, 0, 2)      # [Hd, T, DH]
        dV = A.transpose(0, 2, 1) @ dOh
        dA = dOh @ V.transpose(0, 2, 1)
        dS = A * (dA - (dA * A).sum(axis=-1, keepdims=True))
        dQ = dS @ K / np.sqrt(DH)
        dK = dS.transpose(0, 2, 1) @ Q / np.sqrt(DH)
        dQf = dQ.transpose(1, 0, 2).reshape(T, H_TOK)
        dKf = dK.transpose(1, 0, 2).reshape(T, H_TOK)
        dVf = dV.transpose(1, 0, 2).reshape(T, H_TOK)
        dh += dQf @ p["attn_q"] + dKf @ p["attn_k"] + dVf @ p["attn_v"]
        grads["attn_q"] += dQf.T @ h
        grads["attn_k"] += dKf.T @ h
        grads["attn_v"] += dVf.T @ h
        np.add.at(grads["zemb"], st["tok_zone"], dh)
        self._token_backward(grads, st, x, h0, dh)
