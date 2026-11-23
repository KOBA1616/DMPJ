"""小型方策/価値モデル（Phase 4、numpy実装）。

構成（ポケカABC上位の共通形を本システム向けに最小化したもの）:
- カード埋め込み（定義ごと）＋トークン数値特徴 → ゾーン別プーリング → 局面ベクトル
- 方策ヘッド: 選択肢ごとにスコア（局面ベクトル＋選択肢特徴）。選択は
  Plackett-Luce 型の逐次サンプリング（重みなし抽出）で、単一選択・複数選択・
  順序付け（order_cards）の全決定形を1つの分布で扱う。同値合法手は同じ特徴を
  持つため自然に同スコアになり、集約はサンプリング側で効く。
- 個数ヘッド: 選ぶ個数 k（min..max）の分布。
- 価値ヘッド: 局面ベクトルから勝敗予測（最終勝敗のみを教師にする疎な報酬）。

学習は REINFORCE（価値ヘッドをベースラインにする）＋価値の二乗誤差。
torch が無い環境でも動くよう numpy の手書き逆伝播で実装している。
"""
from __future__ import annotations

import numpy as np

from .encode import GLOB, OPT_NUM, TOK_NUM, ZONES

D_EMB = 24
H_TOK = 64
H_CTX = 128
H_MID = 64
MAXK = 16  # 個数ヘッドの上限（max がこれを超える決定では頭打ち）


def _tanh(x):
    return np.tanh(x)


class Model:
    def __init__(self, vocab_size: int, seed: int = 0):
        rng = np.random.default_rng(seed)
        s = lambda *shape: (rng.standard_normal(shape) * 0.1).astype(np.float32)
        self.p = {
            "emb": s(vocab_size, D_EMB),
            "W1": s(H_TOK, D_EMB + TOK_NUM), "b1": np.zeros(H_TOK, np.float32),
            "Wc": s(H_CTX, len(ZONES) * H_TOK + GLOB), "bc": np.zeros(H_CTX, np.float32),
            "Wv1": s(H_MID, H_CTX), "bv1": np.zeros(H_MID, np.float32),
            "wv2": s(1, H_MID), "bv2": np.zeros(1, np.float32),
            "Wk": s(MAXK + 1, H_CTX), "bk": np.zeros(MAXK + 1, np.float32),
            "Wo1": s(H_MID, H_CTX + D_EMB + OPT_NUM), "bo1": np.zeros(H_MID, np.float32),
            "wo2": s(1, H_MID), "bo2": np.zeros(1, np.float32),
        }
        self.vocab_size = vocab_size
        self._adam_m = {k: np.zeros_like(v) for k, v in self.p.items()}
        self._adam_v = {k: np.zeros_like(v) for k, v in self.p.items()}
        self._adam_t = 0

    # ---- forward ----
    def forward(self, st: dict, op: dict):
        p = self.p
        emb_tok = p["emb"][st["tok_defn"]]                       # [T, D]
        x = np.concatenate([emb_tok, st["tok_num"]], axis=1)     # [T, D+TOK]
        h = _tanh(x @ p["W1"].T + p["b1"])                       # [T, H_TOK]
        zone_vecs = np.zeros((len(ZONES), H_TOK), np.float32)
        for z in range(len(ZONES)):
            m = st["tok_zone"] == z
            if m.any():
                zone_vecs[z] = h[m].mean(axis=0)
        ctx_in = np.concatenate([zone_vecs.reshape(-1), st["glob"]])
        ctx = _tanh(ctx_in @ p["Wc"].T + p["bc"])                # [H_CTX]
        hv = _tanh(ctx @ p["Wv1"].T + p["bv1"])
        value = float(hv @ p["wv2"][0] + p["bv2"][0])
        count_logits = ctx @ p["Wk"].T + p["bk"]                 # [MAXK+1]
        emb_opt = p["emb"][op["opt_defn"]]                       # [O, D]
        ox = np.concatenate([
            np.broadcast_to(ctx, (len(emb_opt), H_CTX)), emb_opt, op["opt_num"],
        ], axis=1)
        ho = _tanh(ox @ p["Wo1"].T + p["bo1"])
        scores = ho @ p["wo2"][0] + p["bo2"][0]                  # [O]
        cache = (x, h, zone_vecs, ctx_in, ctx, hv, ox, ho)
        return scores, value, count_logits, cache

    # ---- 行動のサンプリングと log 確率 ----
    @staticmethod
    def _pl_sample(scores: np.ndarray, k: int, rng, greedy: bool):
        """scores の高い順に k 個を逐次抽出（greedy なら決定的）。(選択順, logp) を返す。"""
        rest = list(range(len(scores)))
        choice, logp = [], 0.0
        for _ in range(min(k, len(scores))):
            sc = scores[rest]
            if greedy:
                j = int(np.argmax(sc))
                logp += 0.0
            else:
                z = sc - sc.max()
                pr = np.exp(z)
                pr /= pr.sum()
                j = int(rng.choice(len(rest), p=pr))
                logp += float(np.log(pr[j] + 1e-12))
            choice.append(rest.pop(j))
        return choice, logp

    @staticmethod
    def _pl_logp(scores: np.ndarray, choice: list[int]) -> float:
        rest = list(range(len(scores)))
        logp = 0.0
        for c in choice:
            sc = scores[rest]
            z = sc - sc.max()
            pr = np.exp(z)
            pr /= pr.sum()
            logp += float(np.log(pr[rest.index(c)] + 1e-12))
            rest.remove(c)
        return logp

    @staticmethod
    def _count_dist(count_logits: np.ndarray, mn: int, mx: int):
        mx = min(mx, MAXK)
        mn = min(mn, mx)
        lg = count_logits[mn:mx + 1].astype(np.float64)
        z = lg - lg.max()
        pr = np.exp(z)
        pr /= pr.sum()
        return mn, pr

    def act(self, st: dict, op: dict, rng, greedy: bool = False):
        scores, value, count_logits, _ = self.forward(st, op)
        mn, mx = op["min"], op["max"]
        if mn == mx:
            k, logp_k = mn, 0.0
        else:
            lo, pr = self._count_dist(count_logits, mn, mx)
            if greedy:
                k = lo + int(np.argmax(pr))
                logp_k = 0.0
            else:
                k = lo + int(rng.choice(len(pr), p=pr))
                logp_k = float(np.log(pr[k - lo] + 1e-12))
        choice, logp_pl = self._pl_sample(scores, k, rng, greedy)
        return choice, (logp_pl + logp_k), value

    # ---- 学習（REINFORCE + 価値ベースライン） ----
    def loss_and_grads(self, batch: list[dict], value_coef: float = 0.5):
        """batch: [{st, op, choice, ret}]。ret はその決定をしたプレイヤーの最終勝敗（+1/-1）。"""
        grads = {k: np.zeros_like(v) for k, v in self.p.items()}
        total = 0.0
        for item in batch:
            st, op, choice, ret = item["st"], item["op"], item["choice"], item["ret"]
            scores, value, count_logits, cache = self.forward(st, op)
            x, h, zone_vecs, ctx_in, ctx, hv, ox, ho = cache
            p = self.p
            adv = ret - value
            # スコアへの勾配: PL logp の勾配 × (-adv)
            dscores = np.zeros_like(scores)
            rest = list(range(len(scores)))
            logp = 0.0
            for c in choice:
                sc = scores[rest]
                z = sc - sc.max()
                pr = np.exp(z)
                pr /= pr.sum()
                logp += float(np.log(pr[rest.index(c)] + 1e-12))
                # loss = -logp * adv なので d loss/d s_i = adv * (p_i - 1[i==c])
                for jj, idx in enumerate(rest):
                    dscores[idx] += adv * pr[jj]
                dscores[c] -= adv
                rest.remove(c)
            # 個数ヘッドへの勾配（loss に -logp_k * adv を含める）
            dcount = np.zeros(MAXK + 1, np.float32)
            mn, mx = op["min"], op["max"]
            logp_k = 0.0
            if mn != mx and len(choice) >= mn:
                lo, pr = self._count_dist(count_logits, mn, mx)
                kk = min(len(choice), MAXK)
                if lo <= kk <= min(mx, MAXK):
                    logp_k = float(np.log(pr[kk - lo] + 1e-12))
                    for jj in range(len(pr)):
                        dcount[lo + jj] += adv * pr[jj]
                    dcount[kk] -= adv
            logp += logp_k
            # 価値への勾配: value_coef * (value - ret)^2 → 2*coef*(value-ret)
            dvalue = 2.0 * value_coef * (value - ret)
            total += -logp * adv + value_coef * (value - ret) ** 2

            # ---- 逆伝播 ----
            # 選択肢スコア経路
            dho = dscores[:, None] * p["wo2"][0][None, :] * (1 - ho ** 2)
            grads["wo2"][0] += (dscores[:, None] * ho).sum(axis=0)
            grads["bo2"][0] += dscores.sum()
            dox = dho @ p["Wo1"]
            grads["Wo1"] += dho.T @ ox
            grads["bo1"] += dho.sum(axis=0)
            dctx = dox[:, :H_CTX].sum(axis=0)
            demb_opt = dox[:, H_CTX:H_CTX + D_EMB]
            np.add.at(grads["emb"], op["opt_defn"], demb_opt)
            # 価値経路
            dhv = dvalue * p["wv2"][0] * (1 - hv ** 2)
            grads["wv2"][0] += dvalue * hv
            grads["bv2"][0] += dvalue
            dctx += dhv @ p["Wv1"]
            grads["Wv1"] += dhv[:, None] * ctx[None, :]
            grads["bv1"] += dhv
            # 個数ヘッド経路
            dctx += dcount @ p["Wk"]
            grads["Wk"] += dcount[:, None] * ctx[None, :]
            grads["bk"] += dcount
            # 局面ベクトル経路
            dctx_in = (dctx * (1 - ctx ** 2)) @ p["Wc"]
            grads["Wc"] += (dctx * (1 - ctx ** 2))[:, None] * ctx_in[None, :]
            grads["bc"] += dctx * (1 - ctx ** 2)
            dzone = dctx_in[:len(ZONES) * H_TOK].reshape(len(ZONES), H_TOK)
            dh = np.zeros_like(h)
            for z in range(len(ZONES)):
                m = st["tok_zone"] == z
                if m.any():
                    dh[m] += dzone[z] / m.sum()
            dx = (dh * (1 - h ** 2)) @ p["W1"]
            grads["W1"] += (dh * (1 - h ** 2)).T @ x
            grads["b1"] += (dh * (1 - h ** 2)).sum(axis=0)
            np.add.at(grads["emb"], st["tok_defn"], dx[:, :D_EMB])
        n = max(1, len(batch))
        for k in grads:
            grads[k] /= n
        return total / n, grads

    def step(self, grads, lr: float = 3e-3):
        self._adam_t += 1
        t = self._adam_t
        for k, g in grads.items():
            self._adam_m[k] = 0.9 * self._adam_m[k] + 0.1 * g
            self._adam_v[k] = 0.999 * self._adam_v[k] + 0.001 * g * g
            mh = self._adam_m[k] / (1 - 0.9 ** t)
            vh = self._adam_v[k] / (1 - 0.999 ** t)
            self.p[k] -= lr * mh / (np.sqrt(vh) + 1e-8)

    # ---- 保存 ----
    def save(self, path: str):
        np.savez(path, **self.p)

    @classmethod
    def load(cls, path: str) -> "Model":
        z = np.load(path)
        m = cls(int(z["emb"].shape[0]))
        for k in m.p:
            if k in z:
                m.p[k] = z[k].astype(np.float32)
        return m
