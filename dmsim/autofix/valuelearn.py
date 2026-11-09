"""経験ログからの価値の学習（小規模・LLMなし）。自己対戦の各ターンの局面から「その局のキルの早さ」を回帰し、
葉の評価へ**順位付けの加点**として足す（足切りには使わない）。加点の大きさ learned_mult は進化＋再確認で採否を決める。

- 特徴は自分側の見えるゾーンの枚数・部品の所持数・相手の盾/山札の枚数だけ（相手の山札の中身は使わない＝公平探索のまま）。
- 学習は標準化したリッジ回帰（外部ライブラリなし）。ラベルは局ごとの -(キルターン。未キルは max_turn+1)。
- データは版つきで追記（data/autofix/value_data/<combo>.jsonl、直近 MAX_ROWS 行）。日を重ねるほど増える。"""
from __future__ import annotations

import json
from pathlib import Path

SCALE = 20.0          # 回帰出力（ターン単位）を葉の評価の尺度へ合わせる倍率（evaluate の打点項は +40 / 体）
MAX_ROWS = 6000
VERSION = "v0"


def feature_names(spec) -> list[str]:
    return ["own_hand", "own_mana", "own_bz", "own_gy", "opp_shield", "opp_deck"] + [f"part:{p.zone}:{'|'.join(p.ids)}" for p in spec.parts if p.ids]


def features(snap: dict, spec) -> list[float]:
    """snapshot（dmsim.eval.progress.snapshot）→ 特徴ベクトル。データ作成時と葉の評価時で同じ関数を使う。"""
    v = [snap["own_hand"], snap["own_mana"], snap["own_bz"], snap["own_gy"], snap["opp_shield"], snap["opp_deck"]]
    defs = snap.get("defs") or {}
    for p in spec.parts:
        if p.ids:
            z = defs.get(p.zone) or {}
            v.append(min(sum(z.get(i, 0) for i in p.ids), p.need))
    return [float(x) for x in v]


def rows_from_curves(curves: list, kill: list, spec, max_turn: int) -> list[list]:
    """局ごとの曲線 → 学習行 [特徴..., ラベル]。ターン0（開始時）は除く。"""
    rows = []
    for cv, k in zip(curves, kill):
        if k is None:      # 未キルは最悪点＋相手の盾をどれだけ割ったかの小さな加点（1ターン分未満。勝ちが全く出ない対象でも学習できるように）
            last = cv[-1] if cv else {}
            y = -float(max_turn + 1) + 0.5 * (1.0 - min(5, last.get("opp_shield", 5)) / 5.0)
        else:
            y = -float(k)
        for s in cv:
            if s.get("turn", 0) >= 1 and s.get("defs") is not None:
                rows.append(features(s, spec) + [y])
    return rows


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        d = m[c][c] or 1e-12
        for j in range(c, n + 1):
            m[c][j] /= d
        for r in range(n):
            if r != c and m[r][c]:
                f = m[r][c]
                for j in range(c, n + 1):
                    m[r][j] -= f * m[c][j]
    return [m[i][n] for i in range(n)]


def fit(rows: list[list[float]], lam: float = 1.0, min_rows: int = 30) -> dict | None:
    """標準化リッジ回帰。行が少ない・ラベルに差が無い時は None（学習しない）。"""
    if len(rows) < min_rows:
        return None
    d = len(rows[0]) - 1
    n = len(rows)
    mu = [sum(r[j] for r in rows) / n for j in range(d)]
    sd = [(sum((r[j] - mu[j]) ** 2 for r in rows) / n) ** 0.5 or 1.0 for j in range(d)]
    ym = sum(r[d] for r in rows) / n
    if all(abs(r[d] - ym) < 1e-9 for r in rows):
        return None
    z = [[(r[j] - mu[j]) / sd[j] for j in range(d)] for r in rows]
    xtx = [[sum(z[k][i] * z[k][j] for k in range(n)) + (lam if i == j else 0.0) for j in range(d)] for i in range(d)]
    xty = [sum(z[k][i] * (rows[k][d] - ym) for k in range(n)) for i in range(d)]
    return {"version": VERSION, "mu": mu, "sd": sd, "w": _solve(xtx, xty), "n": n}


def score(model: dict, x: list[float]) -> float:
    return sum(w * (v - m) / s for w, v, m, s in zip(model["w"], x, model["mu"], model["sd"]))


def with_learned(value_fn, model: dict, spec, mult: float):
    """葉の評価 value_fn に、学習した価値 × mult × SCALE を足した関数（順位付けの補助。終局では足さない）。"""
    from ..eval.progress import snapshot

    def value(eng, me):
        v = value_fn(eng, me)
        if eng.s.result is not None:
            return v
        return v + mult * SCALE * score(model, features(snapshot(eng, me, 1), spec))
    return value


def append_rows(path: str, rows: list[list[float]], names: list[str]) -> list[list[float]]:
    """行を追記し、直近 MAX_ROWS 行を返す。特徴の並びが変わっていたら（部品表が変わった）作り直す。"""
    p = Path(path)
    old: list[list[float]] = []
    if p.exists():
        head, *body = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        if head.get("names") == names:
            old = body
    allrows = (old + rows)[-MAX_ROWS:]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join([json.dumps({"version": VERSION, "names": names}, ensure_ascii=False)] + [json.dumps(r) for r in allrows]) + "\n", encoding="utf-8")
    return allrows


def model_path(combo: str, root: str = "data/autofix/value_models") -> Path:
    return Path(root) / f"{combo}.json"


def load_model(combo: str, root: str = "data/autofix/value_models") -> dict | None:
    p = model_path(combo, root)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save_model(combo: str, model: dict, root: str = "data/autofix/value_models") -> None:
    p = model_path(combo, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")


MULTS = (0.0, 0.5, 1.0, 2.0, 4.0, 8.0)
