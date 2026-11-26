"""属性表現モデル（Phase 26-4）。

カードトークンの表現を「定義ごとの ID 埋め込みテーブル」から
「属性ベクトル（attributes.build_attribute_matrix）の学習する線形
射影」に差し替えた Model。トランク・方策/価値/個数ヘッド・等価手の
集約・トラッカー・特権価値は Model のまま（model.Model の _embed /
_embed_grad フックだけを差し替える）。

狙い: 属性は語彙データから全カードに決定的に付くため、学習対戦に
出たことのないカードにも意味のある表現が与えられる。代償として、
カード固有の振る舞い（属性に表れない個別性）は覚えられない。

保存形式: パラメータに加えて属性行列そのもの（_attr）と特徴名
（_attr_names、JSON）を npz に同梱し、読み込み時に属性の再生成を
要しない（語彙側の変更で評価がずれる事故を防ぐ）。
"""
from __future__ import annotations

import json

import numpy as np

from .model import D_EMB, Model


class AttrModel(Model):
    def __init__(self, attr: np.ndarray, seed: int = 0):
        attr = np.asarray(attr, dtype=np.float32)
        super().__init__(int(attr.shape[0]), seed=seed)
        self.attr = attr
        self.attr_dim = int(attr.shape[1])
        # 射影の初期スケール: 属性行の RMS ノルムに合わせ、初期の
        # 埋め込みのばらつきが ID 埋め込み（標準偏差 0.1）と同程度に
        # なるようにする（A/B の初期条件を揃える）。
        norms = np.sqrt((attr[1:] ** 2).sum(axis=1))
        rms = float(norms[norms > 0].mean()) if (norms > 0).any() else 1.0
        scale = 0.1 / max(rms, 1e-6)
        rng = np.random.default_rng(seed + 1_000_003)
        self.p.pop("emb")
        self.p["Wattr"] = (
            rng.standard_normal((D_EMB, self.attr_dim)) * scale
        ).astype(np.float32)
        self.p["battr"] = np.zeros(D_EMB, np.float32)
        self._adam_m = {k: np.zeros_like(v) for k, v in self.p.items()}
        self._adam_v = {k: np.zeros_like(v) for k, v in self.p.items()}
        self._adam_t = 0

    # ---- 表現フックの差し替え ----
    def _embed(self, idx):
        return self.attr[idx] @ self.p["Wattr"].T + self.p["battr"]

    def _embed_grad(self, grads, idx, g):
        # dL/dWattr = Σ_i g_i ⊗ attr[idx_i]、dL/dbattr = Σ_i g_i。
        # 呼び出しごとに加算すれば全体の勾配と一致する（Model 側の
        # 勾配 dict はバッチ平均の前にここへ素通りで足される）。
        grads["Wattr"] += g.T @ self.attr[idx]
        grads["battr"] += g.sum(axis=0)

    # ---- 保存 ----
    def save(self, path: str):
        d = dict(self.p)
        d["_attr"] = self.attr
        names = getattr(self, "attr_names", None)
        if names is not None:
            d["_attr_names"] = np.asarray(
                json.dumps(names, ensure_ascii=False))
        np.savez(path, **d)

    @classmethod
    def load(cls, path: str) -> "AttrModel":
        z = np.load(path)
        m = cls(z["_attr"].astype(np.float32))
        if "_attr_names" in z:
            m.attr_names = json.loads(str(z["_attr_names"]))
        for k in m.p:
            if k in z:
                arr = z[k].astype(np.float32)
                if arr.shape != m.p[k].shape:
                    padded = np.zeros_like(m.p[k])
                    sl = tuple(slice(0, s) for s in arr.shape)
                    padded[sl] = arr
                    arr = padded
                m.p[k] = arr
        return m


def load_any(path: str):
    """npz の中身で ID 表現 / 属性表現を判別して読み込む。"""
    z = np.load(path)
    if "Wattr" in z:
        return AttrModel.load(path)
    return Model.load(path)
