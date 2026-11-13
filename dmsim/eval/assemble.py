"""物差しの「① 揃う」と「④ 速さ」（S4、docs/combo-ruler-design.md §6 タスク6）。

入口局面の定義 data/loops/entry/<コンボ>.json（LoopSpec.minimal）から条件を機械的に取る。コンボごとの手書き条件は増やさない。
- 中核 core_alts: 入口局面の中核の組（loop_entry.core_groups。source.core に「どれか1組でよい」代わりを書ける、§14）から作った
  {ID: 枚数} の候補。source.core がなければ minimal のうち札の名前で指した述語（ゾーンを問わず合計）。基盤札は数えない（§9）。
- 揃う（cards）: 候補のどれか1つが山札・盾以外の自分のゾーンに揃った（eval.stage.cards_met と同じ意味）。
- 入口（entry）: minimal の全述語（ゾーン・文明・墓地のクリーチャー数など）を満たした（loop_entry.unmet が空）。
(a) 素引き確率 raw_table: eval.reach.cards_ceiling（サーチ・ドローなし、先後平均の厳密計算。下限の理論値）。
(b) 実測 measure: 通常の開幕から FAIR（山札は見えない公平探索、search.fair.FairTurnSearch）で回し、自分の各ターン終了時に
    揃う・入口を判定して最初のターンを記録する。回し方は search.game.fair_game と同じ（同じ seed なら同じ手順）。
④ 速さ: 同じ対局を ruler.judge にかけ、勝ったターンと勝ち方を別欄で集計する（summarize）。
ループの記録: play_turns(record=res) で、FAIR でも採った手のループ（決定化の探索が使った証明書、無ければ指した手順の
     パターン検出）を GameResult.loops に残す（案 F）。勝利効果・山札切れの勝ち effect_win を、ループ由来 effect_loop と
     それ以外 effect_other に分けて出す。lock_probe は含めない。
     相手はマナチャージだけ（決定事項 §7-5）なので殴り勝ちは甘く出る。
"""
from __future__ import annotations

import time
from collections import Counter

from ..engine.core import Engine
from ..engine.view import cards_met, result_of
from ..play_api import InfoLevel, PlayConfig, play_turns
from ..search.game import GameResult
from ..search.opponent import resistance
from ..search import route_goal as RG
from ..search.game import finish_result
from . import loop_entry as L
from .measure import wilson
from .reach import cards_ceiling
from .ruler import judge

EFFECT_KINDS = ("effect", "state", "deck_out", "loop_deck_out")
NOTE = "相手はマナチャージだけ（ブロッカー・S・トリガーなし）なので殴り勝ちは甘く出る。effect_win（勝利効果・山札切れ勝ち）= effect_loop（勝ちより前にループを回した）+ effect_other"


def core_need(ls) -> dict:
    """代わりの組の1つめ（表示・互換用）。揃ったかの判定は core_alts のどれか1つで行う。"""
    alts = L.core_alternatives(ls)
    return alts[0] if alts else {}


def core_alts(ls) -> list[dict]:
    return L.core_alternatives(ls)


def any_met(eng, me: int, alts: list[dict]) -> bool:
    return any(cards_met(eng, me, a) for a in alts)


def any_ceiling(deck, alts: list[dict], turn: int) -> float:
    """代わりの組のどれか1つが揃う素引き確率（包除原理。2組が両方揃う = 札ごとの必要枚数の最大が揃う）。"""
    from itertools import combinations
    tot = 0.0
    for r in range(1, len(alts) + 1):
        for sub in combinations(alts, r):
            need: Counter = Counter()
            for a in sub:
                for i, k in a.items():
                    need[i] = max(need[i], k)
            tot += (-1) ** (r + 1) * cards_ceiling(deck, dict(need), turn)
    return tot


def raw_table(ls, turns=(3, 4, 6), deck=None) -> dict:
    deck = deck or L.deck_of(ls)
    alts = core_alts(ls)
    return {t: any_ceiling(deck, alts, t) for t in turns}


def run_one(rules, ls, seed: int, *, deck=None, opp_deck=None, max_turn: int = 6, budget: int = 200, n_det: int = 8,
            opp_level: int = 0, route: str | None = None, route_log: str | None = None,
            route_opts: dict | None = None):
    """1局。戻り値 dict: seed, first, opp, cards_turn, entry_turn（0=開始時、未到達 None）, verdict（ruler.judge）, res。
    opp_level: 相手の抵抗の段階（search.opponent.resistance）。0 は従来の無抵抗。opp_deck を渡すとデッキだけ差し替える。
    route: 経路の名前（data/loops/route/）。渡すと葉の評価に経路の段の点を足す（search.route_goal、既定 None は従来どおり）。
    route_opts: search.route_goal.make_value_fn の切り替え（mult / partial / elsewhere / away）。
    段の到達は route を渡さなくても名前があれば記録したいので、記録だけは route_log で別に指定できる。"""
    deck = list(deck or L.deck_of(ls))
    opp_model, lvl_deck = resistance(opp_level)
    opp_deck = list(opp_deck or lvl_deck)
    first = seed % 2
    alts = core_alts(ls)
    me = 0
    t0 = time.perf_counter()
    res = GameResult(seed=seed, first_player=first, opp=opp_model.name if opp_model else "none")
    rec = {"cards_turn": None, "entry_turn": None, "entry_mana": None, "route": route, "stage_turn": {}}
    stages = RG.load(route_log or route) if (route_log or route) else ()
    eng = Engine.new_game(rules, [deck, opp_deck], seed, first)
    if opp_model is not None:
        opp_model.setup(eng)

    def record(e, t):
        if rec["cards_turn"] is None and alts and any_met(e, me, alts):
            rec["cards_turn"] = t
        if rec["entry_turn"] is None and not L.unmet(e, ls):
            rec["entry_turn"] = t
            rec["entry_mana"] = len(e.s.zones["mana"][me])
        if stages:
            for i, st in enumerate(stages, 1):
                if i not in rec["stage_turn"] and all(RG.holds(e, p, me) for p in st.preds):
                    rec["stage_turn"][i] = t

    opts = dict(route_opts or {})
    ratchet = [0] if opts.pop("ratchet", False) else None   # route_opts={"ratchet": True}: 達成済みの段を下げない
    holder = [eng]
    try:
        cfg = PlayConfig(seed=seed, max_turn=max_turn, budget=budget, n_det=n_det, me=me,
                         value_fn=RG.make_value_fn(stages, ratchet=ratchet, opp_policy=opp_model.policy if opp_model else None,
                                                  **opts) if route else None)

        def on_turn(e, ot, nodes):
            res.nodes += nodes
            record(e, ot)
            if ratchet is not None:
                RG.note_reached(e, stages, ratchet, me)

        eng.advance()
        record(eng, 0)
        eng = play_turns(eng, cfg, InfoLevel.FAIR, on_turn=on_turn, holder=holder, record=res,
                         opp_policy=opp_model.policy if opp_model else None)
        finish_result(res, eng, me)
        r = result_of(eng)
        if r is not None and r["winner"] is None:
            res.lost = r["reason"]
    except Exception as ex:
        res.error = f"{type(ex).__name__}: {ex}"
        eng = holder[0]
    rec["entry_unmet"] = [f"{q.zone or '/'.join(q.zones)}:{q.match}{q.op}{q.n}" for q in L.unmet(eng, ls)]   # 終局（打ち切り）時に満たしていない入口の述語
    res.decisions = len(eng.log)
    res.seconds = time.perf_counter() - t0
    return dict(seed=seed, first=first, opp=res.opp, **rec, verdict=judge(res, eng), res=res)


def measure(rules, name: str, seeds, **kw) -> list[dict]:
    ls = L.load(name)
    return [run_one(rules, ls, s, **kw) for s in seeds]


def _dist(xs, horizon):
    c = Counter(x for x in xs if x is not None)
    return {t: c.get(t, 0) for t in range(0, horizon + 1)}


def summarize(rows, *, ls=None, turns=(3, 4, 6), kill_turns=(3, 4)) -> dict:
    """揃う（素引き・実測の割合とターン分布）と速さ（T ターン目までのキル率、別欄）を1つの辞書にまとめる。"""
    n = len(rows)
    horizon = max(turns)
    out = {"games": n, "note": NOTE, "opp": sorted({r.get("opp", "none") for r in rows}), "core": core_alts(ls) if ls is not None else None,
           "raw": raw_table(ls, turns) if ls is not None else None,
           "cards_by_turn": {}, "entry_by_turn": {}, "kill": {},
           "cards_turn_dist": _dist([r["cards_turn"] for r in rows], horizon),
           "entry_turn_dist": _dist([r["entry_turn"] for r in rows], horizon),
           "errors": sum(1 for r in rows if r["res"].error),
           "entry_unmet_final": dict(Counter(u for r in rows if r["cards_turn"] is not None for u in r.get("entry_unmet", ())))}
    for t in turns:
        for key, col in (("cards_turn", "cards_by_turn"), ("entry_turn", "entry_by_turn")):
            k = sum(1 for r in rows if r[key] is not None and r[key] <= t)
            out[col][t] = {"k": k, "rate": k / n if n else 0.0, "ci95": wilson(k, n) if n else (0.0, 0.0)}
    for t in kill_turns:
        won = [r for r in rows if r["verdict"].stage2.kill and r["verdict"].stage2.win_turn <= t]
        col = {"kill": len(won),
               "loop_win": sum(1 for r in won if r["verdict"].stage2.loop_win),
               "effect_win": sum(1 for r in won if r["res"].kind in EFFECT_KINDS),
               "effect_loop": sum(1 for r in won if r["res"].kind in EFFECT_KINDS and r["verdict"].stage2.via == "loop"),
               "effect_other": sum(1 for r in won if r["res"].kind in EFFECT_KINDS and r["verdict"].stage2.via != "loop"),
               "beat_win": sum(1 for r in won if r["verdict"].stage2.beat_win)}
        col["rate"] = col["kill"] / n if n else 0.0
        col["ci95"] = wilson(col["kill"], n) if n else (0.0, 0.0)
        out["kill"][t] = col
    wins = [r["verdict"].stage2.win_turn for r in rows if r["verdict"].stage2.kill]
    out["win_turn_dist"] = dict(sorted(Counter(wins).items()))
    out["win_via"] = dict(Counter(r["verdict"].stage2.via or "none" for r in rows))
    return out
