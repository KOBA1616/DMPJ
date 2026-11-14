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
MAX_MACROS = 8      # 勝った局の手順を何本まで残すか（search.macro が1本ずつ手にする）


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
        if "resource" in cand.types:
            step("type", True, "resource としてコスト対アドバンテージを測る（resource.py）")
            return done(_resource(rules, cand, step, measured))
        step("type", False, f"型 {cand.types} は今の物差しで測れない（攻撃型はタスク11 が前提）")
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
    measured.update({"seeds": cand.seeds, "max_turn": cand.max_turn, "budget": le.measure_budget(ls, cand.budget),
                     "stage1": f"{s1}/{n}", "stage2": f"{s2}/{n}", "stage2_rate": round(s2 / n, 3) if n else 0.0,
                     "via": vias, "win_turns": turns, "threshold": known_min,
                     "rows": [{k: r[k] for k in ("seed", "start", "stage1", "stage2", "via", "win_turn")} for r in rows]})
    ok = n > 0 and not errs and s2 / n >= known_min
    if not step("ruler", ok, f"段1 {s1}/{n}・段2 {s2}/{n}（基準 {known_min}）勝ち方 {vias}" + (f"、対局の失敗 seed {errs}" if errs else "")):
        return done(False)
    measured["macros"] = [m for m in (_macro_steps(rules, ls, r["seed"], cand) for r in rows if r["stage2"] and r["win_turn"] == 1)
                          if m is not None][:MAX_MACROS]
    again = [run_one(rules, ls, s, max_turn=cand.max_turn, budget=cand.budget) for s in cand.seeds[:REPLAY_SEEDS]]
    diff = [a["seed"] for a, b in zip(again, rows) if _key(a) != _key(b)]
    if not step("replay", not diff, f"seed {cand.seeds[:REPLAY_SEEDS]} を回し直して一致" if not diff else f"回し直すと結果が変わる seed {diff}"):
        return done(False)
    return done(True)


def _macro_steps(rules, ls, seed: int, cand: Candidate) -> dict:
    """勝った局の手順（自分の決定の (種類, 選んだ意味キー)）。最初のマナチャージは除き、その後の決定から勝つまで。入口のターン（自分の1ターン目）に勝った局だけ。
    探索がこの手順を1手として使う（search.macro）。ruler_control.run_one と同じ局面・同じ設定で回し直して取る。"""
    from ..engine import scenario
    from ..search.game import play_game
    from .lockcheck import lock_probe
    from .ruler_control import _deck, _entry_spec, vary
    deck = _deck(ls)
    e = scenario.build(rules, _entry_spec(vary(rules, ls, seed), deck, seed), first_player=0)
    res, eng = play_game(rules, deck, [], seed, first_player=0, max_turn=cand.max_turn, budget=le.measure_budget(ls, cand.budget),
                         start=e, lock_judge=lock_probe)
    if res.kill_turn != 1:
        return None            # 手順は入口のターンの中だけ（ターンをまたぐ手順は1手にしない）
    steps = [[x["kind"], list(x["keys"])] for x in eng.log if x["p"] == 0]
    while steps and steps[0][0] == "charge":
        steps.pop(0)
    win_ids = cand.core_ids("win")
    loop_end = next((j for j, (_, ks) in enumerate(steps) if any(w in k for k in ks for w in win_ids)), None)
    # loop_end: 勝ち手段の札に初めて触れる手の位置。そこまでがループ部分、以降が勝ちへの変換部分（§23）
    return {"seed": seed, "win_kind": res.kind, "n_steps": len(steps), "steps": steps, "loop_end": loop_end}


def _lock_spec(rules, spec: dict, seed: int, opp_level: int):
    """成立局面の spec。deck（実デッキ）があれば手札の残り・盾・山札をシードで配る（resource._deal と同じ流儀）。
    相手は search.opponent.resistance(opp_level) のデッキ。opp_mana 枚を相手のマナに置く。"""
    from ..search.opponent import resistance
    from . import resource as rs
    model, odeck = resistance(opp_level)
    if spec.get("deck"):
        import yaml
        deck = yaml.safe_load((REPO / spec["deck"]).read_text(encoding="utf-8"))["deck"]
        out = rs._deal(spec, deck, seed)
        out["p1"] = {"mana": odeck[-int(spec.get("opp_mana", 6)):]}
        out["deck_size"] = len(odeck) - int(spec.get("opp_mana", 6))
        out["filler"] = odeck[-1]
    else:
        out = {**{k: v for k, v in spec.items() if k not in ("note", "hand_fill", "opp_mana")}, "seed": seed}
    return out, model


def _lock_row(rules, spec: dict, seed: int, cand: Candidate, opp_level: int = 0) -> dict:
    from ..engine import scenario
    from .lockcheck import prefer_policy, run_lock_to_end
    from .ruler_control import start_key
    sp, model = _lock_spec(rules, spec, seed, opp_level)
    e = scenario.build(rules, sp, first_player=0)
    if model is not None:
        model.setup(e)
    run = run_lock_to_end(e, 0, my_policy=prefer_policy(*cand.policy, avoid=tuple(cand.policy_avoid)),
                          opp_policy=model.policy if model is not None else None)
    return {"seed": seed, "opp_level": opp_level, "start": start_key(e), "stage1": False, "stage2": run.won, "via": "lock" if run.won else None,
            "win_turn": run.win_turn, "error": None, "own_deck_left": run.own_deck_left, "broken": run.broken,
            "broken_turn": run.broken_turn, "opp_mana_end": len(e.zlist("mana", 1))}


def _active_lock(rules, cand: Candidate, step, measured: dict, known_min: float) -> bool:
    """能動ロック。相手の段階 cand.opp_levels のそれぞれで、勝てた割合が known_min 以上なら通す（全段階で）。"""
    import json
    if not cand.setup or not cand.policy:
        return step("entry", False, "能動ロックには setup（成立局面）と policy（与える方針）が要る")
    try:
        spec = json.loads((REPO / cand.setup).read_text(encoding="utf-8"))
    except Exception as ex:   # noqa: BLE001
        return step("entry", False, f"成立局面を読めない: {ex}")
    step("entry", True, f"{cand.setup}、与えた方針 {cand.policy}（除く {cand.policy_avoid}）")
    measured.update({"seeds": cand.seeds, "lock_mode": "active", "policy": cand.policy, "policy_avoid": cand.policy_avoid,
                     "stage1": "対象外（ロックは段2の経路）", "threshold": known_min, "by_opp_level": {}})
    ok_all, rows_all = True, []
    for lvl in cand.opp_levels:
        rows = [_lock_row(rules, spec, s, cand, lvl) for s in cand.seeds]
        rows_all += rows
        n, won = len(rows), sum(r["stage2"] for r in rows)
        why: dict[str, int] = {}
        for r in rows:
            if r["broken"]:
                k = r["broken"].split("（")[0].split(":")[0]
                why[k] = why.get(k, 0) + 1
        measured["by_opp_level"][lvl] = {"stage2": f"{won}/{n}", "stage2_rate": round(won / n, 3) if n else 0.0,
                                         "distinct_starts": len({r["start"] for r in rows}), "broken": why,
                                         "own_deck_left": sorted({r["own_deck_left"] for r in rows})}
        ok_all &= n > 0 and won / n >= known_min
    measured["rows"] = rows_all
    lv = measured["by_opp_level"]
    measured["stage2"] = " / ".join(f"段階{k} {v['stage2']}" for k, v in lv.items())
    if not step("lock", ok_all, f"相手の山札切れまで勝ち {measured['stage2']}（基準 {known_min}）。破れた理由 "
                + "、".join(f"段階{k} {v['broken']}" for k, v in lv.items())):
        return False
    again = [_lock_row(rules, spec, s, cand, cand.opp_levels[0]) for s in cand.seeds[:REPLAY_SEEDS]]
    diff = [a["seed"] for a, b in zip(again, rows_all) if _key(a) != _key(b)]
    return step("replay", not diff, f"seed {cand.seeds[:REPLAY_SEEDS]} を回し直して一致" if not diff else f"回し直すと結果が変わる seed {diff}")


def _resource(rules, cand: Candidate, step, measured: dict) -> bool:
    """リソース型: 測って記録するが、合格線が未定なので通さない（resource 検証で落ちる。線は指揮役とユーザーが決める）。"""
    from . import resource as rs
    if not cand.setup:
        return step("entry", False, "リソース型には setup（入口の局面）が要る")
    spec, deck = rs.load_setup(cand.setup)
    step("entry", True, cand.setup)
    rows = [rs.measure_one(rules, spec, deck, s, budget=cand.budget or 200) for s in cand.seeds]
    measured.update({"seeds": cand.seeds, "resource": rs.summarize(rows), "rows": rows})
    sm = measured["resource"]
    return step("resource", False, f"効率 adv 中央値 {sm['adv_median']}（{sm['adv_min']}〜{sm['adv_max']}）・得た量中央値 {sm['gain_median']}。"
                                   "合格線が未定のため登録しない（docs/combo-ruler-design.md §17）")


def register(rules, cand: Candidate, *, path=registry.PATH, purpose: str = "eval") -> tuple[Evidence, dict]:
    """検証して登録簿に書く（通れば entries、落ちれば rejected）。調整用の経路は purpose="tuning"（holdout は書けない）。"""
    ev = verify(rules, cand)
    return ev, registry.record(cand, ev, path=path, purpose=purpose)
