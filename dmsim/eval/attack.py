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

    snaps = {}

    def tr(e, t):
        hold["e"] = e
        z = e.s.zones
        snaps[t] = {"opp_shield": len(z["shield"][1]), "my_bz": len(z["bz"][0]), "opp_bz": len(z["bz"][1]),
                    "my_shield": len(z["shield"][0])}
    r = assemble.run_one(rules, ls, seed, deck=list(deck), max_turn=max_turn, budget=budget, n_det=n_det, opp_level=opp_level, trace=tr)
    res, v = r["res"], r["verdict"]
    m = marks(hold["e"].log) if "e" in hold and res.kill_turn else {}
    return {"seed": seed, "first": r["first"], "opp": r["opp"], "kill_turn": res.kill_turn if v.stage2.kill else None,
            "kind": res.kind, "via": v.stage2.via, "lost": res.lost, "lost_turn": _lost_turn(hold.get("e")) if res.lost else None,
            "error": res.error, "marks": m, "snaps": snaps}


def measure(rules, deck, seeds, workers: int | None = None, **kw) -> list[dict]:
    from ..base.parallel import map_ordered
    return map_ordered(lambda s: run_one(rules, deck, s, **kw), seeds, workers)


def accumulated(m: dict) -> bool:
    """殴り勝ちが蓄積（出してすぐの攻撃・同じ体の再攻撃・踏み倒し）に由来する印があるか。"""
    return bool(m) and (m.get("haste", 0) > 0 or m.get("repeat", 0) > 0 or m.get("free", 0) > 0)


def kill_by(t: int):
    """組の寄与（eval.contrib.paired）に渡す1局の値: t ターン以内に勝ったら 1。"""
    return lambda r: 1 if r["kill_turn"] is not None and r["kill_turn"] <= t else 0


def _snap(r, t):
    ss = {int(k): v for k, v in (r.get("snaps") or {}).items()}
    ks = [k for k in ss if k <= t]
    return ss[max(ks)] if ks else None


def left_by(t: int):
    """t ターン目の終わりに、キルまでに残る打点（相手の盾 + とどめの1）。勝っていれば 0。値が小さいほど良いので符号を反転して返す。"""
    def f(r):
        if r["kill_turn"] is not None and r["kill_turn"] <= t:
            return 0
        s = _snap(r, t)
        return -((s["opp_shield"] + 1) if s else 6)
    return f


def broken_by(t: int):
    """t ターン目の終わりまでに割った相手の盾の枚数（勝っていれば開始時の枚数）。"""
    def f(r):
        s0 = _snap(r, 0)
        start = s0["opp_shield"] if s0 else 5
        if r["kill_turn"] is not None and r["kill_turn"] <= t:
            return start
        s = _snap(r, t)
        return start - s["opp_shield"] if s else 0
    return f


def board_by(t: int):
    """t ターン目の終わりの盤面の差（自分のバトルゾーンの体数 − 相手の体数）。"""
    def f(r):
        s = _snap(r, t)
        return (s["my_bz"] - s["opp_bz"]) if s else 0
    return f


VALUES = {"kill": kill_by, "left": left_by, "broken": broken_by, "board": board_by}


def pair_contribution(with_rows, without_rows, t: int = 4, value: str = "kill") -> dict:
    """組の寄与。value: kill（t ターン以内の勝ち）/ left（残り打点、符号反転）/ broken（割った盾）/ board（盤面の差）。"""
    from .contrib import by_seed, paired
    f = VALUES[value](t)
    ok = lambda rows: [r for r in rows if not r.get("error")]   # noqa: E731  誤りの局は対から外す
    return paired(by_seed(ok(with_rows), f), by_seed(ok(without_rows), f))


def pair_interaction(ab, a, b, none, t: int = 4, value: str = "kill") -> dict:
    """組の相乗分（eval.contrib.interaction）。4つのデッキ（両方あり・Aだけ・Bだけ・両方なし）の同一シードの行から。"""
    from .contrib import by_seed, interaction
    f = VALUES[value](t)
    ok = lambda rows: by_seed([r for r in rows if not r.get("error")], f)   # noqa: E731
    return interaction(ok(ab), ok(a), ok(b), ok(none))


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
