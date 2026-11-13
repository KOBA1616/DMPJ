"""自分のターンの探索 TurnSearch（S3、P0-3 で solitaire.py から分割）。

手の候補の並べ方（candidates・貪欲方策）と相手役 charge_only_policy もここに置く。
公平探索 FairTurnSearch は dmsim.search.fair（TurnSearch を使う）。
"""
from __future__ import annotations

import itertools
import math
import os
import time
from dataclasses import dataclass, field

from ..engine import Engine
from ..engine.core import IllegalAnswer
from ..engine.loop import LoopCertificate, LoopDetector, abstract, draw_keys, fast_forward, is_burn, verify
from ..engine.play import passive_policy
from .leaf_eval import WIN, Weights, evaluate


def own_turn(eng: Engine, me: int, turn: int | None = None) -> int:
    """全体のターン番号 → 自分の何ターン目か（相手のターン中は直前の自分のターン）。"""
    t = eng.s.turn if turn is None else turn
    return (t + 1) // 2 if eng.s.first_player == me else t // 2


# ---- 相手役 -------------------------------------------------------------------------------------

def charge_only_policy(eng: Engine, d: dict) -> list[int]:
    """マナチャージだけする相手。マナが増え続けるので、ロックが本当に相手の成長を止めているかを見分けられる。"""
    if d["kind"] == "charge":
        keys = [o["key"] for o in d["options"]]
        return [next((i for i, k in enumerate(keys) if k != "pass"), keys.index("pass"))]
    return passive_policy(eng, d)


# ---- 自分の選択の並べ方（貪欲方策・探索の手順付け） --------------------------------------------



def _rank(eng: Engine, d: dict, w: Weights) -> list[int]:
    """選択肢の添字を良さそうな順に並べる（1つ選ぶ決定用）。"""
    opts = d["options"]
    kind = d["kind"]
    p = d["player"]

    def cost(o):
        return eng.cdef(o["cid"]).face(o.get("face")).cost if "cid" in o else 0

    def key(i):
        o = opts[i]
        k = o["key"]
        if kind == "charge":
            if k == "pass":
                return (0 if len(eng.zlist("mana", p)) >= w.max_mana else 2, 0)
            return (1, -cost(o))
        if kind == "main":
            return (1, 0) if k == "pass" else (0, -cost(o))
        if kind == "attack":
            if k == "pass":
                return (2, 0)
            return (0 if o.get("target") == "player" else 1, 0)
        if kind == "yes_no":
            return (0 if k == "yes" else 1, 0)
        if k in ("pass", "decline", "no", "no_block"):
            return (1, 0)
        return (0, 0)
    return sorted(range(len(opts)), key=key)


def candidates(eng: Engine, d: dict, w: Weights, cap: int = 6) -> list[list[int]]:
    """探索で試す答えの候補（良さそうな順）。複数選ぶ決定は組み合わせを cap 個まで。同じ意味キーの組は1つにまとめる。"""
    order = _rank(eng, d, w)
    if d["max"] == 1 and d["min"] == 1:
        # 区別できない選択肢（同じ種類のカード、同じ下のカードを持つシールドなど）は1つにまとめる。
        # マナの払い方は文明の組が同じなら同じとみなして、上位2通りまでにする
        out, seen = [], set()
        for i in order:
            o = d["options"][i]
            sig = (o["key"],) + ((eng.s.cards[o["cid"]].defn, tuple(sorted(eng.s.cards[u].defn for u in eng.s.cards[o["cid"]].under)))
                                 if "cid" in o and o.get("name") == "?" else ())
            if sig in seen:
                continue
            seen.add(sig)
            out.append([i])
        return out[:2] if d["kind"] == "pay_mana" else out
    keys = [o["key"] for o in d["options"]]
    out, seen = [], set()
    if d["kind"] == "order_cards":          # 並べ替え: 元の順と次の順の2つまで（同じ意味キーの並びは1つ）
        for perm in itertools.permutations(order):
            sig = tuple(keys[i] for i in perm)
            if sig not in seen:
                seen.add(sig)
                out.append(list(perm))
                if len(out) >= min(cap, 2):      # 並びの違いで探索が膨らまないよう、元の順と次の順だけ試す
                    break
        return out
    for n in range(d["max"], d["min"] - 1, -1):
        for combo in itertools.combinations(order, n):
            sig = tuple(sorted(keys[i] for i in combo))
            if sig in seen:
                continue
            seen.add(sig)
            out.append(list(combo))
            if len(out) >= cap:
                return out
    return out


def greedy_policy(w: Weights | None = None):
    w = w or Weights()

    def pol(eng: Engine, d: dict) -> list[int]:
        return candidates(eng, d, w, cap=1)[0]
    return pol


# ---- 自分のターンの探索 -------------------------------------------------------------------------

def is_burn_loop(cert: LoopCertificate, me: int) -> bool:
    """相手の山札を削るだけで勝ちに直結しないループ。"""
    return not cert.win_by and is_burn(cert.delta, me)


def is_engine_loop(cert: LoopCertificate, me: int) -> bool:
    """相手の資源を減らさず勝ちにも直結しない（自分の資源を増やすだけの）ループ。"""
    return not cert.win_by and not any(v < 0 for k, v in cert.delta.items() if k.endswith(f":{1 - me}"))


_is_burn = is_burn_loop        # 旧名（互換）
_is_engine = is_engine_loop    # 旧名（互換）


# 「引いて捨てる」型のループ検出の既定（TurnSearch.draw_discard で局ごとに切り替え可）。環境変数 DMSIM_DRAW_DISCARD=0 で切る
DRAW_DISCARD = os.environ.get("DMSIM_DRAW_DISCARD", "1") != "0"
REPEAT_FIRST = os.environ.get("DMSIM_REPEAT_FIRST", "1") != "0"   # 案 E の既定。DMSIM_REPEAT_FIRST=0 で切る


class Detectors:
    """ターン内ループの検出器の組。手札の中身まで見る厳密なものと、ドローを含むループ用に
    手札の中身をぼかす（draw_keys 以外は枚数だけ数える）ものを並べて走らせる。"""

    def __init__(self, dets: list[LoopDetector]):
        self.dets = dets

    @classmethod
    def new(cls, eng: Engine, me: int, draw_discard: bool | None = None) -> "Detectors":
        """draw_discard: 手札をぼかす検出器で山札削り（is_burn）のループも受け付け、手札の選択を抽象キーで記録する
        （「引いて捨てる」型、docs/saga-loop-miss-20261113.md 案 A）。None は DRAW_DISCARD に従う。"""
        dd = DRAW_DISCARD if draw_discard is None else draw_discard
        return cls([LoopDetector(me=me, period="in_turn"),
                    LoopDetector(me=me, period="in_turn", hand_keys=draw_keys(eng, me), engine_loops=True,
                                 burn_loops=dd, wild=dd),
                    LoopDetector(me=me, period="in_turn", burn_loops=True)])

    def fork(self) -> "Detectors":
        return Detectors([d.fork() for d in self.dets])

    def observe(self, eng: Engine) -> LoopCertificate | None:
        found = [c for c in (d.observe(eng) for d in self.dets) if c is not None]
        return found[0] if found else None


@dataclass
class TurnStats:
    nodes: int = 0
    loops: list[dict] = field(default_factory=list)      # 試したループの候補すべて（選ばなかった線を含む）
    chosen: list[dict] = field(default_factory=list)     # 採った手順で使ったループだけ


class TurnSearch:
    """自分のターンの中の選択を深さ優先で探索する。budget を使い切ったら残りは貪欲方策で打ち切る。

    - 同じ骨格＋同じカウンタの局面は1度だけ展開する（マナの払い方の違いなど）。
    - 同じ骨格に戻り、相手側のカウンタが減っていればループ（LoopCertificate）。verify で確かめてから
      fast_forward で必要な周回だけ進め、その局面を子として探索を続ける。"""

    def __init__(self, me: int, budget: int = 200, weights: Weights | None = None, opp_policy=charge_only_policy,
                 combo_cap: int = 6, value_fn=None, time_limit: float | None = None):
        self.time_limit = time_limit          # 1手の探索の実時間の上限（秒）。超えたら budget 切れと同じく貪欲に打ち切る。None は無制限（再現性のため既定）
        self.value_fn = value_fn              # 葉の評価を差し替える関数 f(eng, me)（None なら evaluate）。勝敗を使わない局面評価の測定用
        self.me = me
        self.budget = budget
        self.w = weights or Weights()
        self.opp_policy = opp_policy
        self.combo_cap = combo_cap
        self.stock_offsets: tuple[int, ...] = (0, 1)   # ストックする周回数: 上限から何周手前までを試すか（山札の残りを1枚・2枚にする等）
        self.burn_stock = True                # 山札を削るだけのループを自動で残り1枚までストックする（2段探索の2段目では切る）
        self.draw_discard: bool | None = None
        # 案 E: 同じターンの手順で前に採った手（同じ種類・同じ意味キーの決定）を候補の先頭に回す。ループの2周目で
        # 1周目と同じ手を先に試す一般則（カード名は見ない）。None は REPEAT_FIRST
        self.repeat_first: bool | None = None   # 引いて捨てる型のループ検出（None は DRAW_DISCARD）
        self.collect: list | None = None      # ループ発見モード: 見つけたループ（局面の複製, 証明書）をここへ集めて、ストックはしない

    def _eval(self, eng: Engine) -> float:
        return self.value_fn(eng, self.me) if self.value_fn else evaluate(eng, self.me, self.w)

    def _settle(self, eng: Engine) -> dict | None:
        """相手の決定を相手役に答えさせながら、自分の決定かターン終了まで進める。"""
        while True:
            d = eng.advance()
            if d is None or eng.s.active != self.me:
                return None
            if d["player"] == self.me:
                return d
            eng.answer(self.opp_policy(eng, d))

    rollout_cap = 2000     # 貪欲な先読みの最大の決定数。通常は数手で終わる（実測 5 手以下）。超えたら終わらない繰り返しとみなす

    def _rollout(self, eng: Engine) -> Engine:
        n = 0
        while (d := self._settle(eng)) is not None:
            n += 1
            if n > self.rollout_cap:
                # 貪欲な手が同じ状況を繰り返して終わらない。エンジンの step_limit（約2万ステップ）まで回しても同じ結果
                # （勝者なし・-WIN/2 の評価）になるので、数秒かかる空回しを打ち切る
                eng.s.result = {"winner": None, "reason": "step_limit", "turn": eng.s.turn}
                break
            eng.answer(candidates(eng, d, self.w, cap=1)[0])
        return eng

    def run(self, eng: Engine) -> tuple[Engine, TurnStats]:
        """eng（自分の決定待ち）から探索し、一番評価の高いターン終了局面の Engine を返す。eng は変更しない。"""
        self.left = self.budget
        self._root_log = len(eng.log)
        self._rf = REPEAT_FIRST if self.repeat_first is None else self.repeat_first
        self._deadline = None if self.time_limit is None else time.monotonic() + self.time_limit
        self.seen: set = set()
        self.stats = TurnStats()
        det = Detectors.new(eng, self.me, self.draw_discard)
        best = self._search(eng.clone(), det)
        self.stats.chosen = [dict(lp) for lp in best[2]]
        return best[1], self.stats

    def _search(self, eng: Engine, det: Detectors) -> tuple[float, Engine, tuple]:
        """(評価, 葉の局面, その葉に至る手順で使ったループの記録) を返す。ループの記録は採った線のものだけが親へ伝わる。"""
        d = self._settle(eng)
        if d is None:
            return self._eval(eng), eng, ()
        if self._deadline is not None and self.left > 0 and time.monotonic() > self._deadline:
            self.left = 0                     # 時間切れ: 以降は予算切れと同じ扱い
        if self.left <= 0:
            leaf = self._rollout(eng)
            return self._eval(leaf), leaf, ()
        h, ctr = abstract(eng, "in_turn")
        # マナは枚数だけでなく何が残っているか（文明）も区別する。払い方の違いで闇マナが残るか否かが変わる
        mana_left = tuple(sorted((c.defn, c.tapped) for c in (eng.s.cards[x] for p in (0, 1) for x in eng.s.zones["mana"][p])))
        sizes = tuple(len(eng.s.zones[z][p]) for p in (0, 1) for z in ("hand", "shield", "graveyard", "bz"))   # 骨格が同じでも枚数が違う局面は別（手札を引いて捨てた後など）
        tkey = (h, tuple(sorted(ctr.items())), mana_left, sizes)
        cert = det.observe(eng)
        if cert is not None and self.collect is not None:
            if all(c.start_skeleton != cert.start_skeleton for _, c in self.collect):
                self.collect.append((eng.clone(), cert))
            return -WIN, eng, ()          # ループの先は辿らない（ループの発見だけを行う）
        if cert is not None and _is_burn(cert, self.me) and not self.burn_stock:
            cert = None                       # 周回数は呼び出し側が決める
        elif cert is not None and verify(eng, cert, times=1).verified < 1:
            cert = None                       # 骨格が戻っただけで、実際には繰り返せない（手札のカードを使い切る連鎖など）。ループ扱いせず探索を続ける
        elif cert is not None:
            # 周回数（ストック量）を選ぶ: 上限まで回す線のほか、あと数周手前で止める線（stock_offsets）も試す。
            # 山札を削るループは勝ちにつながるか分からないので上限（残り1枚）の線を試す。ループに入った直後に抜ける線は
            # 親の局面で試されるので、ここでループの続きは辿らない
            best: tuple | None = None
            for ff, lp in self._stocks(eng, cert):
                r = self._search(ff, Detectors.new(ff, self.me, self.draw_discard))
                r = (r[0], r[1], (lp,) + r[2])
                if best is None or r[0] > best[0]:
                    best = r
                if best[0] >= WIN - 1000:
                    break
            if best is not None:
                return best
            if _is_engine(cert, self.me) and not _is_burn(cert, self.me):
                return -WIN, eng, ()  # 資源ループはストックし切った。同じ周回を1つずつ辿り直さない（山札を減らすだけ）
            cert = None
        if tkey in self.seen:
            return -WIN, eng, ()      # 既に展開した局面（ループの途中で戻ってきた場合もここ）
        self.seen.add(tkey)
        best: tuple | None = None
        cands = candidates(eng, d, self.w, self.combo_cap)
        if self.w.lookahead and len(cands) > 1:
            cands = self._lookahead_order(eng, cands)
        if self._rf and len(cands) > 1:
            cands = self._repeat_order(eng, d, cands)
        for choice in cands:
            if self.left <= 0 and best is not None:
                break
            self.left -= 1
            self.stats.nodes += 1
            child = eng.clone()
            child.answer(choice)
            r = self._search(child, det.fork())
            if best is None or r[0] > best[0]:
                best = r
            if best[0] >= WIN - 1000:
                break                 # このターンで勝てる線が見つかった
        return best

    def _repeat_order(self, eng: Engine, d: dict, cands: list[list[int]]) -> list[list[int]]:
        """このターンの手順で、同じ種類の決定に前回答えた意味キーと同じ候補を先頭へ（安定な並べ替え）。"""
        keys = [o["key"] for o in d["options"]]
        ks = set(keys)
        for a in reversed(eng.log[self._root_log:]):
            # 同じ種類で、前に選んだ意味キーが今の選択肢にもある決定（同じ効果の2周目とみなす）
            if a["kind"] == d["kind"] and a["p"] == d["player"] and a["keys"] and set(a["keys"]) <= ks:
                prev = sorted(a["keys"])
                return sorted(cands, key=lambda ch: sorted(keys[i] for i in ch) != prev)
        return cands

    def _lookahead_order(self, eng: Engine, cands: list[list[int]]) -> list[list[int]]:
        """各候補を貪欲に先まで進めた局面の評価で並べ替える（同点は元の順）。ノード数には数えない軽い見積もり。"""
        scored = []
        for i, ch in enumerate(cands):
            c = eng.clone()
            c.answer(ch)
            leaf = c
            for _ in range(self.w.lookahead):
                d2 = self._settle(leaf)
                if d2 is None:
                    break
                leaf.answer(candidates(leaf, d2, self.w, cap=1)[0])
            scored.append((-self._eval(leaf), i, ch))
        return [ch for _, _, ch in sorted(scored)]

    def _stocks(self, eng: Engine, cert: LoopCertificate) -> list[tuple[Engine, dict]]:
        """ループを確かめてストックした局面（周回数の違うもの）と、その記録の組を返す。勝ちにつながらない・確かめられないなら空。
        周回数は上限 n から stock_offsets だけ手前までを試す（山札を残り1枚／2枚にする、など）。"""
        engine = _is_engine(cert, self.me)
        burn = _is_burn(cert, self.me)
        if burn:
            n = int(cert.limit) if math.isfinite(cert.limit) else 0
        elif cert.win_by:
            n = cert.needed
        else:
            n = int(min(cert.limit, self.w.stock_cap)) if engine else (int(cert.limit) if math.isfinite(cert.limit) else 0)
        d_deck = cert.delta.get(f"deck:{self.me}", 0)
        if engine and not burn and d_deck < 0:      # 自分の山札切れ対策: 山札を deck_keep 枚より減らさない
            n = min(n, (len(eng.zlist("deck", self.me)) - self.w.deck_keep) // -d_deck)
        if n <= 0 or verify(eng, cert, times=1).verified < 1:
            return []
        offsets = self.stock_offsets if (burn or (engine and not cert.win_by)) else (0,)
        out = []
        for k in offsets:
            m = n - k
            if m <= 0:
                continue
            ff = eng.clone()
            try:
                fast_forward(ff, cert, m)
            except IllegalAnswer:
                continue
            lp = {"win_by": cert.win_by, "needed": cert.needed, "limit": cert.limit,
                  "delta": cert.delta, "length": len(cert.actions), "stocked": m,
                  "kind": "burn" if burn else "engine" if engine else "kill",
                  "source": "certificate", "verified": True, "wild": cert.wild}
            self.stats.loops.append(lp)       # 候補（選ばなかった線を含む）
            out.append((ff, lp))
        return out

