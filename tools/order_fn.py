"""順序関数（試作）: 評価関数 V とは別に、ターン境界の局面を並べるための関数。

背景（2026-11-17 の実測、docs/exhaustive-search-saga-report.md §5.6）:
saga_hidden_setup では、最速キルに届くターン1終了局面が V では5位以下に
沈んでいた（V差は60点のみ）。V は葉評価用で、判断点・ターン境界での
解像度が不足する。そこで順序専用に、プロジェクトの段階指標
（dmsim/eval/progress.py の曲線項目）と同じ特徴量で並べる関数を用意する。

特徴量（全て枚数。相手の残りが少ないほど、自分側の蓄積が多いほど前進）:
  - own_gy - own_deck : ゾーン循環の進み（墓地に送り、山札が減るほど前進）
  - -opp_shield       : 相手の盾の残り（少ないほど良い）
  - -opp_deck         : 相手の山札の残り（少ないほど良い）
  - own_bz + own_mana : 盤面とマナの蓄積
  - own_hand          : 手札の蓄積
辞書式（タプル）の順序にし、最後の同点解消にだけ V を使う。

これは「除外」には使わない。保持する局面の優先付け専用。
統計版（探索ログから学習した順序）は、この特徴量版との比較で測る。
"""
from __future__ import annotations

from dmsim.search.leaf_eval import WIN, Weights, evaluate

_W = Weights()


def features(eng, me: int = 0) -> dict:
    z = eng.s.zones
    opp = 1 - me
    n = lambda zone, p: len(z[zone][p])
    return {
        "opp_shield": n("shield", opp),
        "opp_deck": n("deck", opp),
        "own_gy": n("graveyard", me),
        "own_deck": n("deck", me),
        "own_bz": n("bz", me),
        "own_mana": n("mana", me),
        "own_hand": n("hand", me),
    }


def ruler_key(eng, me: int = 0) -> tuple:
    """辞書式の順序キー（大きいほど先に保持する）。

    v2（2026-11-17 改修）: v1 は「墓地−山札」を先頭にしたため、自分の山札を
    ほぼ空にしてしまった局面（墓地21・山札1。次のドローで負ける線）が最上位に
    来てしまい、beam が全滅した（hidden beam4 で NO-KILL）。先頭を
    「次のドローを生き残れるか」に変え、循環の進みは2番目に置く。"""
    f = features(eng, me)
    return (
        1 if f["own_deck"] >= 2 else 0,     # 次のドローで山札切れ負けしない
        f["own_gy"] - f["own_deck"],        # ゾーン循環の進み
        -f["opp_shield"],
        -f["opp_deck"],
        f["own_bz"] + f["own_mana"],
        f["own_hand"],
    )


def ruler_score(eng, me: int = 0) -> float:
    """順序キーを float に符号化したもの（value_fn として差し込む用）。

    TurnSearch は「WIN - 1000 以上＝勝ち線」として打ち切るので、通常局面の
    スコアは WIN より十分小さく収める。終局は evaluate と同じ値を返す。
    （初版は素の符号化が WIN を超え、最初の線で探索が打ち切られて壊れた）"""
    s = eng.s
    if s.result is not None:
        if s.result["winner"] == me:
            return WIN - s.result["turn"]
        if s.result["winner"] == 1 - me:
            return -WIN
        return -WIN / 2
    surv, a, b, c, d, e = ruler_key(eng, me)
    enc = (surv * 100**5 + (a + 50) * 100**4 + (b + 40) * 100**3
           + (c + 40) * 100**2 + d * 100 + e)
    return enc * 1e-5 + evaluate(eng, me, _W) / 10_000_000.0


def make_value_fn(name: str):
    """play_game / TurnSearch の value_fn として渡せる関数を返す。"""
    if name == "value":
        return None                      # 既定の evaluate を使う
    if name == "ruler":
        return lambda eng, me: ruler_score(eng, me)
    raise ValueError(name)
