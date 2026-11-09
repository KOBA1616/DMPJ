"""失敗局の自動分類と、そこからの改善候補の生成（ルールベース。LLM・課金なし）。

diagnose は全体の到達率から段階を1つ決めるが、こちらは局ごとに「どこで落ちたか」を分類し、
割合の大きい順に候補（Knobs の変更・デッキ側の報告）を並べる。採否はここでは決めない
（loop.autofix / tune の同一シード対比較）。入力 m は harness_measure の戻り値（局の並びが同じ kill/board/cards/prep）。"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace

from .loop import Knobs, Rule

CLASSES = ("cards_miss", "board_miss", "prep_unused", "finish_miss", "late_kill")


def _late(x, turn):
    return x is not None and x > turn


def classify_games(m: dict, turn: int = 4) -> list[str]:
    """局ごとの分類。"ok"=turn までにキル、"late_kill"=turn+1 以降にキル（惜しい）、それ以外は落ちた段階。"""
    n = len(m["kill"])
    out = []
    for i in range(n):
        k = m["kill"][i]
        if k is not None and k <= turn:
            out.append("ok")
        elif k is not None:
            out.append("late_kill")
        elif m.get("cards") and (m["cards"][i] is None or m["cards"][i] > turn):
            out.append("cards_miss")
        elif m.get("board") and (m["board"][i] is None or m["board"][i] > turn):
            out.append("board_miss")
        elif m.get("prep") and not m["prep"][i]:
            out.append("prep_unused")
        else:
            out.append("finish_miss")
    return out


def summarize(m: dict, turn: int = 4) -> dict:
    cl = classify_games(m, turn)
    c = Counter(cl)
    n = len(cl) or 1
    return {"n": len(cl), "ok_rate": c["ok"] / n, "shares": {k: c[k] / n for k in CLASSES},
            "seeds": {k: [i for i, x in enumerate(cl) if x == k] for k in CLASSES}}


def propose_from_failures(m: dict, k: Knobs, rule: Rule = Rule(), min_share: float = 0.1) -> list[dict]:
    """割合が min_share 以上の失敗クラスごとに候補を作り、割合の大きい順に返す。
    各要素: {class, share, why, knobs(Knobs|None), deck_hint(str|None)}。cards_miss はデッキ側の問題なので deck_hint のみ。"""
    s = summarize(m, rule.turn)
    out = []

    def add(cls, why, knobs=None, deck_hint=None):
        out.append({"class": cls, "share": s["shares"][cls], "why": why, "knobs": knobs, "deck_hint": deck_hint})
    for cls, share in sorted(s["shares"].items(), key=lambda kv: -kv[1]):
        if share < min_share:
            continue
        if cls == "cards_miss":
            add(cls, "部品が見える所に揃わない", deck_hint="デッキの部品枚数・引き込み札を増やす候補を deckplan で評価（自動採用しない）")
        elif cls == "board_miss":
            if k.coef * 2 <= rule.coef_max:
                add(cls, "部品倍率を2倍", replace(k, coef=k.coef * 2))
            if k.gy_mult * 2 <= 8:
                add(cls, "墓地の部品の重みを2倍", replace(k, gy_mult=k.gy_mult * 2))
        elif cls == "prep_unused":
            nb = k.prep_bonus * 2 if k.prep_bonus else 10.0
            if nb <= 80:
                add(cls, "準備札を撃つ加点", replace(k, prep_bonus=nb))
        elif cls in ("finish_miss", "late_kill"):
            if k.lookahead + 1 <= rule.lookahead_max:
                add(cls, "先読み(lookahead)を+1", replace(k, lookahead=k.lookahead + 1))
            if k.budget * 2 <= rule.budget_max:
                add(cls, "探索予算を2倍", replace(k, budget=k.budget * 2))
            if k.finish_mult == 0.0:
                add(cls, "締めの束を加える", replace(k, finish_mult=1.0))
            if k.n_det * 2 <= rule.n_det_max:
                add(cls, "決定化数を2倍", replace(k, n_det=k.n_det * 2))
    return out
