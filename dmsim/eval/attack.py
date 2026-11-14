"""攻撃型の目盛り（S4、docs/combo-ruler-design.md §24、2026-11-14）。

ループ型の段1・段2とは別欄。足切りはせず、値を記録して順位づけに使う。
- 測り方: 通常開幕・山札が見えない公平探索（eval.assemble.run_one、InfoLevel.FAIR）。相手は抵抗あり（search.opponent.resistance(1)
  = S・トリガー入りの盾とブロック）が既定。先攻・後攻はシードで交互。
- 値: キルターン（自分のターンで数える）の分布、3T・4T以内のキル率（ウィルソンの95%区間つき）、勝ち方（殴り勝ち／効果／ループ）。
- 蓄積の印（殴り勝ちが何に由来するか）: 勝ったターンの攻撃回数、攻撃した体数、そのターンに出してすぐ攻撃した体数（スピードアタッカー等）、
  同じ体が2回以上攻撃した数（アンタップ・追加攻撃）、そのターンにマナを払わずに出た体数（踏み倒し）。
"""
from __future__ import annotations

from collections import Counter

from ..base.loopspec import LoopSpec
from .measure import wilson

DEFAULT_OPP = 1


def _turns(log, me: int = 0) -> list[list[dict]]:
    """対局記録を自分のターンごとに分ける（自分のチャージで区切る）。"""
    out, cur = [], None
    for x in log:
        if x.get("p") == me and x.get("kind") == "charge":
            cur = []
            out.append(cur)
        if cur is not None and x.get("p") == me:
            cur.append(x)
    return out


def marks(log, me: int = 0) -> dict:
    """勝ったターン（最後の自分のターン）の蓄積の印。"""
    ts = _turns(log, me)
    last = ts[-1] if ts else []
    played, paid, attackers = [], set(), Counter()
    pending_play = None
    for x in last:
        for k in x.get("keys", ()):
            if x.get("kind") == "main" and k.startswith("play:"):
                pending_play = k.split(":", 1)[1]
                played.append(pending_play)
            elif x.get("kind") == "pay_mana" and pending_play:
                paid.add(pending_play)
            elif x.get("kind") == "attack" and k.startswith("attack:") and not k.endswith(":none"):
                attackers[k.split(":")[1]] += 1
    haste = sum(1 for c in attackers if c in played)
    return {"attacks": sum(attackers.values()), "attackers": len(attackers), "haste": haste,
            "repeat": sum(1 for v in attackers.values() if v >= 2), "played": len(played),
            "free": sum(1 for c in played if c not in paid)}


def _lost_turn(e):
    from ..search.turn import own_turn
    r = e.s.result if e is not None else None
    return own_turn(e, 0, r["turn"]) if r and r.get("turn") is not None else None


def run_one(rules, deck, seed: int, *, opp_level: int = DEFAULT_OPP, max_turn: int = 6, budget: int = 200, n_det: int = 8) -> dict:
    from . import assemble
    ls = LoopSpec(name="attack", kind="deterministic", minimal=[])
    hold = {}

    def tr(e, t):
        hold["e"] = e
    r = assemble.run_one(rules, ls, seed, deck=list(deck), max_turn=max_turn, budget=budget, n_det=n_det, opp_level=opp_level, trace=tr)
    res, v = r["res"], r["verdict"]
    m = marks(hold["e"].log) if "e" in hold and res.kill_turn else {}
    return {"seed": seed, "first": r["first"], "opp": r["opp"], "kill_turn": res.kill_turn if v.stage2.kill else None,
            "kind": res.kind, "via": v.stage2.via, "lost": res.lost, "lost_turn": _lost_turn(hold.get("e")) if res.lost else None,
            "error": res.error, "marks": m}


def measure(rules, deck, seeds, **kw) -> list[dict]:
    return [run_one(rules, deck, s, **kw) for s in seeds]


def accumulated(m: dict) -> bool:
    """殴り勝ちが蓄積（出してすぐの攻撃・同じ体の再攻撃・踏み倒し）に由来する印があるか。"""
    return bool(m) and (m.get("haste", 0) > 0 or m.get("repeat", 0) > 0 or m.get("free", 0) > 0)


def kill_by(t: int):
    """組の寄与（eval.contrib.paired）に渡す1局の値: t ターン以内に勝ったら 1。"""
    return lambda r: 1 if r["kill_turn"] is not None and r["kill_turn"] <= t else 0


def pair_contribution(with_rows, without_rows, t: int = 4) -> dict:
    from .contrib import by_seed, paired
    return paired(by_seed(with_rows, kill_by(t)), by_seed(without_rows, kill_by(t)))


def summarize(rows, horizon: int = 6, kill_turns=(3, 4)) -> dict:
    n = len(rows)
    kt = [r["kill_turn"] for r in rows if r["kill_turn"] is not None]
    c = Counter(kt)
    out = {"games": n, "dist": {t: c.get(t, 0) for t in range(1, horizon + 1)}, "no_kill": n - len(kt),
           "errors": sum(1 for r in rows if r["error"]), "lost": sum(1 for r in rows if r.get("lost")), "opp": sorted({r["opp"] for r in rows}),
           "via": dict(Counter(r["via"] for r in rows if r["kill_turn"] is not None)), "kill": {}}
    for t in kill_turns:
        won = [r for r in rows if r["kill_turn"] is not None and r["kill_turn"] <= t]
        out["kill"][t] = {"k": len(won), "rate": len(won) / n if n else 0.0, "ci95": wilson(len(won), n) if n else (0.0, 0.0),
                          "beat": sum(1 for r in won if r["via"] == "beat"),
                          "accumulated": sum(1 for r in won if r["via"] == "beat" and accumulated(r["marks"]))}
    out["mean_kill_turn"] = round(sum(kt) / len(kt), 2) if kt else None
    return out
