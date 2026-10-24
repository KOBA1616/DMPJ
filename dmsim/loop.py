"""ループ／ロックの検出とストック（設計判断⑦）。

状態を「骨格」と「カウンタ」に分ける。
- 骨格: バトルゾーン（カード名・タップ・召喚酔い・重なり）、手札の中身、待機中の効果、継続的効果、
        ステップ、決定待ちの種類と選択肢。ここが同じなら「同じ局面に戻った」とみなす。
- カウンタ: zones.yaml で counter: true のゾーンの枚数（山札・墓地・マナ・シールドなど）と、未タップのマナ数。
同じ骨格に戻る行動列が見つかったら、カウンタの差分 Δ を取り、Δ×N 回で勝てるかを判定する（LoopCertificate）。
period="in_turn" は1ターン内のループ、"round" は自分＋相手のターンを1周とするロック。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .engine import Engine


def abstract(eng: Engine, period: str = "in_turn", hand_keys: set[str] | None = None) -> tuple[str, dict[str, int]]:
    """hand_keys を渡すと、手札はその名前のカードだけを骨格に入れ、残りは枚数（hand:p）だけのカウンタにする。
    ドローを含むループ・ロックでは、引いたカードで骨格が変わらないようにこれを使う。"""
    s = eng.s
    zones = eng.rules.zones

    def name(c):
        return s.cards[c].defn

    skel = {
        "active": s.active, "step": s.step,
        "turn": s.turn if period == "in_turn" else None,
        "bz": sorted([s.cards[c].controller, name(c), s.cards[c].tapped, s.cards[c].entered_turn == s.turn,
                      sorted(name(u) for u in s.cards[c].under)] for c in eng.bz_tops()),
        "pending": sorted([p["kind"], p["defn"], p["ab"], p["controller"], p["win"]] for p in s.pending),
        "cont": sorted([json.dumps(ce["mod"], sort_keys=True), ce["duration"],
                        sorted(name(r[0]) for r in ce["affected"] if s.alive(r))] for ce in s.continuous),
        "hold": sorted(name(c) for c in s.hold),
        "tasks": [[t["t"], t.get("phase"), t.get("pc"), t.get("i"), t.get("sub")] for t in s.tasks],
        "waiting": None if s.waiting is None else [s.waiting["kind"], s.waiting["player"]] + (
            [] if hand_keys is not None else [sorted(o["key"] for o in s.waiting["options"])]),
        "delayed": sorted(json.dumps([d["when"], d["effect"], d["duration"]], sort_keys=True) for d in s.delayed),
        "step_mods": sorted(json.dumps(m, sort_keys=True) for m in s.step_mods),
    }
    counters: dict[str, int] = {}
    for z, zd in zones.items():
        if zd["shared"]:
            continue
        for p in (0, 1):
            if zd["counter"]:
                counters[f"{z}:{p}"] = len(s.zones[z][p])
            elif z == "hand" and hand_keys is not None:
                names = [name(c) for c in s.zones[z][p]]
                skel[f"{z}:{p}"] = sorted(n for n in names if n in hand_keys)
                counters[f"{z}:{p}"] = sum(1 for n in names if n not in hand_keys)
            else:
                skel[f"{z}:{p}"] = sorted(name(c) for c in s.zones[z][p])
    for p in (0, 1):
        counters[f"mana_untapped:{p}"] = sum(1 for c in s.zones["mana"][p] if not s.cards[c].tapped)
    h = hashlib.blake2b(json.dumps(skel, sort_keys=True, ensure_ascii=False).encode(), digest_size=16).hexdigest()
    return h, counters


@dataclass
class LoopCertificate:
    start_skeleton: str
    actions: list[list[str]]          # 1周分の選択（意味キー）。answer_by_keys で再生できる
    deciders: list[int]
    delta: dict[str, int]
    limit: float                      # 繰り返せる回数の上限（inf もありうる）
    period: str
    win_by: str | None = None
    needed: int | None = None         # 勝利に必要な周回数
    verified: int = 0                 # 実際に再生して確認できた周回数
    notes: list[str] = field(default_factory=list)
    hand_keys: set[str] | None = None


def analyze(delta: dict[str, int], counters: dict[str, int], me: int) -> tuple[float, str | None, int | None]:
    opp = 1 - me
    limit = float("inf")
    for k, d in delta.items():
        if d < 0 and (k.endswith(f":{me}")):
            # 自分の資源を消費する成分。山札は 0 枚で敗北なので残り1枚までしか使えない
            reserve = 1 if k.startswith("deck:") else 0
            limit = min(limit, (counters[k] - reserve) // -d)
    win_by, needed = None, None
    d_deck = delta.get(f"deck:{opp}", 0)
    if d_deck < 0:
        needed = -(-counters[f"deck:{opp}"] // -d_deck)   # 相手の山札が 0 枚になった瞬間に勝ち（104.2b）
        if needed <= limit:
            win_by = "opp_deck_out"
    d_sh = delta.get(f"shield:{opp}", 0)
    if win_by is None and d_sh < 0:
        n = -(-counters[f"shield:{opp}"] // -d_sh)
        if n <= limit:
            win_by, needed = "shield_zero", n   # この後ダイレクトアタックが通れば勝ち
    return limit, win_by, needed


class LoopDetector:
    """1人回し中に呼び出し、同じ骨格への回帰を見つける。"""

    def __init__(self, me: int = 0, period: str = "in_turn", hand_keys: set[str] | None = None):
        self.me = me
        self.period = period
        self.hand_keys = hand_keys
        self.seen: dict[str, tuple[dict[str, int], int]] = {}

    def observe(self, eng: Engine) -> LoopCertificate | None:
        h, ctr = abstract(eng, self.period, self.hand_keys)
        now = len(eng.log)
        if h in self.seen:
            old, at = self.seen[h]
            delta = {k: ctr[k] - old[k] for k in ctr if ctr[k] != old[k]}
            if delta and now > at:
                limit, win_by, needed = analyze(delta, ctr, self.me)
                if any(v < 0 for k, v in delta.items() if k.endswith(f":{1 - self.me}")) or win_by:
                    acts = eng.log[at:now]
                    return LoopCertificate(h, [a["keys"] for a in acts], [a["p"] for a in acts], delta,
                                           limit, self.period, win_by, needed, hand_keys=self.hand_keys)
        self.seen[h] = (ctr, now)
        return None


def verify(eng: Engine, cert: LoopCertificate, times: int = 2) -> LoopCertificate:
    """証明書の行動列を実際に再生し、同じ骨格に戻って同じ差分が出ることを確かめる。"""
    e = eng.clone()
    for _ in range(times):
        h0, c0 = abstract(e, cert.period, cert.hand_keys)
        for keys in cert.actions:
            d = e.advance()
            if d is None:
                cert.notes.append("game ended during replay")
                return cert
            e.answer_by_keys(keys)
        e.advance()
        h1, c1 = abstract(e, cert.period, cert.hand_keys)
        delta = {k: c1[k] - c0[k] for k in c1 if c1[k] != c0[k]}
        if h1 != cert.start_skeleton or delta != cert.delta:
            cert.notes.append(f"diverged: delta={delta}")
            return cert
        cert.verified += 1
    return cert


def fast_forward(eng: Engine, cert: LoopCertificate, n: int):
    """競技ルール4.3 の「回数を宣言して省略」に相当。ここでは決定的に n 周を実際に再生する。"""
    for _ in range(n):
        for keys in cert.actions:
            if eng.advance() is None:
                return
            eng.answer_by_keys(keys)
    eng.advance()
