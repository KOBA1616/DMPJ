"""小型方策/価値モデル（Phase 4、numpy実装）。

構成（ポケカABC上位の共通形を本システム向けに最小化したもの）:
- カード埋め込み（定義ごと）＋トークン数値特徴 → ゾーン別プーリング → 局面ベクトル
  （トランク。注意機構版は model_attn.AttnModel がトランクだけ差し替える）
- 方策ヘッド: 選択肢ごとにスコア（局面ベクトル＋選択肢特徴）。選択は
  Plackett-Luce 型の逐次サンプリング（重みなし抽出）で、単一選択・複数選択・
  順序付け（order_cards）の全決定形を1つの分布で扱う。
- 等価手の集約（Phase 26-1、任意）: 意味キーが同じ選択肢をグループとして
  確率を合算してから選び、REINFORCE の log 確率もグループ確率で計算する
  （act / loss_and_grads / bc_loss_and_grads の aggregate 引数、単一選択のみ）。
- 個数ヘッド: 選ぶ個数 k（min..max）の分布。
- 価値ヘッド: 局面ベクトルから勝敗予測（最終勝敗のみを教師にする疎な報酬）。

学習は REINFORCE（価値ヘッドをベースラインにする）＋価値の二乗誤差。
torch が無い環境でも動くよう numpy の手書き逆伝播で実装している。

Phase 26-3 の追加:
- トラッカー特徴（encode.tracker_features）: トランクの入力に glob と
  並べて接続する（Wc の入力幅が GLOB+TRACK に拡張）。公開情報のみ。
- 特権価値ヘッド: 学習時の軌跡（encode_state(privileged=True)）に限り、
  相手の手札の集約ベクトルを価値ヘッドへ追加入力する。方策ヘッドと
  個数ヘッドには接続しないため、対戦時の手の選択は特権情報に一切
  依存しない。価値への接続（Wv1 の特権列）はゼロ初期化し、旧 npz の
  読み込みでもゼロ埋めするので、移行直後の価値は旧モデルと完全
  一致する。Wpv 自体は小さな乱数で初期化して対称性を壊す（両方を
  ゼロにすると勾配が永遠に流れず死に分岐になる。勾配はまず Wv1 の
  特権列へ、次に Wpv へ流れ始める）。
"""
from __future__ import annotations

import numpy as np

from .encode import GLOB, OPT_NUM, TOK_NUM, TRACK, ZONES

D_EMB = 24
H_TOK = 64
H_CTX = 128
H_MID = 64
H_PRIV = 32  # 特権ベクトル（相手の手札の集約）の次元
MAXK = 16  # 個数ヘッドの上限（max がこれを超える決定では頭打ち）


def full_glob(st: dict) -> np.ndarray:
    """glob とトラッカー特徴を連結したトランク入力の全体特徴部分。

    "track" が無い局面（Rust エンコードの軌跡など）ではゼロで埋める
    （移行直後の旧モデルでは Wc の該当列もゼロのため挙動は不変）。"""
    g = st["glob"]
    t = st.get("track")
    if t is None:
        t = np.zeros(TRACK, dtype=np.float32)
    return np.concatenate([g, t])


def _tanh(x):
    return np.tanh(x)


# ---- 等価手の集約（Phase 26-1） ----
# 意味キー（encode_options の "grp"）が同じ選択肢は盤面上の結果が同一。
# 集約時はグループ確率（メンバーの softmax 確率の合計）で選び・学ぶ。
# 対象は単一選択（min == max == 1）の決定のみ。複数選択では「同じ札を
# 2枚選ぶ」が正当な別結果になるため集約しない。

def group_log_probs(scores: np.ndarray, grp) -> tuple[list[int], np.ndarray]:
    """グループごとの log 確率と代表インデックスを返す。

    戻り: (reps, logp)。グループは id の昇順で並び、reps[g] はその
    グループの代表（最小の選択肢番号）、logp[g] はグループ確率の log
    （= メンバーのスコアの logsumexp − 全体の logsumexp）。
    グループ確率の合計は 1 になる（元の softmax の総和保存）。
    """
    scores = np.asarray(scores, dtype=np.float64)
    grp = np.asarray(grp)
    z = scores - scores.max()
    log_z = float(scores.max() + np.log(np.exp(z).sum()))
    reps: list[int] = []
    lps: list[float] = []
    for g in np.unique(grp):
        idx = np.nonzero(grp == g)[0]
        s = scores[idx]
        m = float(s.max())
        reps.append(int(idx[0]))
        lps.append(m + float(np.log(np.exp(s - m).sum())) - log_z)
    return reps, np.asarray(lps)


def _group_dscores(scores: np.ndarray, grp, chosen: int,
                   adv: float) -> np.ndarray:
    """集約時のスコア勾配: loss = -logp_group * adv に対する d loss/d scores。

    d(-logp_g)/ds_i = p_i（全体 softmax）− q_i。q は選ばれたグループ内での
    softmax（メンバー外は 0）で、合計は 1。非集約時の one-hot の一般化。
    """
    scores64 = np.asarray(scores, dtype=np.float64)
    grp = np.asarray(grp)
    z = scores64 - scores64.max()
    pr = np.exp(z)
    pr /= pr.sum()
    d = adv * pr
    idx = np.nonzero(grp == grp[chosen])[0]
    s = scores64[idx]
    zz = s - s.max()
    q = np.exp(zz)
    q /= q.sum()
    d[idx] -= adv * q
    return d.astype(np.float32)


def _agg_target(op: dict, choice, aggregate: bool):
    """集約を適用すべき決定なら grp を、そうでなければ None を返す。

    条件: 集約 ON、op に "grp" がある（Rust エンコード経路の軌跡には無い）、
    単一選択（min == max == 1）、記録された選択がちょうど1つ。
    """
    if not aggregate:
        return None
    grp = op.get("grp")
    if grp is None or len(choice) != 1:
        return None
    if op["min"] != 1 or op["max"] != 1:
        return None
    return grp


def _pad_cols(a: np.ndarray, extra: int) -> np.ndarray:
    """行列の右にゼロ列を足す（新規入力の寄与を初期状態で 0 にする）。"""
    if extra <= 0:
        return a
    return np.concatenate(
        [a, np.zeros((a.shape[0], extra), np.float32)], axis=1)


class Model:
    def __init__(self, vocab_size: int, seed: int = 0):
        rng = np.random.default_rng(seed)
        s = lambda *shape: (rng.standard_normal(shape) * 0.1).astype(np.float32)
        self.p = {
            "emb": s(vocab_size, D_EMB),
            "W1": s(H_TOK, D_EMB + TOK_NUM), "b1": np.zeros(H_TOK, np.float32),
            # Wc/Wv1 は旧形状で初期化してからゼロ列で広げる。新規モデルは
            # 従来モデル＋寄与ゼロの新分岐と完全一致し、乱数の消費順も
            # 従来と変わらない（既存テストの初期値前提を保つ）。
            "Wc": _pad_cols(s(H_CTX, len(ZONES) * H_TOK + GLOB), TRACK),
            "bc": np.zeros(H_CTX, np.float32),
            # 価値ヘッドは [ctx, 特権ベクトル] を入力にする（特権なしでは後半 0）
            "Wv1": _pad_cols(s(H_MID, H_CTX), H_PRIV),
            "bv1": np.zeros(H_MID, np.float32),
            "wv2": s(1, H_MID), "bv2": np.zeros(1, np.float32),
            "Wk": s(MAXK + 1, H_CTX), "bk": np.zeros(MAXK + 1, np.float32),
            "Wo1": s(H_MID, H_CTX + D_EMB + OPT_NUM), "bo1": np.zeros(H_MID, np.float32),
            "wo2": s(1, H_MID), "bo2": np.zeros(1, np.float32),
            # 特権分岐（相手の手札トークンの平均 → tanh 投影）は辞書の
            # 最後に置く: Wpv の乱数を最後に引くことで、他のパラメータの
            # 乱数消費は従来と変わらない。Wv1 の特権列がゼロのため初期の
            # 価値への寄与は 0 で、Wpv の乱数は対称性を壊すためにある。
            "Wpv": s(H_PRIV, D_EMB + TOK_NUM),
            "bpv": np.zeros(H_PRIV, np.float32),
        }
        self.vocab_size = vocab_size
        self._adam_m = {k: np.zeros_like(v) for k, v in self.p.items()}
        self._adam_v = {k: np.zeros_like(v) for k, v in self.p.items()}
        self._adam_t = 0

    # ---- カード表現のフック（Phase 26-4） ----
    # 埋め込みの参照と勾配の蓄積はこの2つに集約する。既定は ID 埋め込み
    # テーブルそのもので、model_attr.AttrModel が「属性ベクトルの射影」
    # に差し替える。他の部品（トランク、ヘッド、集約、特権分岐）は
    # 表現の出所を知らない。
    def _embed(self, idx):
        return self.p["emb"][idx]

    def _embed_grad(self, grads, idx, g):
        np.add.at(grads["emb"], idx, g)

    # ---- トランク（局面ベクトルまで）。AttnModel が差し替える ----
    def _trunk(self, st: dict):
        p = self.p
        emb_tok = self._embed(st["tok_defn"])                    # [T, D]
        x = np.concatenate([emb_tok, st["tok_num"]], axis=1)     # [T, D+TOK]
        h = _tanh(x @ p["W1"].T + p["b1"])                       # [T, H_TOK]
        # ゾーン別プーリング（Phase 7 でベクトル化。旧実装はゾーンごとのマスクループ）
        zone_vecs = np.zeros((len(ZONES), H_TOK), np.float32)
        np.add.at(zone_vecs, st["tok_zone"], h)
        cnt = np.bincount(st["tok_zone"], minlength=len(ZONES)).astype(np.float32)
        zone_vecs /= np.maximum(cnt, 1.0)[:, None]
        ctx_in = np.concatenate([zone_vecs.reshape(-1), full_glob(st)])
        ctx = _tanh(ctx_in @ p["Wc"].T + p["bc"])                # [H_CTX]
        return ctx, (x, h, ctx_in, ctx, cnt)

    def _trunk_backward(self, grads, st: dict, tcache, dctx):
        x, h, ctx_in, ctx, cnt = tcache
        p = self.p
        dctx_in = (dctx * (1 - ctx ** 2)) @ p["Wc"]
        grads["Wc"] += (dctx * (1 - ctx ** 2))[:, None] * ctx_in[None, :]
        grads["bc"] += dctx * (1 - ctx ** 2)
        dzone = dctx_in[:len(ZONES) * H_TOK].reshape(len(ZONES), H_TOK)
        dh = dzone[st["tok_zone"]] / cnt[st["tok_zone"]][:, None]
        self._token_backward(grads, st, x, h, dh)

    def _token_backward(self, grads, st: dict, x, h, dh):
        """h = tanh(x @ W1.T + b1) の逆伝播（dh は h への勾配）。"""
        p = self.p
        dhp = dh * (1 - h ** 2)
        dx = dhp @ p["W1"]
        grads["W1"] += dhp.T @ x
        grads["b1"] += dhp.sum(axis=0)
        self._embed_grad(grads, st["tok_defn"], dx[:, :D_EMB])

    # ---- 特権分岐（学習時のみ: 相手の手札の集約 → 価値ヘッド専用入力） ----
    def _priv(self, st: dict):
        """st に "priv_defn" があれば相手の手札の集約ベクトルを返す。

        戻り: (priv_vec[H_PRIV], cache)。特権情報が無い局面（対戦時・
        通常の軌跡）ではゼロベクトルを返し、価値は非特権の値になる。"""
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
        self._embed_grad(grads, st["priv_defn"], dx[:, :D_EMB])

    # ---- ヘッド（局面ベクトル→スコア/価値/個数） ----
    def _heads(self, ctx, op: dict, priv=None):
        p = self.p
        pv, pcache = priv if priv is not None else (
            np.zeros(H_PRIV, np.float32), None)
        vin = np.concatenate([ctx, pv])
        hv = _tanh(vin @ p["Wv1"].T + p["bv1"])
        value = float(hv @ p["wv2"][0] + p["bv2"][0])
        count_logits = ctx @ p["Wk"].T + p["bk"]                 # [MAXK+1]
        emb_opt = self._embed(op["opt_defn"])                    # [O, D]
        ox = np.concatenate([
            np.broadcast_to(ctx, (len(emb_opt), H_CTX)), emb_opt, op["opt_num"],
        ], axis=1)
        ho = _tanh(ox @ p["Wo1"].T + p["bo1"])
        scores = ho @ p["wo2"][0] + p["bo2"][0]                  # [O]
        return scores, value, count_logits, (hv, ox, ho, vin, pcache)

    def _heads_backward(self, grads, st: dict, op: dict, ctx, hcache,
                        dscores, dcount, dvalue):
        hv, ox, ho, vin, pcache = hcache
        p = self.p
        dho = dscores[:, None] * p["wo2"][0][None, :] * (1 - ho ** 2)
        grads["wo2"][0] += (dscores[:, None] * ho).sum(axis=0)
        grads["bo2"][0] += dscores.sum()
        dox = dho @ p["Wo1"]
        grads["Wo1"] += dho.T @ ox
        grads["bo1"] += dho.sum(axis=0)
        dctx = dox[:, :H_CTX].sum(axis=0)
        demb_opt = dox[:, H_CTX:H_CTX + D_EMB]
        self._embed_grad(grads, op["opt_defn"], demb_opt)
        dhv = dvalue * p["wv2"][0] * (1 - hv ** 2)
        grads["wv2"][0] += dvalue * hv
        grads["bv2"][0] += dvalue
        dvin = dhv @ p["Wv1"]
        dctx += dvin[:H_CTX]
        grads["Wv1"] += dhv[:, None] * vin[None, :]
        grads["bv1"] += dhv
        # 特権分岐への勾配は価値からだけ流れる（方策・個数には接続しない）
        self._priv_backward(grads, st, pcache, dvin[H_CTX:])
        dctx += dcount @ p["Wk"]
        grads["Wk"] += dcount[:, None] * ctx[None, :]
        grads["bk"] += dcount
        return dctx

    # ---- forward ----
    def forward(self, st: dict, op: dict):
        ctx, tcache = self._trunk(st)
        scores, value, count_logits, hcache = self._heads(
            ctx, op, priv=self._priv(st))
        return scores, value, count_logits, (tcache, hcache, ctx)

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

    def act(self, st: dict, op: dict, rng, greedy: bool = False,
            aggregate: bool = False):
        scores, value, count_logits, _ = self.forward(st, op)
        mn, mx = op["min"], op["max"]
        grp = op.get("grp") if aggregate else None
        if grp is not None and mn == 1 and mx == 1:
            # 単一選択の集約: グループ確率で選び、代表を返す。
            # 結果の分布は非集約時と同一（同値手の結果は同じため）。
            reps, glp = group_log_probs(scores, grp)
            if greedy:
                j = int(np.argmax(glp))
                return [reps[j]], 0.0, value
            pr = np.exp(glp - glp.max())
            pr /= pr.sum()
            j = int(rng.choice(len(reps), p=pr))
            return [reps[j]], float(glp[j]), value
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
    def loss_and_grads(self, batch: list[dict], value_coef: float = 0.5,
                       aggregate: bool = False):
        """batch: [{st, op, choice, ret}]。ret はその決定をしたプレイヤーの最終勝敗（+1/-1）。"""
        grads = {k: np.zeros_like(v) for k, v in self.p.items()}
        total = 0.0
        for item in batch:
            st, op, choice, ret = item["st"], item["op"], item["choice"], item["ret"]
            scores, value, count_logits, cache = self.forward(st, op)
            tcache, hcache, ctx = cache
            adv = ret - value
            # スコアへの勾配: PL logp の勾配 × (-adv)
            grp = _agg_target(op, choice, aggregate)
            if grp is not None:
                # 集約: logp はグループ確率、勾配はグループ内 softmax で一般化
                _reps, glp = group_log_probs(scores, grp)
                gpos = int(np.nonzero(
                    np.unique(np.asarray(grp)) == grp[choice[0]])[0][0])
                logp = float(glp[gpos])
                dscores = _group_dscores(scores, grp, choice[0], adv)
            else:
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

            dctx = self._heads_backward(grads, st, op, ctx, hcache, dscores, dcount, dvalue)
            self._trunk_backward(grads, st, tcache, dctx)
        n = max(1, len(batch))
        for k in grads:
            grads[k] /= n
        return total / n, grads

    def bc_loss_and_grads(self, batch: list[dict], aggregate: bool = False):
        """模倣学習（BC）専用の損失と勾配（Phase 18）。

        loss_and_grads と違い、方策の勾配の重みを常に 1 に固定し
        （= 教師の選択の log 確率を最大化）、価値ヘッドには触れない。
        個数ヘッドも教師の個数に合わせる。"""
        grads = {k: np.zeros_like(v) for k, v in self.p.items()}
        total = 0.0
        for item in batch:
            st, op, choice = item["st"], item["op"], item["choice"]
            scores, value, count_logits, cache = self.forward(st, op)
            tcache, hcache, ctx = cache
            grp = _agg_target(op, choice, aggregate)
            if grp is not None:
                _reps, glp = group_log_probs(scores, grp)
                gpos = int(np.nonzero(
                    np.unique(np.asarray(grp)) == grp[choice[0]])[0][0])
                logp = float(glp[gpos])
                dscores = _group_dscores(scores, grp, choice[0], 1.0)
            else:
                dscores = np.zeros_like(scores)
                rest = list(range(len(scores)))
                logp = 0.0
                for c in choice:
                    sc = scores[rest]
                    z = sc - sc.max()
                    pr = np.exp(z)
                    pr /= pr.sum()
                    logp += float(np.log(pr[rest.index(c)] + 1e-12))
                    for jj, idx in enumerate(rest):
                        dscores[idx] += pr[jj]
                    dscores[c] -= 1.0
                    rest.remove(c)
            dcount = np.zeros(MAXK + 1, np.float32)
            mn, mx = op["min"], op["max"]
            logp_k = 0.0
            if mn != mx and len(choice) >= mn:
                lo, pr = self._count_dist(count_logits, mn, mx)
                kk = min(len(choice), MAXK)
                if lo <= kk <= min(mx, MAXK):
                    logp_k = float(np.log(pr[kk - lo] + 1e-12))
                    for jj in range(len(pr)):
                        dcount[lo + jj] += pr[jj]
                    dcount[kk] -= 1.0
            logp += logp_k
            total += -logp
            dctx = self._heads_backward(grads, st, op, ctx, hcache, dscores,
                                        dcount, 0.0)
            self._trunk_backward(grads, st, tcache, dctx)
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
        """旧形式の npz（Phase 26-2 以前）もそのまま読める。

        幅が広がったパラメータ（Wc: トラッカー列、Wv1: 特権列）は
        ゼロ埋めで移行し、欠けた特権分岐（Wpv/bpv）は初期化値のまま
        にする（Wv1 の特権列がゼロのため価値への寄与は 0）。したが
        って移行直後のモデルの出力（方策・価値・個数）は旧モデルと
        完全一致する。"""
        z = np.load(path)
        m = cls(int(z["emb"].shape[0]))
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
