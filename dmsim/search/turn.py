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

    keep = set()
    if KEEP_HAND is not None and kind in ("charge", "choose_cards"):
        # 経路に要る札を手札に残す（search.route_goal.keep_hand。並べ替えだけで候補は消さない。既定 None は従来どおり）
        try:
            if kind == "charge" or _from_hand_to_grave(eng, d):
                keep = KEEP_HAND(eng, p)
        except Exception:
            keep = set()

    def kept(o):
        return 1 if keep and "cid" in o and eng.s.cards[o["cid"]].defn in keep else 0

    free_now = set()
    if kind == "charge" and CHARGE_KEEP_FREE:
        # 今コストを払わずに出せる札（無償詠唱・G・ゼロ）はマナに置くと損をする（出せば効果が得られる）ので後回し
        try:
            free_now = {eng.s.cards[o["cid"]].defn for o in eng._play_options(p) if o.get("free")}
        except Exception:
            free_now = set()

    dw = _drawout_order(eng, d) if DRAWOUT_ORDER() else None

    def key(i):
        o = opts[i]
        k = o["key"]
        if dw is not None and "cid" in o:
            return dw(o)
        if kind == "charge":
            if k == "pass":
                return (0 if len(eng.zlist("mana", p)) >= w.max_mana else 2, 0)
            return (1, kept(o), 1 if "cid" in o and eng.s.cards[o["cid"]].defn in free_now else 0, -cost(o))
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
        return (0, kept(o))
    return sorted(range(len(opts)), key=key)


def DRAWOUT_ORDER() -> bool:
    """進化元・メテオバーンの並べ替え（§33）。段階1の40局で段2が改善しなかったので独立の切り替え DMSIM_EVO_ORDER（既定無効）。"""
    return _os.environ.get("DMSIM_EVO_ORDER", "0") == "1"


def _drawout_order(eng: Engine, d: dict):
    """ドロー置換の勝ち手段の線の並べ替え（§33、DMSIM_EVO_ORDER=1 のときだけ）。効果データの形だけを見る。
    - 進化元を選ぶ: 「墓地に置かれた時に引く」札を先に、ドロー置換の勝ち手段を後に（勝ち手段は墓地に残してメテオバーンで出す）。
    - 場の札の下から墓地へ置く札を選ぶ（メテオバーンなど）: 引く札を先に、勝ち手段を後に。
    - 墓地から場へ出す札を選ぶ: 勝ち手段を先に。
    それ以外の決定は None（従来の並び）。"""
    from .access import draw_win, grave_draws
    rules, s = eng.rules, eng.s
    opts = d["options"]
    if not opts or not all("cid" in o for o in opts):
        return None
    kind = d["kind"]
    zones = {s.cards[o["cid"]].zone for o in opts}
    t = eng.s.tasks[-1] if eng.s.tasks else {}
    op = (t.get("ops") or [None])[t.get("pc", 0)] if t.get("t") == "effect" and 0 <= t.get("pc", -1) < len(t.get("ops") or ()) else None
    to = op.get("to") if isinstance(op, dict) else None
    under_all = {u for c in s.zones["bz"][d["player"]] for u in s.cards[c].under}
    from_under = all(o["cid"] in under_all for o in opts)

    def win(o):
        return 1 if draw_win(rules, s.cards[o["cid"]].defn) else 0

    def drw(o):
        return 1 if grave_draws(rules, s.cards[o["cid"]].defn) else 0
    if kind == "choose_evo_source" or (kind == "choose_cards" and from_under and to == "graveyard"):
        return lambda o: (win(o), -drw(o))
    if kind == "choose_cards" and zones == {"graveyard"} and to == "bz":
        return lambda o: (-win(o), 0)
    return None


# 予算切れの後の打ち切りで1手先読みする（§31）。既定は無効（従来どおり並びの先頭）
import os as _os
ROLLOUT_LOOKAHEAD = _os.environ.get("DMSIM_ROLLOUT_LOOKAHEAD", "0") == "1"
ROLLOUT_WIDTH = 4
ROLLOUT_TOTAL = 3000    # 1手の探索の中で先読みに使う総手数の上限。使い切ったら残りは並びの先頭（seed 39 が終わらなかった、§35）
ROLLOUT_DEPTH = 60      # 先読みの各候補を貪欲に進める手数の上限（ループで2000手まで回ると1局が数時間かかった）


# 経路に要る札を手札に残す口（search.route_goal.keep_hand を eval.assemble が経路つきの測定の間だけ差す）。
# callable(eng, player) -> その手番の選択で後回しにする札の定義ID の集合。None（既定）は従来どおり
KEEP_HAND = None


def _from_hand_to_grave(eng, d) -> bool:
    """この choose_cards が「手札から墓地へ捨てる札を選ぶ」か（選択肢が全部その手番のプレイヤーの手札にあり、
    待っている処理の行き先が墓地）。"""
    p = d["player"]
    if not d["options"] or not all("cid" in o and eng.s.cards[o["cid"]].zone == "hand" and eng.s.cards[o["cid"]].owner == p
                                    for o in d["options"]):
        return False
    t = eng.s.tasks[-1] if eng.s.tasks else {}
    if t.get("t") != "effect" or not (0 <= t.get("pc", -1) < len(t.get("ops") or ())):
        return False
    op = t["ops"][t["pc"]]
    return isinstance(op, dict) and op.get("to") == "graveyard"


def _card_sig(eng, cs, cid):
    r = cs(cid) if cs is not None else None
    if r is not None:
        return r
    c = eng.s.cards[cid]
    return (c.defn, tuple(sorted(eng.s.cards[u].defn for u in c.under)))


def candidates(eng: Engine, d: dict, w: Weights, cap: int = 6) -> list[list[int]]:
    """探索で試す答えの候補（良さそうな順）。複数選ぶ決定は組み合わせを cap 個まで。同じ意味キーの組は1つにまとめる。"""
    order = _rank(eng, d, w)
    if d["max"] == 1 and d["min"] == 1:
        # 区別できない選択肢（同じ種類のカード、同じ下のカードを持つシールドなど）は1つにまとめる。
        # マナの払い方は文明の組が同じなら同じとみなして、上位2通りまでにする
        out, seen = [], set()
        cs = getattr(eng, "card_sig", None)
        for i in order:
            o = d["options"][i]
            sig = (o["key"],) + (_card_sig(eng, cs, o["cid"]) if "cid" in o and o.get("name") == "?" else ())
            if sig in seen:
                continue
            seen.add(sig)
            out.append([i])
        return out[:2] if d["kind"] == "pay_mana" else out
    keys = [o["key"] for o in d["options"]]
    out, seen = [], set()
    if d["kind"] == "choose_evo_source" and DRAWOUT_ORDER():
        # §33: 勝ち手段（ドロー置換）を進化元に入れない組を先に試す（墓地に残してメテオバーンで出す）
        from .access import draw_win
        keep = [i for i in order if not draw_win(eng.rules, eng.s.cards[d["options"][i]["cid"]].defn)] if all(
            "cid" in o for o in d["options"]) else []
        if d["min"] <= len(keep[:d["max"]]) and len(keep) < len(order):
            c = keep[:d["max"]]
            seen.add(tuple(sorted(keys[i] for i in c)))
            out.append(c)          # 並べ替え: 元の順と次の順の2つまで（同じ意味キーの並びは1つ）
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
CHARGE_KEEP_FREE = os.environ.get("DMSIM_CHARGE_KEEP_FREE", "1") != "0"   # マナチャージで、今無償で出せる札を後回しにする（既定有効、0 で切る）
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
                 combo_cap: int = 6, value_fn=None, time_limit: float | None = None,
                 order_fn=None):
        self.time_limit = time_limit          # 1手の探索の実時間の上限（秒）。超えたら budget 切れと同じく貪欲に打ち切る。None は無制限（再現性のため既定）
        self.value_fn = value_fn              # 葉の評価を差し替える関数 f(eng, me)（None なら evaluate）。勝敗を使わない局面評価の測定用
        self.order_fn = order_fn              # 候補の並べ替え f(eng, d, cands) -> cands（Phase 12: 学習方策による並べ替え用。None は従来どおり）
        self.me = me
        self.deck_floor: int | None = None    # 自分の山札がこの枚数以下になる局面は探索しない（周回を回し切っての山札切れ自滅を避ける。None は無効）
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
        self.macros: list | None = None       # 登録簿の手順（search.macro）。None は macro.active()（既定は無効で空）
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
            if self.deck_floor is not None and len(eng.s.zones["deck"][self.me]) <= self.deck_floor:
                eng.s.result = {"winner": None, "reason": "deck_floor", "turn": eng.s.turn}
                break
            if n > self.rollout_cap:
                # 貪欲な手が同じ状況を繰り返して終わらない。エンジンの step_limit（約2万ステップ）まで回しても同じ結果
                # （勝者なし・-WIN/2 の評価）になるので、数秒かかる空回しを打ち切る
                eng.s.result = {"winner": None, "reason": "step_limit", "turn": eng.s.turn}
                break
            eng.answer(self._rollout_pick(eng, d))
        return eng

    def _rollout_pick(self, eng: Engine, d: dict) -> list[int]:
        """予算切れの後の1手。既定は並びの先頭（貪欲）。ROLLOUT_LOOKAHEAD（DMSIM_ROLLOUT_LOOKAHEAD=1、経路の点があるときだけ）なら、
        1つ選ぶ決定は各候補を答えて次の自分の決定まで進めた局面を評価関数で比べる（1手先読み。深いループの途中の選択を並び順で決めない）。"""
        cands = candidates(eng, d, self.w, cap=1 if not (ROLLOUT_LOOKAHEAD and self.value_fn) else 6)
        if len(cands) == 1 or not (ROLLOUT_LOOKAHEAD and self.value_fn) or not (d["max"] == 1 and d["min"] == 1) \
                or getattr(self, "_la_left", 0) <= 0:
            return cands[0]
        best, bv = cands[0], None
        for c in cands[:ROLLOUT_WIDTH]:
            e2 = eng.clone()
            try:
                e2.answer(c)
                n = 0
                while (d2 := self._settle(e2)) is not None and n < ROLLOUT_DEPTH:   # 残りは並びの先頭で（ROLLOUT_DEPTH 手まで）
                    e2.answer(candidates(e2, d2, self.w, cap=1)[0])
                    n += 1
                self._la_left -= n + 1
                v = self._eval(e2)
            except Exception:
                continue
            if bv is None or v > bv:
                best, bv = c, v
        return best

    def run(self, eng: Engine) -> tuple[Engine, TurnStats]:
        """eng（自分の決定待ち）から探索し、一番評価の高いターン終了局面の Engine を返す。eng は変更しない。"""
        self.left = self.budget
        self._la_left = ROLLOUT_TOTAL     # 先読みの総手数の残り（1手の探索あたり、§35）
        self._root_log = len(eng.log)
        self._rf = REPEAT_FIRST if self.repeat_first is None else self.repeat_first
        self._deadline = None if self.time_limit is None else time.monotonic() + self.time_limit
        self.seen: set = set()
        self._macro_nodes = 0
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
        if self.deck_floor is not None and len(eng.s.zones["deck"][self.me]) <= self.deck_floor:
            return -WIN / 2, eng, ()
        if self._deadline is not None and self.left > 0 and time.monotonic() > self._deadline:
            self.left = 0                     # 時間切れ: 以降は予算切れと同じ扱い
        if self.left <= 0:
            leaf = self._rollout(eng)
            return self._eval(leaf), leaf, ()
        h, ctr = abstract(eng, "in_turn")
        # マナは枚数だけでなく何が残っているか（文明）も区別する。払い方の違いで闇マナが残るか否かが変わる
        ex = eng.tkey_extra() if hasattr(eng, "tkey_extra") else None   # Rust で進めている局は状態を作り直さずに読む
        if ex is not None:
            mana_left, sizes = ex
        else:
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
        for child, lp in self._macro_children(eng, d):   # 登録簿の手順を1手として先に試す（既定は無効で何もしない）
            self.left -= 1
            self.stats.nodes += 1
            r = self._search(child, det.fork())
            r = (r[0], r[1], (lp,) + r[2])
            if best is None or r[0] > best[0]:
                best = r
            if best[0] >= WIN - 1000:
                return best
        cands = candidates(eng, d, self.w, self.combo_cap)
        if self.w.lookahead and len(cands) > 1:
            cands = self._lookahead_order(eng, cands)
        if self._rf and len(cands) > 1:
            cands = self._repeat_order(eng, d, cands)
        if self.order_fn is not None and len(cands) > 1:
            cands = self.order_fn(eng, d, cands)
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

    def _macro_children(self, eng: Engine, d: dict) -> list[tuple[Engine, dict]]:
        from . import macro
        ms = macro.active() if self.macros is None else self.macros
        out = []
        if not ms or self._macro_nodes >= macro.MAX_NODES:
            return out
        if any(macro.applies(m, eng, d, self.me) for m in ms):
            self._macro_nodes += 1
        else:
            return out
        for m in ms:
            if macro.applies(m, eng, d, self.me):
                child = macro.replay(m, eng, self.me, self.opp_policy, lambda e, d2: candidates(e, d2, self.w, self.combo_cap))
                self.stats.macro_tries = getattr(self.stats, "macro_tries", 0) + 1
                if child is not None:
                    self.stats.macro_hits = getattr(self.stats, "macro_hits", 0) + 1
                    out.append((child, macro.record(m)))
                    continue
                child = macro.replay_loop(m, eng, self.me, self.opp_policy, lambda e, d2: candidates(e, d2, self.w, self.combo_cap))
                if child is not None:     # 勝ちへの変換が再生できない: ループ部分だけ使って続きは探索に任せる（§23）
                    self.stats.macro_loop_hits = getattr(self.stats, "macro_loop_hits", 0) + 1
                    out.append((child, macro.record(m, loop_only=True)))
        return out

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

