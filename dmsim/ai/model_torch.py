"""方策モデルの torch 版（Phase 10）。

numpy 版 Model と同じ構造・同じパラメータ名/形状で、学習をバッチ化する。
決定をまとめて padded テンソルにし、forward と REINFORCE の損失を
autograd で一括計算する（numpy 版は決定ごとの手書き逆伝播ループ）。
損失の意味論は numpy 版と同一: adv = (ret - value) を凍結した
-logp * adv + value_coef * (value - ret)^2 のバッチ平均。

インターフェースは Model と互換（act / loss_and_grads / step / save / load）で、
selfplay.train_iters をそのまま使える。保存形式（npz）も同一なので、
numpy 版と torch 版でモデルファイルを相互に読み書きできる。
torch が無い環境では import 自体が失敗する（呼び出し側で分岐すること）。
"""
from __future__ import annotations

import numpy as np
import torch

from .encode import GLOB, OPT_NUM, TOK_NUM, ZONES
from .model import D_EMB, H_CTX, H_MID, H_TOK, MAXK, Model

_PARAM_SHAPES = {
    "emb": None,  # (vocab, D_EMB)
    "W1": (H_TOK, D_EMB + TOK_NUM), "b1": (H_TOK,),
    "Wc": (H_CTX, len(ZONES) * H_TOK + GLOB), "bc": (H_CTX,),
    "Wv1": (H_MID, H_CTX), "bv1": (H_MID,),
    "wv2": (1, H_MID), "bv2": (1,),
    "Wk": (MAXK + 1, H_CTX), "bk": (MAXK + 1,),
    "Wo1": (H_MID, H_CTX + D_EMB + OPT_NUM), "bo1": (H_MID,),
    "wo2": (1, H_MID), "bo2": (1,),
}


class TorchModel:
    def __init__(self, vocab_size: int, seed: int = 0):
        g = torch.Generator().manual_seed(seed)

        def s(*shape):
            return (torch.randn(*shape, generator=g) * 0.1).requires_grad_(True)

        def z(*shape):
            return torch.zeros(*shape).requires_grad_(True)

        self.t = {
            "emb": s(vocab_size, D_EMB),
            "W1": s(H_TOK, D_EMB + TOK_NUM), "b1": z(H_TOK),
            "Wc": s(H_CTX, len(ZONES) * H_TOK + GLOB), "bc": z(H_CTX),
            "Wv1": s(H_MID, H_CTX), "bv1": z(H_MID),
            "wv2": s(1, H_MID), "bv2": z(1),
            "Wk": s(MAXK + 1, H_CTX), "bk": z(MAXK + 1),
            "Wo1": s(H_MID, H_CTX + D_EMB + OPT_NUM), "bo1": z(H_MID),
            "wo2": s(1, H_MID), "bo2": z(1),
        }
        self.vocab_size = vocab_size
        self._opt: torch.optim.Adam | None = None

    # numpy 版との互換: p はパラメータの numpy コピー（読み取り用）
    @property
    def p(self) -> dict:
        return {k: v.detach().numpy().copy() for k, v in self.t.items()}

    # ---- バッチ forward ----
    def _forward_batch(self, sts: list[dict], ops: list[dict]):
        t = self.t
        B = len(sts)
        T = max(1, max(len(st["tok_defn"]) for st in sts))
        O = max(1, max(len(op["opt_defn"]) for op in ops))
        tok_defn = np.zeros((B, T), np.int64)
        tok_num = np.zeros((B, T, TOK_NUM), np.float32)
        tok_zone = np.zeros((B, T), np.int64)
        tok_mask = np.zeros((B, T), np.float32)
        glob = np.zeros((B, GLOB), np.float32)
        opt_defn = np.zeros((B, O), np.int64)
        opt_num = np.zeros((B, O, OPT_NUM), np.float32)
        opt_mask = np.zeros((B, O), np.float32)
        for i, (st, op) in enumerate(zip(sts, ops)):
            n = len(st["tok_defn"])
            if n:
                tok_defn[i, :n] = st["tok_defn"]
                tok_num[i, :n] = st["tok_num"]
                tok_zone[i, :n] = st["tok_zone"]
                tok_mask[i, :n] = 1.0
            glob[i] = st["glob"]
            m = len(op["opt_defn"])
            if m:
                opt_defn[i, :m] = op["opt_defn"]
                opt_num[i, :m] = op["opt_num"]
                opt_mask[i, :m] = 1.0
        td = torch.as_tensor(tok_defn)
        x = torch.cat([t["emb"][td], torch.as_tensor(tok_num)], dim=2)
        h = torch.tanh(x @ t["W1"].T + t["b1"]) * torch.as_tensor(tok_mask)[..., None]
        Z = len(ZONES)
        zone_vecs = torch.zeros(B, Z, H_TOK)
        zone_vecs.scatter_add_(1, torch.as_tensor(tok_zone)[..., None].expand(B, T, H_TOK), h)
        cnt = torch.zeros(B, Z, 1)
        cnt.scatter_add_(1, torch.as_tensor(tok_zone)[..., None],
                         torch.as_tensor(tok_mask)[..., None])
        zone_vecs = zone_vecs / cnt.clamp(min=1.0)
        ctx_in = torch.cat([zone_vecs.reshape(B, Z * H_TOK), torch.as_tensor(glob)], dim=1)
        ctx = torch.tanh(ctx_in @ t["Wc"].T + t["bc"])                     # [B, H_CTX]
        hv = torch.tanh(ctx @ t["Wv1"].T + t["bv1"])
        value = (hv @ t["wv2"][0] + t["bv2"][0])                           # [B]
        count_logits = ctx @ t["Wk"].T + t["bk"]                           # [B, MAXK+1]
        od = torch.as_tensor(opt_defn)
        ox = torch.cat([ctx[:, None, :].expand(B, O, H_CTX), t["emb"][od],
                        torch.as_tensor(opt_num)], dim=2)
        ho = torch.tanh(ox @ t["Wo1"].T + t["bo1"])
        scores = ho @ t["wo2"][0] + t["bo2"][0]                            # [B, O]
        return scores, value, count_logits, torch.as_tensor(opt_mask)

    # ---- 行動（numpy 版と同じサンプリング規則） ----
    def act(self, st: dict, op: dict, rng, greedy: bool = False):
        with torch.no_grad():
            scores, value, count_logits, _ = self._forward_batch([st], [op])
        scores = scores[0].numpy()
        count_logits = count_logits[0].numpy()
        mn, mx = op["min"], op["max"]
        if mn == mx:
            k, logp_k = mn, 0.0
        else:
            lo, pr = Model._count_dist(count_logits, mn, mx)
            if greedy:
                k = lo + int(np.argmax(pr))
                logp_k = 0.0
            else:
                k = lo + int(rng.choice(len(pr), p=pr))
                logp_k = float(np.log(pr[k - lo] + 1e-12))
        choice, logp_pl = Model._pl_sample(scores, k, rng, greedy)
        return choice, (logp_pl + logp_k), float(value[0])

    # ---- 学習（REINFORCE + 価値ベースライン、バッチ一括） ----
    def loss_and_grads(self, batch: list[dict], value_coef: float = 0.5):
        for v in self.t.values():
            if v.grad is not None:
                v.grad = None
        sts = [it["st"] for it in batch]
        ops = [it["op"] for it in batch]
        scores, value, count_logits, opt_mask = self._forward_batch(sts, ops)
        B, O = scores.shape
        ret = torch.tensor([it["ret"] for it in batch], dtype=torch.float32)
        adv = (ret - value).detach()
        # PL logp（格納された choice の順序で逐次抽出したとみなす。numpy 版と同じ）
        L = max(1, max(len(it["choice"]) for it in batch))
        choice_pad = torch.zeros(B, L, dtype=torch.int64)
        choice_len = torch.tensor([len(it["choice"]) for it in batch])
        for i, it in enumerate(batch):
            if len(it["choice"]):
                choice_pad[i, :len(it["choice"])] = torch.tensor(it["choice"])
        remaining = opt_mask.clone()
        logp_pl = torch.zeros(B)
        for tt in range(L):
            logsm = torch.log_softmax(
                scores + torch.log(remaining.clamp(min=1e-12)), dim=1)
            pick = torch.where(tt < choice_len,
                               logsm.gather(1, choice_pad[:, tt:tt + 1])[:, 0],
                               torch.zeros(B))
            logp_pl = logp_pl + pick
            remaining.scatter_(1, choice_pad[:, tt:tt + 1], 0.0)
        # 個数ヘッドの logp（numpy 版の条件をそのままベクトル化）
        mn = torch.tensor([op["min"] for op in ops], dtype=torch.int64)
        mx_raw = torch.tensor([op["max"] for op in ops], dtype=torch.int64)
        hi = mx_raw.clamp(max=MAXK)
        lo = torch.minimum(mn, hi)
        kk = choice_len.clamp(max=MAXK)
        kgrid = torch.arange(MAXK + 1)[None, :]
        cmask = ((kgrid >= lo[:, None]) & (kgrid <= hi[:, None])).float()
        clogsm = torch.log_softmax(
            count_logits + torch.log(cmask.clamp(min=1e-12)), dim=1)
        valid = ((mn != mx_raw) & (choice_len >= mn)
                 & (kk >= lo) & (kk <= hi)).float()
        logp_k = clogsm.gather(1, kk[:, None])[:, 0] * valid
        loss = (-(logp_pl + logp_k) * adv
                + value_coef * (value - ret) ** 2).mean()
        loss.backward()
        grads = {k: (v.grad.numpy().copy() if v.grad is not None
                     else np.zeros(tuple(v.shape), np.float32))
                 for k, v in self.t.items()}
        return float(loss), grads

    def step(self, grads, lr: float = 3e-3):
        if self._opt is None:
            self._opt = torch.optim.Adam(list(self.t.values()), lr=lr)
        for gparam in self._opt.param_groups:
            gparam["lr"] = lr
        self._opt.step()

    # ---- 保存（numpy 版と同一形式） ----
    def save(self, path: str):
        np.savez(path, **{k: v.detach().numpy() for k, v in self.t.items()})

    @classmethod
    def load(cls, path: str) -> "TorchModel":
        z = np.load(path)
        m = cls(int(z["emb"].shape[0]))
        with torch.no_grad():
            for k in m.t:
                if k in z:
                    m.t[k].copy_(torch.as_tensor(z[k].astype(np.float32)))
        return m
