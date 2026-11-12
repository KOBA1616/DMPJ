"""評価関数 V の採否ゲート（docs/value-function-design.md §7）。
段階目標の鎖（data/eval/stages/<コンボ>.yaml）への到達数を、手で決めた順位づけ（base）と v_priority の重み候補で、同じ seed・同じ強制開始から比べる。
採用は「合計の到達段階数が base 以上で、かつ base を上回る」候補だけ（同点・下回りは採らない）。足切りには使わない（順位づけの補助）。"""
from __future__ import annotations

import time
from functools import partial

import yaml
from .cost_perf import make_term as cost_term
from .lock_terms import make_term as lock_make
from .key_terms import make_term

from ..discovery.bestfirst import priority
from ..engine.core import Engine
from ..engine_view import force_hand
from ..play_api import InfoLevel, PlayConfig, play
from .vfeatures import macro_prio, v_priority

GRID = ((3.0, 1.0), (6.0, 1.0), (6.0, 3.0), (10.0, 3.0),
        (0.0, 0.0, -0.1), (0.0, 0.0, -0.3), (0.0, 0.0, -1.0))     # (under_w, res_w[, plan_w[, key_pen[, cost_scale[, lock_w]]]])。(0, 0) は base と同じ。plan_w<0 は計画項を基本スコアの標準偏差の -plan_w 倍にする（正規化、macro_prio）


def stage_path(combo: str, root: str = "data/eval/stages") -> str | None:
    """手書きの <combo>.yaml を優先し、無ければ自動生成の <combo>.generated.yaml（tools/gen_stages.py）。どちらも無ければ None。"""
    from pathlib import Path
    for name in (f"{combo}.yaml", f"{combo}.generated.yaml"):
        if (Path(root) / name).exists():
            return str(Path(root) / name)
    return None


def load_stages(path) -> dict:
    return yaml.safe_load(open(path, encoding="utf-8"))


def start_engine(rules, deck, opp_deck, keys, seed):
    e = Engine.new_game(rules, [deck, opp_deck], seed, first_player=0)
    return e if force_hand(e, 0, keys) else None


def chain_score(rules, deck, opp_deck, keys, stages, seeds, prio, width=150, max_depth=80, max_turn=14, deadline=None, keep_later=True, lookahead=2) -> dict:
    """seed ごとの到達段階数。deadline(time.time()) を過ぎたら残りの seed は測らない（打ち切り）。"""
    out, by_seed = [], {}
    for sd in seeds:
        if deadline and time.time() > deadline:
            break
        e = start_engine(rules, deck, opp_deck, keys, sd)
        if e is None:   # この seed は強制開始の札が山札に無い（盾などに落ちた）。測れないので飛ばす（全 seed で同じ seed が飛ぶ）
            continue
        cfg = PlayConfig(mode="chain", stages=tuple(stages), keep_later=keep_later, chain_lookahead=lookahead, width=width,
                         max_depth=max_depth, max_turn=max_turn, prio=prio)
        out.append(play(e, cfg, InfoLevel.CHEAT).stages)   # 段階探索は真の山札順を見る（CHEAT）。V の順位づけ比較のみに使う
        by_seed[sd] = out[-1]
    return {"stages": out, "total": sum(out), "by_seed": by_seed}


MIN_ADOPT_N = 8   # 採用候補にする最小局数。時間切れで n がこれ未満なら verdict は "adopt" にせず "small_n"（n=2 の偶然で手入力値を上書きしないため）


def run_gate(rules, deck, opp_deck, keys, stages, seeds, grid=GRID, deadline=None, min_n=MIN_ADOPT_N, **kw) -> dict:
    """base と各重みを同じ seed で測る。打ち切られて seed 数が違うときは短い方に揃えて比べる。"""
    # 時間の上限は base と各重みで等分する（先頭の base が全部使うと他が 0 seed になり n=0 になる）
    k = 1 + len(grid)
    t_start = time.time()
    slice_ = ((deadline - t_start) / k) if deadline else 0

    def dl(i):
        return (t_start + slice_ * (i + 1)) if deadline else None
    base = chain_score(rules, deck, opp_deck, keys, stages, seeds, None, deadline=dl(0), **kw)
    rows = []
    for gi, (u, r, *ex) in enumerate(grid, 1):
        prio, pw, kp = row_prio(stages, (u, r, *ex))
        rows.append({"under_w": u, "res_w": r, "plan_w": pw, "key_pen": kp, **chain_score(rules, deck, opp_deck, keys, stages, seeds, prio, deadline=dl(gi), **kw)})
    n = min([len(base["stages"])] + [len(x["stages"]) for x in rows])
    b = sum(base["stages"][:n])
    for x in rows:
        x["total_n"] = sum(x["stages"][:n])
        x["verdict"] = ("adopt" if n >= min_n else "small_n") if (n and x["total_n"] > b) else ("tie" if x["total_n"] == b else "worse")
    best = max((x for x in rows if x["verdict"] == "adopt"), key=lambda x: x["total_n"], default=None)
    return {"n": n, "base_total": b, "base": base["stages"][:n], "rows": rows, "best": best, "base_by_seed": base.get("by_seed", {})}


def row_prio(stages, row):
    """grid の1行 (under_w, res_w[, plan_w[, key_pen[, cost_scale[, lock_w]]]]) から順位づけ関数を作る。(prio, plan_w, key_pen) を返す。"""
    u, r, *ex = row
    pw = ex[0] if ex else 0.0
    kp = ex[1] if len(ex) > 1 else 0.0          # 4つ目: 部品札をマナに置く減点（key_terms、枚あたり）。0=なし
    cs = ex[2] if len(ex) > 2 else 0.0          # 5つ目: コスト対パフォーマンス項の倍率(cost_perf)。0=なし
    lw = ex[3] if len(ex) > 3 else 0.0          # 6つ目: 継続効果ロック項の係数 lock_w（lock_terms、recur_w も同じ値）。0=なし
    terms = ((make_term(stages, kp),) if kp else ()) + ((cost_term(scale=cs),) if cs else ()) + ((lock_make(lock_w=lw, recur_w=lw),) if lw else ())
    prio = macro_prio(stages, pw, under_w=u, res_w=r, terms=terms) if pw else partial(_vp, under_w=u, res_w=r, terms=terms)
    return prio, pw, kp


def _vp(eng, me, w, under_w, res_w, terms=()):
    return v_priority(eng, me, w, priority, under_w=under_w, res_w=res_w, terms=terms)


# ---- 日をまたいだ積み上げ（1日の枠では MIN_ADOPT_N 局に届かないため。data/autofix/vgate_acc.yaml）----
MAX_ACC_N = 24      # どの候補も積み上げがこの局数に達したら判定して積み上げを作り直す


def cand_key(row) -> str:
    return ":".join(str(row.get(k, 0.0)) for k in ("under_w", "res_w", "plan_w", "key_pen"))


def accumulate(acc: dict, result: dict) -> dict:
    """run_gate の結果（by_seed 付き）を acc（{"base": {seed: 段数}, <cand_key>: {seed: 段数}}）へ足す。同じ seed は上書き。"""
    acc.setdefault("base", {}).update({int(k): v for k, v in (result.get("base_by_seed") or {}).items()})
    for x in result["rows"]:
        acc.setdefault(cand_key(x), {}).update({int(k): v for k, v in (x.get("by_seed") or {}).items()})
    return acc


def judge_acc(acc: dict, rows, min_n: int = MIN_ADOPT_N) -> dict:
    """積み上げた結果から候補ごとに base と同じ seed だけで比べる。採用は『その候補の共通局数 >= min_n かつ base を厳密に上回る』もののみ。"""
    base = {int(k): v for k, v in (acc.get("base") or {}).items()}
    out = []
    for x in rows:
        c = {int(k): v for k, v in (acc.get(cand_key(x)) or {}).items()}
        common = sorted(set(base) & set(c))
        b, t = sum(base[i] for i in common), sum(c[i] for i in common)
        v = ("adopt" if len(common) >= min_n else "small_n") if (common and t > b) else ("tie" if t == b else "worse")
        out.append({**{k: x.get(k, 0.0) for k in ("under_w", "res_w", "plan_w", "key_pen")}, "n": len(common), "base_total": b, "total_n": t, "verdict": v})
    best = max((x for x in out if x["verdict"] == "adopt"), key=lambda x: x["total_n"] - x["base_total"], default=None)
    return {"rows": out, "best": best, "n": min((x["n"] for x in out), default=0)}


def next_seed(acc: dict) -> int:
    """次に測る最初の seed。各系列（base と候補）の最大 seed のうち一番小さいものの次（無ければ 1）。遅れている候補に合わせる（時間切れで候補ごとに進み方が違うため）。"""
    tops = [max(int(k) for k in v) for v in acc.values() if v]
    return (min(tops) if tops else 0) + 1


# ---- 勝ちの測定（到達段でなく、通しターン T 以内に勝てるか・最速の勝ちターン。ビーム探索、強制開始の札あり）----
WIN_TURN = 12      # ビームの上限（通しターン）。これ以内に勝てなければ負け扱い
EARLY_TURN = 8     # 「早い勝ち」の基準（通しターン）


def win_score(rules, deck, opp_deck, keys, seeds, prio, width=40, max_depth=80, max_turn=WIN_TURN, deadline=None) -> dict:
    """seed ごとの勝ちターン（勝てなければ None）。{seed: turn|None}"""
    out = {}
    for sd in seeds:
        if deadline and time.time() > deadline:
            break
        e = start_engine(rules, deck, opp_deck, keys, sd)
        if e is None:
            continue
        r = play(e, PlayConfig(mode="beam", width=width, max_depth=max_depth, max_turn=max_turn, prio=prio), InfoLevel.CHEAT)
        out[sd] = r.kill_turn
    return out


def win_stats(turns: dict, seeds=None, early: int = EARLY_TURN) -> dict:
    t = [v for k, v in turns.items() if seeds is None or k in seeds]
    w = [v for v in t if v is not None]
    return {"n": len(t), "wins": len(w), "early": sum(1 for v in w if v <= early),
            "fastest": min(w) if w else None, "mean_win_turn": round(sum(w) / len(w), 2) if w else None}


def win_key(st: dict) -> tuple:
    """大きいほど良い: (早い勝ちの数, 勝ちの数, -勝ちターン平均)。"""
    return (st["early"], st["wins"], -(st["mean_win_turn"] if st["mean_win_turn"] is not None else 99.0))


def run_win_gate(rules, deck, opp_deck, keys, stages, seeds, grid=GRID, width=40, max_turn=WIN_TURN, early=EARLY_TURN,
                 deadline=None, min_n=MIN_ADOPT_N) -> dict:
    """base と各重みを同じ seed で、勝ちの数・早い勝ち・最速で比べる（辞書式: 早い勝ち → 勝ち → 勝ちターン平均）。"""
    k = 1 + len(grid)
    t_start = time.time()
    slice_ = ((deadline - t_start) / k) if deadline else 0

    def dl(i):
        return (t_start + slice_ * (i + 1)) if deadline else None
    seeds = list(seeds)
    base = win_score(rules, deck, opp_deck, keys, seeds, None, width=width, max_turn=max_turn, deadline=dl(0))
    rows = []
    for gi, row in enumerate(grid, 1):
        prio, pw, kp = row_prio(stages, row)
        rows.append({"row": list(row), "turns": win_score(rules, deck, opp_deck, keys, seeds, prio, width=width, max_turn=max_turn, deadline=dl(gi))})
    common = set(base)
    for x in rows:
        common &= set(x["turns"])
    n = len(common)
    b = win_stats(base, common, early)
    for x in rows:
        x["stats"] = win_stats(x["turns"], common, early)
        kb, kx = win_key(b), win_key(x["stats"])
        x["verdict"] = ("adopt" if n >= min_n else "small_n") if kx > kb else ("tie" if kx == kb else "worse")
    return {"n": n, "base": b, "rows": rows}


def load_prio(combo: str, stages: list, store: str = "data/autofix/vweights.yaml"):
    """採用済みの重み（vweights.yaml の combo 項）から順位づけ関数を作る。無ければ None（基本の priority）。
    項目: under_w・res_w・plan_w（負なら標準偏差の倍率）・key_pen（部品札をマナに置く減点）。探索側がこれを prio に渡して使う。"""
    from pathlib import Path
    p = Path(store)
    cur = (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}
    w = cur.get(combo)
    if not w:
        return None
    row = (float(w.get("under_w", 0.0)), float(w.get("res_w", 0.0)), float(w.get("plan_w", 0.0)), float(w.get("key_pen", 0.0)))
    if not any(row):
        return None
    return row_prio(stages, row)[0]
