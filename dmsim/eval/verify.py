"""登録簿へ書く前の検証（S4、docs/registry-design.md §3）。登録簿（dmsim.base.registry）へ書くのはここの register だけ。

検証は順に行い、最初に落ちた所で止める（どこで落ちたかを rejected に残す）:
1. cards   … 中核の札に ID があり、カードデータにある。
2. type    … 今の物差しで測れる型か。ループ型・ロック型（受け身）は測れる。リソース型・攻撃型だけの候補は目盛りが未実装（設計書 §6 タスク11・12）。
3. entry   … 入口局面（data/loops/entry/*.json）があって読める。手順の文だけでは再生できない。
   能動ロック（lock_mode="active"）は entry の代わりに setup（ロック成立の局面）と policy（与えた自分の方針）を使い、
   4 を lock に置き換える: lockcheck.run_lock_to_end を prefer_policy(*policy) で回し、相手の山札切れまで勝てた割合が KNOWN_MIN 以上。
   受け身の lock_probe を前提にする make_full_lock_judge は能動ロックを見つけられないので使わない（§8.2）。
4. ruler   … 物差し（ruler.judge）で、入口をシードで配り直した局面を各シード1局（ruler_control.run_one と同じ測り方）。
             段2（ループ・ロックによる勝ち）の到達率が KNOWN_MIN 以上。対局の失敗が混ざれば不合格。
5. replay  … 同じシードをもう一度回して、開始局面の指紋・段1・段2・勝ち方・勝ったターンが一致する（再現性）。

数字を合わせる調整はしない: 閾値は陽性対照と同じ KNOWN_MIN、測り方は入口局面の既定（budget）をそのまま使う。
"""
from __future__ import annotations

import datetime as _dt
import subprocess

from ..base import registry
from ..base.registry import Candidate, Evidence
from ..base.store import REPO
from ..base.loopspec import LoopSpec
from . import loop_entry as le
from .ruler_control import KNOWN_MIN, run_one

MEASURABLE = ("loop", "lock")
REPLAY_SEEDS = 2


def _commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True, timeout=10).stdout.strip() or None
    except Exception:
        return None


def _version() -> dict:
    from .validity import fingerprint
    return {"fingerprint": fingerprint(REPO), "commit": _commit(), "measured_at": _dt.date.today().isoformat()}


def _key(row: dict) -> tuple:
    return (row["start"], row["stage1"], row["stage2"], row["via"], row["win_turn"], row["error"])


def verify(rules, cand: Candidate, *, known_min: float = KNOWN_MIN) -> Evidence:
    checks: list[dict] = []
    measured: dict = {}

    def done(passed: bool) -> Evidence:
        return Evidence(cand.digest(), passed, checks, measured, _version(), registry.ISSUER)

    def step(name: str, ok: bool, detail: str) -> bool:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
        return ok

    missing = [c.get("name") for c in cand.core if not c.get("id") or c["id"] not in rules.cards]
    if not step("cards", not missing and bool(cand.core), "中核の札がカードデータにある" if not missing else f"ID が無いかカードデータに無い: {missing}"):
        return done(False)
    if not set(cand.types) & set(MEASURABLE):
        step("type", False, f"型 {cand.types} は今の物差しで測れない（リソース型はタスク12、攻撃型はタスク11 が前提）")
        return done(False)
    if cand.lock_mode == "active":
        step("type", True, "lock（能動）として相手の山札切れまで回す")
        return done(_active_lock(rules, cand, step, measured, known_min))
    step("type", True, f"{'/'.join(t for t in cand.types if t in MEASURABLE)} として段1・段2で測る")
    if not cand.entry:
        step("entry", False, "入口局面が無い（手順の文だけでは再生できない）")
        return done(False)
    try:
        ls = LoopSpec.from_json((REPO / cand.entry).read_text(encoding="utf-8"))
    except Exception as ex:   # noqa: BLE001
        step("entry", False, f"入口局面を読めない: {ex}")
        return done(False)
    step("entry", True, f"{cand.entry}（{ls.name}）")

    rows = [run_one(rules, ls, s, max_turn=cand.max_turn, budget=cand.budget) for s in cand.seeds]
    n = len(rows)
    vias: dict[str, int] = {}
    for r in rows:
        vias[str(r["via"])] = vias.get(str(r["via"]), 0) + 1
    s1 = sum(r["stage1"] for r in rows)
    s2 = sum(r["stage2"] for r in rows)
    errs = [r["seed"] for r in rows if r["error"]]
    turns = sorted({r["win_turn"] for r in rows if r["stage2"] and r["win_turn"] is not None})
    measured.update({"seeds": cand.seeds, "max_turn": cand.max_turn, "budget": cand.budget if cand.budget is not None else ls.source.get("budget", 200),
                     "stage1": f"{s1}/{n}", "stage2": f"{s2}/{n}", "stage2_rate": round(s2 / n, 3) if n else 0.0,
                     "via": vias, "win_turns": turns, "threshold": known_min,
                     "rows": [{k: r[k] for k in ("seed", "start", "stage1", "stage2", "via", "win_turn")} for r in rows]})
    ok = n > 0 and not errs and s2 / n >= known_min
    if not step("ruler", ok, f"段1 {s1}/{n}・段2 {s2}/{n}（基準 {known_min}）勝ち方 {vias}" + (f"、対局の失敗 seed {errs}" if errs else "")):
        return done(False)
    again = [run_one(rules, ls, s, max_turn=cand.max_turn, budget=cand.budget) for s in cand.seeds[:REPLAY_SEEDS]]
    diff = [a["seed"] for a, b in zip(again, rows) if _key(a) != _key(b)]
    if not step("replay", not diff, f"seed {cand.seeds[:REPLAY_SEEDS]} を回し直して一致" if not diff else f"回し直すと結果が変わる seed {diff}"):
        return done(False)
    return done(True)


def _lock_row(rules, spec: dict, seed: int, policy: list[str]) -> dict:
    from ..engine import scenario
    from .lockcheck import prefer_policy, run_lock_to_end
    from .ruler_control import start_key
    e = scenario.build(rules, {**spec, "seed": seed}, first_player=0)
    run = run_lock_to_end(e, 0, my_policy=prefer_policy(*policy))
    return {"seed": seed, "start": start_key(e), "stage1": False, "stage2": run.won, "via": "lock" if run.won else None,
            "win_turn": run.win_turn, "error": None, "own_deck_left": run.own_deck_left, "broken": run.broken}


def _active_lock(rules, cand: Candidate, step, measured: dict, known_min: float) -> bool:
    import json
    if not cand.setup or not cand.policy:
        return step("entry", False, "能動ロックには setup（成立局面）と policy（与える方針）が要る")
    try:
        spec = {k: v for k, v in json.loads((REPO / cand.setup).read_text(encoding="utf-8")).items() if k != "note"}
    except Exception as ex:   # noqa: BLE001
        return step("entry", False, f"成立局面を読めない: {ex}")
    step("entry", True, f"{cand.setup}、与えた方針 {cand.policy}")
    rows = [_lock_row(rules, spec, s, cand.policy) for s in cand.seeds]
    n, won = len(rows), sum(r["stage2"] for r in rows)
    starts = len({r["start"] for r in rows})
    measured.update({"seeds": cand.seeds, "lock_mode": "active", "policy": cand.policy, "stage1": "対象外（ロックは段2の経路）",
                     "stage2": f"{won}/{n}", "stage2_rate": round(won / n, 3) if n else 0.0, "threshold": known_min,
                     "distinct_starts": starts, "rows": [{k: r[k] for k in ("seed", "start", "stage2", "win_turn", "own_deck_left", "broken")} for r in rows]})
    if not step("lock", n > 0 and won / n >= known_min,
                f"相手の山札切れまで勝ち {won}/{n}（基準 {known_min}）、開始局面 {starts} 種、勝ったターン {sorted({r['win_turn'] for r in rows if r['stage2']})}、"
                f"自分の山札残り {sorted({r['own_deck_left'] for r in rows})}"):
        return False
    again = [_lock_row(rules, spec, s, cand.policy) for s in cand.seeds[:REPLAY_SEEDS]]
    diff = [a["seed"] for a, b in zip(again, rows) if _key(a) != _key(b)]
    return step("replay", not diff, f"seed {cand.seeds[:REPLAY_SEEDS]} を回し直して一致" if not diff else f"回し直すと結果が変わる seed {diff}")


def register(rules, cand: Candidate, *, path=registry.PATH, purpose: str = "eval") -> tuple[Evidence, dict]:
    """検証して登録簿に書く（通れば entries、落ちれば rejected）。調整用の経路は purpose="tuning"（holdout は書けない）。"""
    ev = verify(rules, cand)
    return ev, registry.record(cand, ev, path=path, purpose=purpose)
