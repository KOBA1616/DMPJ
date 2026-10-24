"""対戦記録（シード＋選択ログ）を1手ずつ再生して見るための読み取り専用の解析。

  - frames: 1手ごとの手番・ステップ・選んだ選択肢・動いたカード・各ゾーンの枚数
  - loops : ログの中の繰り返し（ループの骨格・1周の選択・周回数・ストック量 Δ×周回）
            検出は solitaire と同じ Detectors を読むだけで使い、探索ロジックには手を入れない
  - route : 勝ち筋。ターンごとに、ループの周回を1行にまとめた主要な手の並び
  - lock  : 終局時点でロック（相手の山札切れまで何もできない周期）が成立していれば、その証明書

  python -m dmsim.playback g.json            # 記録（solitaire --record の出力など）の要約を表示
"""
from __future__ import annotations

import json
import math

from .devserver import Session, _diff, _label, _snapshot
from .engine import Engine
from .loop import LoopCertificate, fast_forward
from .play import replay
from .solitaire import Detectors, lock_probe

ZONES = ("hand", "bz", "mana", "shield", "deck", "graveyard")


def _counts(eng: Engine) -> list[dict[str, int]]:
    out = []
    for p in (0, 1):
        c = {z: len(eng.bz_tops(p)) if z == "bz" else len(eng.zlist(z, p)) for z in ZONES}
        c["mana_untapped"] = sum(1 for x in eng.zlist("mana", p) if not eng.s.cards[x].tapped)
        out.append(c)
    return out


def _skeleton(eng: Engine) -> dict:
    s = eng.s
    return {"bz": [[s.cards[c].controller, eng.cdef(c).name, s.cards[c].tapped] for c in eng.bz_tops()],
            "hand": [eng.cdef(c).name for c in eng.zlist("hand", s.active)]}


def _num(x):
    return None if isinstance(x, float) and math.isinf(x) else x


def cert_to_dict(cert: LoopCertificate) -> dict:
    return {"start_skeleton": cert.start_skeleton, "actions": cert.actions, "deciders": cert.deciders,
            "delta": cert.delta, "limit": _num(cert.limit), "period": cert.period, "win_by": cert.win_by,
            "needed": cert.needed, "verified": cert.verified, "notes": cert.notes,
            "hand_keys": sorted(cert.hand_keys) if cert.hand_keys is not None else None}


def cert_from_dict(d: dict) -> LoopCertificate:
    return LoopCertificate(d["start_skeleton"], d["actions"], d["deciders"], d["delta"],
                           float("inf") if d.get("limit") is None else d["limit"], d["period"], d.get("win_by"),
                           d.get("needed"), d.get("verified", 0), list(d.get("notes", [])),
                           set(d["hand_keys"]) if d.get("hand_keys") is not None else None)


def record_with_cert(rules, rec: dict, at: int, cert: LoopCertificate, laps: int) -> dict:
    """記録の at 手目までのあとに、証明書の1周を laps 回つなげた記録を作る（証明書だけを渡された時の再生用）。"""
    eng = replay(rules, rec["decks"], rec["seed"], rec["log"][:at], rec.get("first_player", 0), rec.get("scenario"))
    fast_forward(eng, cert, laps)
    return {**rec, "log": list(eng.log), "result": eng.s.result, "digest": eng.s.digest(), "cards_digest": None}


def _find_loops(eng: Engine, log: list[dict], i: int, det: Detectors, me: int = 0):
    """i 手目（これから答える決定の直前）で検出器を回す。見つかれば (開始位置, 1周の長さ, 周回数, 証明書)。"""
    cert = det.observe(eng)
    if cert is None:
        return None
    n = len(cert.actions)
    at = i - n
    first = [e["keys"] for e in log[at:i]]
    laps = 1
    while at + (laps + 1) * n <= len(log) and [e["keys"] for e in log[at + laps * n:at + (laps + 1) * n]] == first:
        laps += 1
    return at, n, laps, cert


def analyze_record(rules, rec: dict, me: int = 0) -> dict:
    log = rec["log"]
    eng = replay(rules, rec["decks"], rec["seed"], [], rec.get("first_player", 0), rec.get("scenario"))
    frames, loops = [], []
    det, det_turn, skip_until = None, None, -1
    for i, e in enumerate(log):
        d = eng.advance()
        if d is None:
            break
        if eng.s.active == me and d["player"] == me and i > skip_until:
            if det is None or det_turn != eng.s.turn:
                det, det_turn = Detectors.new(eng, me), eng.s.turn
            hit = _find_loops(eng, log, i, det, me)
            if hit is not None:
                at, n, laps, cert = hit
                loops.append({"id": len(loops), "start": at, "length": n, "laps": laps, "end": at + n * laps,
                              "turn": eng.s.turn, "actions": cert.actions, "deciders": cert.deciders,
                              "delta": cert.delta, "stock": {k: v * laps for k, v in cert.delta.items()},
                              "limit": _num(cert.limit), "win_by": cert.win_by, "needed": cert.needed,
                              "skeleton": _skeleton(eng), "skeleton_hash": cert.start_skeleton,
                              "period": cert.period, "kind": _kind(cert, me),
                              "before": frames[at - 1]["counts"] if at > 0 else None})
                skip_until = at + n * laps - 1
                det = None
        turn, active = eng.s.turn, eng.s.active
        before = _snapshot(eng)
        chosen = [_label(eng, d["options"][k]) for k in e["choice"]]
        eng.answer(e["choice"])
        eng.advance()
        frames.append({"i": i, "turn": turn, "active": active, "p": e["p"], "kind": e["kind"],
                       "choice": e["choice"], "chosen": chosen, "keys": e["keys"],
                       "moved": [c for c, a in before.items() if a != _snapshot_one(eng, c)],
                       "changes": _diff(eng, before, _snapshot(eng)), "counts": _counts(eng)})
    for lp in loops:
        lp["end_counts"] = frames[lp["end"] - 1]["counts"]
        for k in range(lp["start"], lp["end"]):
            frames[k]["loop"] = lp["id"]
            frames[k]["lap"] = (k - lp["start"]) // lp["length"] + 1
    eng.advance()
    result = eng.s.result
    lock = None
    if result is None:
        try:
            c = lock_probe(eng, me, 2)
            lock = cert_to_dict(c) if c is not None else None
        except Exception as ex:      # 読み取りだけの試し回し。失敗しても再生は続ける
            lock = {"error": f"{type(ex).__name__}: {ex}"}
    note = {}
    try:
        note = json.loads(rec.get("note") or "{}", parse_constant=lambda c: None)
    except ValueError:
        pass
    return {"n": len(log), "frames": frames, "loops": loops, "result": result, "lock": lock, "note": note,
            "route": _route(frames, loops), "seed": rec["seed"], "first_player": rec.get("first_player", 0)}


def _snapshot_one(eng: Engine, cid: int):
    c = eng.s.cards[cid]
    return (c.zone, c.controller, c.tapped, c.gen)


def _kind(cert: LoopCertificate, me: int) -> str:
    from .solitaire import _is_burn, _is_engine
    return "burn" if _is_burn(cert, me) else "engine" if _is_engine(cert, me) else "kill" if cert.win_by else "loop"


def _short(f: dict) -> str:
    return f"P{f['p']} {f['kind']}: " + (", ".join(f["chosen"]) or "-")


def _route(frames: list[dict], loops: list[dict]) -> list[dict]:
    """ターンごとの主要な手。charge / pass など流れを動かさない手は省き、ループの周回は1項目にまとめる。"""
    out: list[dict] = []
    skip = {"charge", "pay_mana", "block"}
    done = set()
    for f in frames:
        if "loop" in f:
            if f["loop"] in done:
                continue
            done.add(f["loop"])
            lp = loops[f["loop"]]
            out.append({"turn": f["turn"], "type": "loop", "i": lp["start"], "loop": lp["id"],
                        "text": f"ループ {lp['length']}手 × {lp['laps']}周（{lp['kind']}）"})
        elif f["kind"] not in skip and not (len(f["chosen"]) == 1 and f["keys"] == ["pass"]) \
                and f["keys"] not in (["no_block"], ["no"]):
            out.append({"turn": f["turn"], "type": "step", "i": f["i"], "text": _short(f)})
    return out


class Playback:
    """解析結果と、任意の手数目の盤面（開発者モードの view と同じ形）を返す。"""

    def __init__(self, rules, rec: dict):
        self.rules, self.rec = rules, rec
        self.info = analyze_record(rules, rec)
        self.cur: tuple[int, Engine] | None = None

    def view_at(self, i: int) -> dict:
        """i 手目の決定の直前（i = 手数なら終局後）の盤面。"""
        i = max(0, min(i, self.info["n"]))
        if self.cur is None or self.cur[0] > i:
            eng = replay(self.rules, self.rec["decks"], self.rec["seed"], [], self.rec.get("first_player", 0),
                         self.rec.get("scenario"))
            eng.advance()
            self.cur = (0, eng)
        k, eng = self.cur
        while k < i:
            eng.answer(self.rec["log"][k]["choice"])
            eng.advance()
            k += 1
        self.cur = (k, eng)
        s = Session.__new__(Session)
        s.rules, s.start, s.auto, s.history, s.eng = self.rules, {}, [False, False], [], eng.clone()
        v = s.view()
        v["frame"] = i
        v["chosen"] = self.info["frames"][i]["choice"] if i < self.info["n"] else []
        return v


def main(argv=None):
    import argparse
    from pathlib import Path

    from .defs import load_rules
    ap = argparse.ArgumentParser(description="対戦記録の手順・ループ・勝ち筋を要約する（画面は dmsim.devserver の「再生」タブ）")
    ap.add_argument("record")
    a = ap.parse_args(argv)
    pb = analyze_record(load_rules(), json.loads(Path(a.record).read_text(encoding="utf-8")))
    print(f"手数={pb['n']} 結果={pb['result']} ループ={len(pb['loops'])} ロック={'あり' if pb['lock'] else 'なし'}")
    for r in pb["route"]:
        print(f"  T{r['turn']} #{r['i']} {r['text']}")


if __name__ == "__main__":
    main()
