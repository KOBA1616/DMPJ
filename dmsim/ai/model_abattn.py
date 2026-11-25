"""能力ブロック注意モデル（Phase 27'）。

Phase 26-4 の AttrModel（属性294次元をプーリング済みベクトルとして
線形射影する方式）と Phase 6 の AttnModel（ID 埋め込み＋盤面の
自己注意のみ）の先にあるモデル。カード表現を拡張可能特徴量
（ability_features）の能力ブロック列から作り、注意を3段入れる:

1. カード内: 能力ブロック列を線形射影（D_BLK）→ ブロック間の
   自己注意（4ヘッド）→ 注意プーリング＋平均＋最大プーリングを
   カードヘッダの射影と合わせてカードトークン（D_CARD）にする。
   ツインパクトは面ごとの能力がブロック列に並ぶため、面の区別は
   ブロック側の特徴（face 添字を含む）で自然に扱われる。
2. 盤面: カードトークン列への自己注意（4ヘッド×2層、残差＋tanh、
   Phase 6 と同じ流儀）。その後ゾーン別プーリングで局面ベクトル。
3. 決定: 選択肢ベクトル（局面＋選択肢カード＋選択肢数値）を
   クエリとして盤面トークン列を参照する交差注意（単一ヘッド）で
   スコアを出す。「どの効果が・どの対象に」という結び付きを、
   プーリングで潰さずに選択肢ごとに読むのが狙い。

価値ヘッド・個数ヘッド・特権価値・トラッカー・等価手の集約は
Model と同一（_trunk / _heads / _priv と埋め込みフックだけを
差し替える）。学習則（REINFORCE＋価値ベースライン、BC）も同一。

勾配の流れ: カードベクトルはパラメータ版（step のたびに増える）
ごとにキャッシュし、バッチ内では定義ごとに dL/dカードベクトルを
蓄積して、loss の最後に定義ごとに1回だけブロック側へ逆伝播する
（_flush_card_grads）。これで全カードのブロック行列を dense に
持たず、学習で使う定義（サガデッキ17種が中心）だけが遅延生成＋
キャッシュされる。

保存形式: パラメータに加えてスキーマ版・特徴名（ブロック／
ヘッダ、JSON）と、プロバイダが生成済みの定義のブロック／ヘッダ
（定義IDキー）を npz に同梱する。読み込みは vocab があれば
スナップショットから復元でき、rules を渡せば全定義を遅延生成
できる。
"""
from __future__ import annotations

import json

import numpy as np

from .ability_features import card_ability_blocks, card_vector, default_schema
from .encode import OPT_NUM, TOK_NUM, ZONES
from .model import H_CTX, H_MID, H_PRIV, H_TOK, Model, _tanh, full_glob

D_BLK = 64          # 能力ブロックの射影次元
D_CARD = 64         # カードトークンの次元
BLK_HEADS = 4
BOARD_HEADS = 4
BOARD_LAYERS = 2
D_ATTN = 64         # 交差注意の次元
DH_BLK = D_BLK // BLK_HEADS
DH_BOARD = H_TOK // BOARD_HEADS


def _softmax_rows(S: np.ndarray) -> np.ndarray:
    S = S - S.max(axis=-1, keepdims=True)
    A = np.exp(S)
    A /= A.sum(axis=-1, keepdims=True)
    return A


def _attn_forward(h: np.ndarray, p: dict, pre: str, heads: int, dh: int):
    """多ヘッド自己注意1層: h2 = tanh(h + Attn(h))。Phase 6 と同じ形。"""
    T = h.shape[0]
    Q = (h @ p[f"{pre}q"].T).reshape(T, heads, dh).transpose(1, 0, 2)
    K = (h @ p[f"{pre}k"].T).reshape(T, heads, dh).transpose(1, 0, 2)
    V = (h @ p[f"{pre}v"].T).reshape(T, heads, dh).transpose(1, 0, 2)
    A = _softmax_rows(Q @ K.transpose(0, 2, 1) / np.sqrt(dh))
    O = (A @ V).transpose(1, 0, 2).reshape(T, -1)
    h2 = _tanh(h + O @ p[f"{pre}o"].T)
    return h2, (h, Q, K, V, A, O, h2)


def _attn_backward(grads, p: dict, pre: str, cache, dh_out: np.ndarray,
                   heads: int, dh_dim: int) -> np.ndarray:
    """_attn_forward の逆伝播。h への勾配を返す。"""
    h, Q, K, V, A, O, h2 = cache
    T = h.shape[0]
    dpre = dh_out * (1 - h2 ** 2)
    dh = dpre.copy()
    dO = dpre @ p[f"{pre}o"]
    grads[f"{pre}o"] += dpre.T @ O
    dOh = dO.reshape(T, heads, dh_dim).transpose(1, 0, 2)
    dV = A.transpose(0, 2, 1) @ dOh
    dA = dOh @ V.transpose(0, 2, 1)
    dS = A * (dA - (dA * A).sum(axis=-1, keepdims=True))
    dQ = dS @ K / np.sqrt(dh_dim)
    dK = dS.transpose(0, 2, 1) @ Q / np.sqrt(dh_dim)
    dQf = dQ.transpose(1, 0, 2).reshape(T, -1)
    dKf = dK.transpose(1, 0, 2).reshape(T, -1)
    dVf = dV.transpose(1, 0, 2).reshape(T, -1)
    dh += dQf @ p[f"{pre}q"] + dKf @ p[f"{pre}k"] + dVf @ p[f"{pre}v"]
    grads[f"{pre}q"] += dQf.T @ h
    grads[f"{pre}k"] += dKf.T @ h
    grads[f"{pre}v"] += dVf.T @ h
    return dh


class CardFeatures:
    """定義ごとの（能力ブロック列, カードヘッダ）の遅延生成＋キャッシュ。

    全カードのブロック行列は dense に持たない。学習・評価で実際に
    現れた定義だけを ability_features の公開 API で生成する。
    """

    def __init__(self, rules, vocab, schema=None):
        self.rules = rules
        self.vocab = vocab
        self.schema = schema or default_schema(rules)
        pos = {n: i for i, n in enumerate(self.schema.card_names)}
        self._hdr_pos = np.array(
            [pos[n] for n in self.schema.header_names], dtype=np.int64)
        self.block_dim = int(self.schema.block_dim)
        self.header_dim = len(self.schema.header_names)
        self._cache: dict[int, tuple[np.ndarray, np.ndarray]] = {}

    def get(self, idx: int) -> tuple[np.ndarray, np.ndarray]:
        ent = self._cache.get(idx)
        if ent is not None:
            return ent
        if self.rules is None:
            raise RuntimeError(
                f"定義 idx={idx} はスナップショットに無く、rules も無い")
        defn = self.vocab.ids[idx - 1]
        cd = self.rules.cards[defn]
        blocks = card_ability_blocks(cd, self.schema)
        header = card_vector(cd, self.schema)[self._hdr_pos]
        ent = (blocks, np.asarray(header, dtype=np.float32))
        self._cache[idx] = ent
        return ent

    def cached_indices(self) -> list[int]:
        return sorted(self._cache)

    def snapshot_arrays(self) -> dict[str, np.ndarray]:
        """生成済み定義を npz 同梱用に平坦化する（定義IDキー）。"""
        defns, blocks, offsets, headers = [], [], [0], []
        for idx in self.cached_indices():
            b, h = self._cache[idx]
            defns.append(self.vocab.ids[idx - 1])
            blocks.append(b)
            offsets.append(offsets[-1] + len(b))
            headers.append(h)
        return {
            "_snap_defns": np.asarray(
                json.dumps(defns, ensure_ascii=False)),
            "_snap_blocks": (np.concatenate(blocks, axis=0)
                             if blocks else np.zeros(
                                 (0, self.block_dim), np.float32)),
            "_snap_offsets": np.asarray(offsets, dtype=np.int64),
            "_snap_headers": (np.stack(headers) if headers else np.zeros(
                (0, self.header_dim), np.float32)),
        }

    @classmethod
    def from_snapshot(cls, z, vocab, block_names, header_names,
                      version) -> "CardFeatures":
        obj = cls.__new__(cls)
        obj.rules = None
        obj.vocab = vocab

        class _S:  # schema のうちモデルが使う属性だけを持つ軽量版
            pass
        sch = _S()
        sch.block_names = block_names
        sch.header_names = header_names
        sch.version = version
        sch.block_dim = len(block_names)
        obj.schema = sch
        obj.block_dim = len(block_names)
        obj.header_dim = len(header_names)
        obj._cache = {}
        defns = json.loads(str(z["_snap_defns"]))
        blocks = z["_snap_blocks"].astype(np.float32)
        offsets = z["_snap_offsets"]
        headers = z["_snap_headers"].astype(np.float32)
        for i, defn in enumerate(defns):
            idx = vocab.index.get(defn)
            if idx is None:
                continue
            obj._cache[idx] = (blocks[offsets[i]:offsets[i + 1]], headers[i])
        return obj


class AbAttnModel(Model):
    def __init__(self, features: CardFeatures, vocab_size: int,
                 seed: int = 0):
        super().__init__(vocab_size, seed=seed)
        self.features = features
        bd, hd = features.block_dim, features.header_dim
        rng = np.random.default_rng(seed + 1_000_003)
        s = lambda *shape: (rng.standard_normal(shape) * 0.1).astype(np.float32)
        blk_scale, hdr_scale = self._feature_scales(rng)
        self.p.pop("emb")
        self.p.pop("wo2")
        self.p.pop("bo2")
        self.p["W1"] = s(H_TOK, D_CARD + TOK_NUM)
        self.p["Wo1"] = s(H_MID, H_CTX + D_CARD + OPT_NUM)
        self.p["Wpv"] = s(H_PRIV, D_CARD + TOK_NUM)
        self.p.update({
            # カード内: ブロック射影＋ブロック間注意＋プーリング＋ヘッダ
            "Wblk": (rng.standard_normal((D_BLK, bd)) * blk_scale
                     ).astype(np.float32),
            "bblk": np.zeros(D_BLK, np.float32),
            "cb_q": s(D_BLK, D_BLK), "cb_k": s(D_BLK, D_BLK),
            "cb_v": s(D_BLK, D_BLK), "cb_o": s(D_BLK, D_BLK),
            "qpool": s(D_BLK),
            "Wcard": s(D_CARD, 3 * D_BLK),
            "bcard": np.zeros(D_CARD, np.float32),
            "Whdr": (rng.standard_normal((D_CARD, hd)) * hdr_scale
                     ).astype(np.float32),
            # 盤面: ゾーン埋め込み＋自己注意2層
            "zemb": s(len(ZONES), H_TOK),
            # 決定: 交差注意
            "Wcq": s(D_ATTN, H_MID), "Wck": s(D_ATTN, H_TOK),
            "Wcv": s(D_ATTN, H_TOK),
            "Ws": s(H_MID, H_MID + D_ATTN),
            "bs": np.zeros(H_MID, np.float32),
            "ws2": s(1, H_MID),
            "bscore": np.zeros(1, np.float32),
        })
        for l in range(BOARD_LAYERS):
            for nm in ("q", "k", "v", "o"):
                self.p[f"ba{l}{nm}"] = s(H_TOK, H_TOK)
        self._adam_m = {k: np.zeros_like(v) for k, v in self.p.items()}
        self._adam_v = {k: np.zeros_like(v) for k, v in self.p.items()}
        self._adam_t = 0
        self._version = 0
        self._card_cache: dict[int, tuple] = {}
        self._pending: dict[int, np.ndarray] = {}
        self._dboard = None

    def _feature_scales(self, rng) -> tuple[float, float]:
        """Wblk / Whdr の初期スケール: 特徴行の RMS ノルムに合わせ、
        射影後のばらつきが tanh の入力として適度な大きさ（標準偏差
        0.4 程度）になるようにする（AttrModel の Wattr と同じ考え方）。"""
        f = self.features
        if f.rules is not None:
            n = len(f.vocab)
            idxs = list(range(1, n, max(1, n // 200)))[:200]
        else:
            idxs = f.cached_indices()[:200]
        bnorms, hnorms = [], []
        for idx in idxs:
            b, h = f.get(idx)
            if len(b):
                bnorms.extend(np.sqrt((b ** 2).sum(axis=1)).tolist())
            hnorms.append(float(np.sqrt((h ** 2).sum())))
        rms_b = float(np.mean(bnorms)) if bnorms else 1.0
        rms_h = float(np.mean(hnorms)) if hnorms else 1.0
        return 0.4 / max(rms_b, 1e-6), 0.4 / max(rms_h, 1e-6)

    # ---- カード表現（能力ブロック列 → カードトークン） ----
    def _card_forward(self, idx: int):
        ent = self._card_cache.get(idx)
        if ent is not None:
            return ent
        p = self.p
        blocks, hdr = self.features.get(idx)
        if len(blocks) == 0:
            pools = np.zeros(3 * D_BLK, np.float32)
            acache = None
        else:
            hb = _tanh(blocks @ p["Wblk"].T + p["bblk"])
            hb2, acache = _attn_forward(hb, p, "cb_", BLK_HEADS, DH_BLK)
            sc = hb2 @ p["qpool"] / np.sqrt(D_BLK)
            a = _softmax_rows(sc[None, :])[0]
            pools = np.concatenate([
                a @ hb2, hb2.mean(axis=0), hb2.max(axis=0)]).astype(
                    np.float32)
            acache = acache + (a, hb2.argmax(axis=0))
        u = pools @ p["Wcard"].T + hdr @ p["Whdr"].T + p["bcard"]
        vec = _tanh(u)
        ent = (vec, blocks, hdr, pools, acache)
        self._card_cache[idx] = ent
        return ent

    def _embed(self, idx):
        idx = np.asarray(idx)
        out = np.zeros((len(idx), D_CARD), np.float32)
        for i, ix in enumerate(idx):
            if ix != 0:
                out[i] = self._card_forward(int(ix))[0]
        return out

    def _embed_grad(self, grads, idx, g):
        # 即座には逆伝播せず、定義ごとに蓄積する（_flush_card_grads）。
        for i, ix in enumerate(idx):
            if ix == 0:
                continue
            ix = int(ix)
            acc = self._pending.get(ix)
            if acc is None:
                self._pending[ix] = np.array(g[i], dtype=np.float32)
            else:
                acc += g[i]

    def _flush_card_grads(self, grads, scale: float):
        for ix, dvec in self._pending.items():
            self._card_backward(grads, ix, dvec * scale)
        self._pending = {}

    def _card_backward(self, grads, idx: int, dvec: np.ndarray):
        vec, blocks, hdr, pools, acache = self._card_cache[idx]
        p = self.p
        du = dvec * (1 - vec ** 2)
        grads["Wcard"] += du[:, None] * pools[None, :]
        grads["Whdr"] += du[:, None] * hdr[None, :]
        grads["bcard"] += du
        if acache is None:
            return
        dpools = du @ p["Wcard"]
        hb, Q, K, V, A, O, hb2, a, amax = acache
        n = hb.shape[0]
        d_att, d_mean, d_max = (dpools[:D_BLK], dpools[D_BLK:2 * D_BLK],
                                dpools[2 * D_BLK:])
        dhb2 = a[:, None] * d_att[None, :]
        da = hb2 @ d_att
        dsc = a * (da - float(a @ da))
        dhb2 += dsc[:, None] * (p["qpool"] / np.sqrt(D_BLK))[None, :]
        grads["qpool"] += (dsc[:, None] * hb2).sum(axis=0) / np.sqrt(D_BLK)
        dhb2 += d_mean[None, :] / n
        np.add.at(dhb2, (amax, np.arange(D_BLK)), d_max)
        dhb = _attn_backward(grads, p, "cb_", (hb, Q, K, V, A, O, hb2),
                             dhb2, BLK_HEADS, DH_BLK)
        dhb_pre = dhb * (1 - hb ** 2)
        grads["Wblk"] += dhb_pre.T @ blocks
        grads["bblk"] += dhb_pre.sum(axis=0)

    # ---- 学習ラッパー（カード側勾配の flush を挟む） ----
    def loss_and_grads(self, batch, value_coef: float = 0.5,
                       aggregate: bool = False):
        loss, grads = super().loss_and_grads(
            batch, value_coef=value_coef, aggregate=aggregate)
        self._flush_card_grads(grads, 1.0 / max(1, len(batch)))
        return loss, grads

    def bc_loss_and_grads(self, batch, aggregate: bool = False):
        loss, grads = super().bc_loss_and_grads(batch, aggregate=aggregate)
        self._flush_card_grads(grads, 1.0 / max(1, len(batch)))
        return loss, grads

    def step(self, grads, lr: float = 3e-3):
        super().step(grads, lr=lr)
        self._version += 1
        self._card_cache.clear()

    # ---- トランク（盤面の自己注意つき） ----
    def _trunk(self, st: dict):
        p = self.p
        emb_tok = self._embed(st["tok_defn"])
        x = np.concatenate([emb_tok, st["tok_num"]], axis=1)
        h0 = _tanh(x @ p["W1"].T + p["b1"])
        h = h0 + p["zemb"][st["tok_zone"]]
        lcaches = []
        for l in range(BOARD_LAYERS):
            if h.shape[0] == 0:
                lcaches.append(None)
                continue
            h, lc = _attn_forward(h, p, f"ba{l}", BOARD_HEADS, DH_BOARD)
            lcaches.append(lc)
        zone_vecs = np.zeros((len(ZONES), H_TOK), np.float32)
        np.add.at(zone_vecs, st["tok_zone"], h)
        cnt = np.bincount(st["tok_zone"], minlength=len(ZONES)
                          ).astype(np.float32)
        zone_vecs /= np.maximum(cnt, 1.0)[:, None]
        ctx_in = np.concatenate([zone_vecs.reshape(-1), full_glob(st)])
        ctx = _tanh(ctx_in @ p["Wc"].T + p["bc"])
        return ctx, (x, h0, lcaches, h, ctx_in, ctx, cnt)

    def _trunk_backward(self, grads, st: dict, tcache, dctx):
        x, h0, lcaches, h_fin, ctx_in, ctx, cnt = tcache
        p = self.p
        dctx_in = (dctx * (1 - ctx ** 2)) @ p["Wc"]
        grads["Wc"] += (dctx * (1 - ctx ** 2))[:, None] * ctx_in[None, :]
        grads["bc"] += dctx * (1 - ctx ** 2)
        dzone = dctx_in[:len(ZONES) * H_TOK].reshape(len(ZONES), H_TOK)
        if h_fin.shape[0] == 0:
            self._token_backward(grads, st, x, h0, np.zeros_like(h0))
            self._dboard = None
            return
        dh = dzone[st["tok_zone"]] / cnt[st["tok_zone"]][:, None]
        if self._dboard is not None:
            dh = dh + self._dboard
            self._dboard = None
        for l in range(BOARD_LAYERS - 1, -1, -1):
            if lcaches[l] is None:
                continue
            dh = _attn_backward(grads, p, f"ba{l}", lcaches[l], dh,
                                BOARD_HEADS, DH_BOARD)
        np.add.at(grads["zemb"], st["tok_zone"], dh)
        self._token_backward(grads, st, x, h0, dh)

    def _token_backward(self, grads, st: dict, x, h, dh):
        p = self.p
        dhp = dh * (1 - h ** 2)
        dx = dhp @ p["W1"]
        grads["W1"] += dhp.T @ x
        grads["b1"] += dhp.sum(axis=0)
        self._embed_grad(grads, st["tok_defn"], dx[:, :D_CARD])

    # ---- 特権分岐（Model と同一。埋め込み次元だけ D_CARD） ----
    def _priv(self, st: dict):
        p = self.p
        defn = st.get("priv_defn")
        if defn is None or len(defn) == 0:
            return np.zeros(H_PRIV, np.float32), None
        x = np.concatenate([self._embed(defn), st["priv_num"]], axis=1)
        mx = x.mean(axis=0)
        pv = _tanh(mx @ p["Wpv"].T + p["bpv"])
        return pv, (x, mx, pv)

    def _priv_backward(self, grads, st: dict, pcache, dpriv):
        if pcache is None:
            return
        x, mx, pv = pcache
        p = self.p
        du = dpriv * (1 - pv ** 2)
        grads["Wpv"] += du[:, None] * mx[None, :]
        grads["bpv"] += du
        dmx = du @ p["Wpv"]
        dx = np.broadcast_to(dmx / len(x), x.shape)
        self._embed_grad(grads, st["priv_defn"], dx[:, :D_CARD])

    # ---- ヘッド（交差注意つき） ----
    def forward(self, st: dict, op: dict):
        ctx, tcache = self._trunk(st)
        scores, value, count_logits, hcache = self._heads(
            ctx, op, priv=self._priv(st), board=tcache[3])
        return scores, value, count_logits, (tcache, hcache, ctx)

    def _heads(self, ctx, op: dict, priv=None, board=None):
        p = self.p
        pv, pcache = priv if priv is not None else (
            np.zeros(H_PRIV, np.float32), None)
        vin = np.concatenate([ctx, pv])
        hv = _tanh(vin @ p["Wv1"].T + p["bv1"])
        value = float(hv @ p["wv2"][0] + p["bv2"][0])
        count_logits = ctx @ p["Wk"].T + p["bk"]
        emb_opt = self._embed(op["opt_defn"])
        ox = np.concatenate([
            np.broadcast_to(ctx, (len(emb_opt), H_CTX)), emb_opt,
            op["opt_num"],
        ], axis=1)
        u = _tanh(ox @ p["Wo1"].T + p["bo1"])
        if board is None or board.shape[0] == 0:
            c = np.zeros((len(u), D_ATTN), np.float32)
            xcache = None
        else:
            q = u @ p["Wcq"].T
            k = board @ p["Wck"].T
            v = board @ p["Wcv"].T
            A = _softmax_rows(q @ k.T / np.sqrt(D_ATTN))
            c = A @ v
            xcache = (q, k, v, A, board)
        hs_in = np.concatenate([u, c], axis=1)
        hs = _tanh(hs_in @ p["Ws"].T + p["bs"])
        scores = hs @ p["ws2"][0] + p["bscore"][0]
        return scores, value, count_logits, (
            hv, ox, u, hs, hs_in, vin, pcache, xcache)

    def _heads_backward(self, grads, st: dict, op: dict, ctx, hcache,
                        dscores, dcount, dvalue):
        hv, ox, u, hs, hs_in, vin, pcache, xcache = hcache
        p = self.p
        grads["ws2"][0] += (dscores[:, None] * hs).sum(axis=0)
        grads["bscore"][0] += dscores.sum()
        dhs = dscores[:, None] * p["ws2"][0][None, :] * (1 - hs ** 2)
        grads["Ws"] += dhs.T @ hs_in
        grads["bs"] += dhs.sum(axis=0)
        dhs_in = dhs @ p["Ws"]
        du = dhs_in[:, :H_MID].copy()
        dc = dhs_in[:, H_MID:]
        if xcache is not None:
            q, k, v, A, board = xcache
            dA = dc @ v.T
            dv = A.T @ dc
            dS = A * (dA - (dA * A).sum(axis=-1, keepdims=True))
            dS /= np.sqrt(D_ATTN)
            dq = dS @ k
            dk = dS.T @ q
            du += dq @ p["Wcq"]
            grads["Wcq"] += dq.T @ u
            self._dboard = dk @ p["Wck"] + dv @ p["Wcv"]
            grads["Wck"] += dk.T @ board
            grads["Wcv"] += dv.T @ board
        else:
            self._dboard = None
        du_pre = du * (1 - u ** 2)
        grads["Wo1"] += du_pre.T @ ox
        grads["bo1"] += du_pre.sum(axis=0)
        dox = du_pre @ p["Wo1"]
        dctx = dox[:, :H_CTX].sum(axis=0)
        self._embed_grad(grads, op["opt_defn"],
                         dox[:, H_CTX:H_CTX + D_CARD])
        dhv = dvalue * p["wv2"][0] * (1 - hv ** 2)
        grads["wv2"][0] += dvalue * hv
        grads["bv2"][0] += dvalue
        dvin = dhv @ p["Wv1"]
        dctx += dvin[:H_CTX]
        grads["Wv1"] += dhv[:, None] * vin[None, :]
        grads["bv1"] += dhv
        self._priv_backward(grads, st, pcache, dvin[H_CTX:])
        dctx += dcount @ p["Wk"]
        grads["Wk"] += dcount[:, None] * ctx[None, :]
        grads["bk"] += dcount
        return dctx

    # ---- 保存 ----
    def save(self, path: str):
        d = dict(self.p)
        sch = self.features.schema
        d["_schema_version"] = np.asarray(int(sch.version))
        d["_block_names"] = np.asarray(
            json.dumps(list(sch.block_names), ensure_ascii=False))
        d["_header_names"] = np.asarray(
            json.dumps(list(sch.header_names), ensure_ascii=False))
        d.update(self.features.snapshot_arrays())
        np.savez(path, **d)

    @classmethod
    def load(cls, path: str, vocab, rules=None) -> "AbAttnModel":
        z = np.load(path)
        block_names = json.loads(str(z["_block_names"]))
        header_names = json.loads(str(z["_header_names"]))
        version = int(z["_schema_version"])
        if rules is not None:
            features = CardFeatures(rules, vocab)
            if list(features.schema.block_names) != block_names:
                raise ValueError("ブロック特徴名が保存時と一致しない")
            if list(features.schema.header_names) != header_names:
                raise ValueError("ヘッダ特徴名が保存時と一致しない")
        else:
            features = CardFeatures.from_snapshot(
                z, vocab, block_names, header_names, version)
        m = cls(features, len(vocab))
        for k in m.p:
            if k in z:
                arr = z[k].astype(np.float32)
                if arr.shape != m.p[k].shape:
                    padded = np.zeros_like(m.p[k])
                    sl = tuple(slice(0, s) for s in arr.shape)
                    padded[sl] = arr
                    arr = padded
                m.p[k] = arr
        m._card_cache.clear()
        return m
