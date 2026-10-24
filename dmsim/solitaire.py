"""1人回し（ソリティア）AI とキル率の測定ハーネス（ステップ4の土台）。

相手は何もしない（マナチャージだけする。ブロック・S・トリガー・召喚・攻撃はしない）。妨害は後から足す。
自分の手番は「そのターンの中の自分の選択」を深さ優先で探索し、ターン終了時の局面を評価して一番良い線を採る。
エンジンは決定的（乱数も state に入っている）なので、探索で見つけた葉の Engine をそのまま本番の局面として採用できる。

キルとして数えるもの（own_turn は自分の何ターン目か。先攻・後攻どちらでも自分のターンを 1, 2, 3 ... と数える）:
- direct_attack  シールドを割ってダイレクトアタックが通った
- deck_out       相手の山札切れ（ループをストックして削り切ったものは loop_deck_out）
- effect         「ゲームに勝つ」効果
- lock           ターンをまたぐロック（LoopDetector period="round"）。確立したターンで数える。
                 相手のマナ・手札などが周回ごとに増えないこと（相手が何も積み上げられない）と、
                 自分の山札が相手より先に尽きないこと（analyze の limit）を条件にする
ターン内ループは探索中に LoopDetector（period="in_turn"）で見つけ、verify で確かめてから fast_forward でストックする。
相手のシールドを 0 にするループ（win_by="shield_zero"）はストックした後の局面から探索を続ける（その後の攻撃を探す）。

  python -m dmsim.solitaire --deck deck.yaml --games 1000 --turns 4 --workers 4
  python -m dmsim.solitaire --deck deck.yaml --games 1 --seed 7 --record g.json   # 1局を記録（python -m dmsim.play --replay g.json）
"""
from __future__ import annotations

import itertools
import math
import time
from collections import Counter
from dataclasses import asdict, dataclass, field

from .engine import Engine
from .engine.core import IllegalAnswer
from .loop import LoopCertificate, LoopDetector, abstract, draw_keys, fast_forward, is_burn, verify
from .play import passive_policy

WIN = 1e9


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

@dataclass
class Weights:
    """ターン終了時の局面の評価の重み。キル率を見ながら調整する前提の素朴な値。"""
    shield: float = 100.0       # 相手のシールド1枚につき減点
    threat: float = 40.0        # 次のターンに攻撃できる打点（ブレイク数、シールド+1 まで）
    mana: float = 10.0
    hand: float = 4.0
    board: float = 2.0
    opp_deck: float = 3.0       # 相手の山札を削った枚数
    deck_danger: float = 60.0   # 自分の山札が少ない時の減点（自分の山札切れ対策）
    max_mana: int = 8           # これ以上はチャージしない（貪欲方策）
    stock_cap: int = 8          # 相手に効かない資源ループ（ドロー等）を1度にストックする最大周回数
    deck_keep: int = 8          # 資源ループでも自分の山札はこの枚数より減らさない


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
        return [[i] for i in order]
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


def evaluate(eng: Engine, me: int, w: Weights) -> float:
    s = eng.s
    opp = 1 - me
    if s.result is not None:
        if s.result["winner"] == me:
            return WIN - s.result["turn"]
        if s.result["winner"] == opp:
            return -WIN
        return -WIN / 2
    sh = len(eng.zlist("shield", opp))
    breaks = 0
    mine = eng.bz_tops(me)
    for c in mine:
        ch = eng.chars(c)
        if "creature" in ch["types"]:
            breaks += ch["breaks"]
    deck = len(eng.zlist("deck", me))
    self_keep = w.deck_keep
    return (-w.shield * sh + w.threat * min(breaks, sh + 1) + w.mana * len(eng.zlist("mana", me))
            + w.hand * len(eng.zlist("hand", me)) + w.board * len(mine)
            + w.opp_deck * (40 - len(eng.zlist("deck", opp)))
            - w.deck_danger * max(0, self_keep - deck))


# ---- 自分のターンの探索 -------------------------------------------------------------------------

def _is_burn(cert: LoopCertificate, me: int) -> bool:
    return not cert.win_by and is_burn(cert.delta, me)


def _is_engine(cert: LoopCertificate, me: int) -> bool:
    """相手の資源を減らさず勝ちにも直結しない（自分の資源を増やすだけの）ループ。"""
    return not cert.win_by and not any(v < 0 for k, v in cert.delta.items() if k.endswith(f":{1 - me}"))


class Detectors:
    """ターン内ループの検出器の組。手札の中身まで見る厳密なものと、ドローを含むループ用に
    手札の中身をぼかす（draw_keys 以外は枚数だけ数える）ものを並べて走らせる。"""

    def __init__(self, dets: list[LoopDetector]):
        self.dets = dets

    @classmethod
    def new(cls, eng: Engine, me: int) -> "Detectors":
        return cls([LoopDetector(me=me, period="in_turn"),
                    LoopDetector(me=me, period="in_turn", hand_keys=draw_keys(eng, me), engine_loops=True),
                    LoopDetector(me=me, period="in_turn", burn_loops=True)])

    def fork(self) -> "Detectors":
        return Detectors([d.fork() for d in self.dets])

    def observe(self, eng: Engine) -> LoopCertificate | None:
        found = [c for c in (d.observe(eng) for d in self.dets) if c is not None]
        return found[0] if found else None


@dataclass
class TurnStats:
    nodes: int = 0
    loops: list[dict] = field(default_factory=list)


class TurnSearch:
    """自分のターンの中の選択を深さ優先で探索する。budget を使い切ったら残りは貪欲方策で打ち切る。

    - 同じ骨格＋同じカウンタの局面は1度だけ展開する（マナの払い方の違いなど）。
    - 同じ骨格に戻り、相手側のカウンタが減っていればループ（LoopCertificate）。verify で確かめてから
      fast_forward で必要な周回だけ進め、その局面を子として探索を続ける。"""

    def __init__(self, me: int, budget: int = 200, weights: Weights | None = None, opp_policy=charge_only_policy,
                 combo_cap: int = 6):
        self.me = me
        self.budget = budget
        self.w = weights or Weights()
        self.opp_policy = opp_policy
        self.combo_cap = combo_cap

    def _settle(self, eng: Engine) -> dict | None:
        """相手の決定を相手役に答えさせながら、自分の決定かターン終了まで進める。"""
        while True:
            d = eng.advance()
            if d is None or eng.s.active != self.me:
                return None
            if d["player"] == self.me:
                return d
            eng.answer(self.opp_policy(eng, d))

    def _rollout(self, eng: Engine) -> Engine:
        while (d := self._settle(eng)) is not None:
            eng.answer(candidates(eng, d, self.w, cap=1)[0])
        return eng

    def run(self, eng: Engine) -> tuple[Engine, TurnStats]:
        """eng（自分の決定待ち）から探索し、一番評価の高いターン終了局面の Engine を返す。eng は変更しない。"""
        self.left = self.budget
        self.seen: set = set()
        self.stats = TurnStats()
        det = Detectors.new(eng, self.me)
        best = self._search(eng.clone(), det)
        return best[1], self.stats

    def _search(self, eng: Engine, det: Detectors) -> tuple[float, Engine]:
        d = self._settle(eng)
        if d is None:
            return evaluate(eng, self.me, self.w), eng
        if self.left <= 0:
            leaf = self._rollout(eng)
            return evaluate(leaf, self.me, self.w), leaf
        h, ctr = abstract(eng, "in_turn")
        # マナは枚数だけでなく何が残っているか（文明）も区別する。払い方の違いで闇マナが残るか否かが変わる
        mana_left = tuple(sorted((c.defn, c.tapped) for c in (eng.s.cards[x] for p in (0, 1) for x in eng.s.zones["mana"][p])))
        tkey = (h, tuple(sorted(ctr.items())), mana_left)
        cert = det.observe(eng)
        if cert is not None and _is_burn(cert, self.me):
            # 山札を削るだけのループ: 勝ちにつながるかは分からないので、山札を残り1枚まで削った線（遅く抜ける）を試す。
            # ループに入った直後に抜ける線は親の局面で試されるので、ここでループの続きは辿らない
            ff = self._stock(eng, cert)
            if ff is not None:
                return self._search(ff, Detectors.new(ff, self.me))
            cert = None
        if cert is not None:
            ff = self._stock(eng, cert)
            if ff is not None:
                return self._search(ff, Detectors.new(ff, self.me))
            if _is_engine(cert, self.me):
                return -WIN, eng      # 資源ループはストックし切った。同じ周回を1つずつ辿り直さない（山札を減らすだけ）
        if tkey in self.seen:
            return -WIN, eng          # 既に展開した局面（ループの途中で戻ってきた場合もここ）
        self.seen.add(tkey)
        best: tuple[float, Engine] | None = None
        for choice in candidates(eng, d, self.w, self.combo_cap):
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

    def _stock(self, eng: Engine, cert: LoopCertificate) -> Engine | None:
        """ループを確かめてストックした局面を返す。勝ちにつながらない・確かめられないなら None。"""
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
            return None
        ff = eng.clone()
        try:
            fast_forward(ff, cert, n)
        except IllegalAnswer:
            return None
        self.stats.loops.append({"win_by": cert.win_by, "needed": cert.needed, "limit": cert.limit,
                                 "delta": cert.delta, "length": len(cert.actions), "stocked": n,
                                 "kind": "burn" if burn else "engine" if engine else "kill"})
        return ff


# ---- 1局 ----------------------------------------------------------------------------------------

@dataclass
class GameResult:
    seed: int
    first_player: int
    kill_turn: int | None = None      # 自分の何ターン目に勝ち（またはロック確立）
    origin: str | None = None         # lock / loop（ループで山札・シールドを削った）/ engine（資源ループの後に殴った・決めた）/ combat / effect
    kind: str | None = None           # direct_attack / deck_out / loop_deck_out / effect / lock
    lost: str | None = None           # 自分が負けた理由（deck_out など）
    loops: list[dict] = field(default_factory=list)
    lock: dict | None = None
    nodes: int = 0
    decisions: int = 0
    seconds: float = 0.0
    error: str | None = None


def _lock_ok(cert: LoopCertificate, me: int) -> bool:
    """相手の資源が周回ごとに増えない（山札と墓地以外の相手側カウンタの差分が 0 以下）ロックだけを認める。"""
    opp = f":{1 - me}"
    grows = any(v > 0 for k, v in cert.delta.items()
                if k.endswith(opp) and not k.startswith(("deck:", "graveyard:")))
    return cert.win_by == "opp_deck_out" and not grows


def _origin(res: GameResult) -> str:
    """勝ち方の由来。ループで相手の山札・シールドを削ってから決めたものを、殴り勝ちや効果だけの勝ちと分ける。"""
    if any(lp["win_by"] for lp in res.loops):
        return "loop"
    if res.loops:
        return "engine"
    return "combat" if res.kind == "direct_attack" else "effect"


def lock_probe(eng: Engine, me: int, rounds: int = 2) -> LoopCertificate | None:
    """「ここで自分が何もしなくなっても、相手は山札切れまで何もできないか」を確かめる。
    自分は何もしない（passive）、相手はマナチャージだけして rounds+1 周回し、ラウンド周期の骨格の回帰を探す。
    自分が動き続ける本番の対戦では骨格が毎ターン変わるので、ロックはこの別の試し回しで見る。"""
    e = eng.clone()
    det = LoopDetector(me=me, period="round", hand_keys=set())
    seen_turns, last = 0, None
    while (d := e.advance()) is not None:
        if e.s.active == me and d["player"] == me and e.s.turn != last:
            last = e.s.turn
            seen_turns += 1
            cert = det.observe(e)
            if cert is not None:
                return cert if _lock_ok(cert, me) and verify(e, cert, times=2).verified == 2 else None
            if seen_turns > rounds:
                return None
        e.answer(passive_policy(e, d) if d["player"] == me else charge_only_policy(e, d))
    return None


def play_game(rules, deck: list[str], opp_deck: list[str], seed: int, *, first_player: int = 0,
              max_turn: int = 4, budget: int = 200, weights: Weights | None = None,
              lock_rounds: int = 2, start: Engine | None = None) -> tuple[GameResult, Engine]:
    """自分 = プレイヤー0。自分の max_turn ターン目が終わるまで回す。各ターンの後に lock_probe でロックを確かめる。
    start（dmsim.scenario.build で作った局面など）を渡すとそこから始める（deck / opp_deck / seed は使わない）。"""
    me = 0
    t0 = time.perf_counter()
    res = GameResult(seed=seed, first_player=first_player)
    eng = start.clone() if start is not None else Engine.new_game(rules, [deck, opp_deck], seed, first_player)
    search = TurnSearch(me, budget, weights)
    try:
        while (d := eng.advance()) is not None:
            if eng.s.active != me or d["player"] != me:
                eng.answer(charge_only_policy(eng, d))
                continue
            ot = own_turn(eng, me)
            if ot > max_turn:
                break
            eng, st = search.run(eng)
            res.nodes += st.nodes
            res.loops += [dict(lp, own_turn=ot) for lp in st.loops]
            if eng.s.result is None and lock_rounds > 0:
                cert = lock_probe(eng, me, lock_rounds)
                if cert is not None:
                    res.kind, res.kill_turn = "lock", ot
                    res.lock = {"delta": cert.delta, "needed_rounds": cert.needed, "limit": cert.limit}
                    break
        r = eng.s.result
        if res.kind == "lock":
            res.origin = "lock"
        if r is not None and res.kind is None:
            if r["winner"] == me:
                res.kill_turn = own_turn(eng, me, r["turn"])
                res.kind = r["reason"]
                if r["reason"] == "deck_out" and any(lp["win_by"] == "opp_deck_out" for lp in res.loops):
                    res.kind = "loop_deck_out"
                res.origin = _origin(res)
            elif r["winner"] == 1 - me:
                res.lost = r["reason"]
    except Exception as ex:          # 1局の失敗で全体を止めない。seed で再現できる
        res.error = f"{type(ex).__name__}: {ex}"
    res.decisions = len(eng.log)
    res.seconds = time.perf_counter() - t0
    return res, eng


# ---- 大量試行と集計 -----------------------------------------------------------------------------

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def summarize(results: list[GameResult], max_turn: int) -> dict:
    n = len(results)
    by_turn = {}
    for t in range(1, max_turn + 1):
        k = sum(1 for r in results if r.kill_turn is not None and r.kill_turn <= t)
        lo, hi = wilson(k, n)
        by_turn[t] = {"kills": k, "rate": k / n if n else 0.0, "ci95": [lo, hi]}
    counted = [r for r in results if r.kill_turn is not None and r.kill_turn <= max_turn]
    return {
        "games": n,
        "kill_rate_by_turn": by_turn,
        "kinds": dict(Counter(r.kind for r in counted)),
        "origins": dict(Counter(r.origin for r in counted)),
        "loop_kill_rate_by_turn": {t: sum(1 for r in results if r.origin in ("loop", "lock") and r.kill_turn is not None
                                          and r.kill_turn <= t) / n if n else 0.0 for t in range(1, max_turn + 1)},
        "lost": dict(Counter(r.lost for r in results if r.lost)),
        "errors": [{"seed": r.seed, "first_player": r.first_player, "error": r.error} for r in results if r.error],
        "loop_games": sum(1 for r in results if r.loops),
        "mean_seconds": sum(r.seconds for r in results) / n if n else 0.0,
        "mean_nodes": sum(r.nodes for r in results) / n if n else 0.0,
        "kill_seeds": [[r.seed, r.first_player, r.kill_turn, r.kind] for r in counted][:50],
    }


_W: dict = {}


def _init_worker(cards_paths):
    from .defs import load_rules
    _W["rules"] = load_rules(cards_paths)


def _one(args):
    deck, opp_deck, seed, fp, kw = args
    res, _ = play_game(_W["rules"], deck, opp_deck, seed, first_player=fp, **kw)
    return res


def measure(deck: list[str], opp_deck: list[str], seeds, *, first: str = "both", workers: int = 1,
            rules=None, **kw) -> list[GameResult]:
    """seeds × 先攻/後攻 の全局を回す。workers>1 ならプロセスを分けて並列に回す（結果は seed 順）。"""
    fps = {"first": [0], "second": [1], "both": [0, 1]}[first]
    jobs = [(deck, opp_deck, s, fp, kw) for s in seeds for fp in fps]
    if workers <= 1:
        _W["rules"] = rules if rules is not None else _W.get("rules")
        if _W["rules"] is None:
            _init_worker(None)
        return [_one(j) for j in jobs]
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(workers, initializer=_init_worker, initargs=(None,)) as ex:
        return list(ex.map(_one, jobs, chunksize=max(1, len(jobs) // (workers * 8))))


def load_deck(path: str) -> list[str]:
    """YAML: {deck: [id, ...]} か {cards: {id: 枚数}}。"""
    from pathlib import Path

    import yaml
    y = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if "deck" in y:
        return list(y["deck"])
    return [cid for cid, n in y["cards"].items() for _ in range(n)]


def main(argv=None):
    import argparse
    import json
    from pathlib import Path

    from .defs import load_rules
    from .play import default_decks, make_record
    ap = argparse.ArgumentParser(description="1人回しで N ターン目までのキル率を測る")
    ap.add_argument("--deck", help="自分のデッキ（YAML）。省略時は実カードを繰り返した40枚")
    ap.add_argument("--opp-deck", help="相手のデッキ（YAML）。省略時は T001×40")
    ap.add_argument("--games", type=int, default=100, help="seed の数（--first both なら局数はその2倍）")
    ap.add_argument("--seed", type=int, default=1, help="最初の seed")
    ap.add_argument("--first", choices=["first", "second", "both"], default="both")
    ap.add_argument("--turns", type=int, default=4, help="何ターン目までのキルを数えるか")
    ap.add_argument("--budget", type=int, default=200, help="1ターンの探索で展開する局面数（0 で貪欲方策のみ）")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", help="集計と各局の結果（JSON）の保存先")
    ap.add_argument("--record", help="最初の1局の対戦記録（JSON）。python -m dmsim.play --replay で再生できる")
    a = ap.parse_args(argv)
    rules = load_rules()
    deck = load_deck(a.deck) if a.deck else default_decks(rules, "dm")[0]
    opp_deck = load_deck(a.opp_deck) if a.opp_deck else ["T001"] * 40
    kw = {"max_turn": a.turns, "budget": a.budget}
    if a.record:
        fp = 1 if a.first == "second" else 0
        res, eng = play_game(rules, deck, opp_deck, a.seed, first_player=fp, **kw)
        Path(a.record).write_text(json.dumps(make_record(eng, [deck, opp_deck], a.seed, fp,
                                                         note=json.dumps(asdict(res), ensure_ascii=False)),
                                             ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(asdict(res), ensure_ascii=False))
        return
    t0 = time.perf_counter()
    results = measure(deck, opp_deck, range(a.seed, a.seed + a.games), first=a.first, workers=a.workers,
                      rules=rules, **kw)
    summ = summarize(results, a.turns)
    summ["wall_seconds"] = time.perf_counter() - t0
    for t, v in summ["kill_rate_by_turn"].items():
        print(f"turn {t}: {v['rate']:.1%}  ({v['kills']}/{summ['games']}, 95%CI {v['ci95'][0]:.1%}-{v['ci95'][1]:.1%})")
    print(f"origins={summ['origins']} loop/lock kill rate by turn={ {t: f'{v:.1%}' for t, v in summ['loop_kill_rate_by_turn'].items()} }")
    print(f"kinds={summ['kinds']} lost={summ['lost']} errors={len(summ['errors'])} "
          f"loop_games={summ['loop_games']} wall={summ['wall_seconds']:.1f}s")
    if a.out:
        Path(a.out).write_text(json.dumps({"summary": summ, "games": [asdict(r) for r in results]},
                                          ensure_ascii=False, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
