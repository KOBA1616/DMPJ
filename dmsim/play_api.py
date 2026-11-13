"""探索・プレイの窓口 play/api（S3、ロードマップ P0-2）。

S4 以上（評価・発見・自動改善・デッキ構築・tools）は、探索を直接呼ばずにここを通す。
    play(局面, 設定, 情報水準) -> PlayResult
- 局面: 開始局面の Engine（None ならデッキとシードから新しく始める。mode="game" のみ）。渡した Engine は書き換えない。
- 設定: PlayConfig（不変）。mode で中身の探索を選ぶ。探索ロジック自体はここでは変えない（振り分けるだけ）。
    game  : 1局を回す。CHEAT は search.game.play_game（TurnSearch）、FAIR は search.fair.FairTurnSearch（n_det・lookahead=複数ターン探索）
    chain : 段階目標の鎖への到達 search.reachsearch.reach_chain（大局観の prio を渡せる）
    beam  : 勝ちまでのビーム探索 search.bestfirst.beam
- 情報水準: InfoLevel。既定 FAIR。chain / beam は真の山札順を見る探索なので CHEAT を明示したときだけ動く（FAIR は未実装）。
1ターンごとに処理を挟みたい呼び出し側（評価の盤面記録・使用率の監査など）は play_turns(局面, 設定, 情報水準, on_turn=...) を使う。
同じ入力なら同じ出力（エンジン・探索とも乱数は seed と局面に入っている。time_limit 等の実時間打ち切りは使わない）。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

API_VERSION = 1


class InfoLevel(str, Enum):
    """情報水準。CHEAT = 真の山札順を見る（教師・診断・上限値のみ）。FAIR = 山札は多重集合から決定化（採否はこちら）。"""
    CHEAT = "cheat"
    FAIR = "fair"


MODES = ("game", "chain", "beam")


@dataclass(frozen=True)
class PlayConfig:
    """1回のプレイの設定（不変）。使わない項目は mode ごとに無視される。"""
    mode: str = "game"
    deck: tuple[str, ...] = ()             # start が None のときのデッキ（自分 = プレイヤー0）
    opp_deck: tuple[str, ...] = ()
    seed: int = 0
    first_player: int = 0
    max_turn: int = 4                      # game: 自分の何ターン目まで / chain・beam: 通しターンの上限
    # game
    budget: int = 200                      # 1ターンの探索予算（ノード数）
    n_det: int = 8                         # FAIR の決定化数
    lookahead: int = 0                     # FAIR の複数ターン探索の予算（0 で無効）
    lock_rounds: int = 2                   # CHEAT のロック判定の周回（0 で判定しない）
    weights: Any = None                    # search.leaf_eval.Weights
    value_fn: Callable | None = None       # 葉の評価の差し替え f(eng, me)（CHEAT のみ）
    opp: Any = None                        # dmsim.search.opponent.OppModel（None は何もしない相手）
    lock_judge: Callable | None = None     # CHEAT のロック判定役 f(eng, me, rounds)（None は登録済みの既定 = eval.lockcheck.lock_probe）
    # chain / beam
    stages: tuple = ()                     # chain: 段階目標（dict）の並び
    width: int = 150
    max_depth: int = 80
    prio: Callable | None = None           # 大局観などの順位づけ f(eng, me)（None は既定の priority）
    keep_later: bool = True                # chain
    chain_lookahead: int = 2               # chain の先読み段数
    reserve: int = 0                       # chain: 次の段に近い局面へ予約する枠
    me: int = 0
    version: int = API_VERSION

    def __post_init__(self):
        if self.mode not in MODES:
            raise ValueError(f"mode は {MODES} のどれか: {self.mode}")


@dataclass
class PlayResult:
    """プレイの結果。actions は採った手順（エンジンの決定ログ）。"""
    mode: str
    info: InfoLevel
    won: bool
    kill_turn: int | None                  # game: 自分の何ターン目に勝ち / beam: 勝った通しターン / chain: None
    kind: str | None = None                # 勝ち方（game のみ）
    stages: int | None = None              # chain: 到達した段階数
    turns: list = field(default_factory=list)   # chain: 各段階の到達ターン
    nodes: int = 0
    actions: list = field(default_factory=list)
    log: dict = field(default_factory=dict)     # 探索ごとの詳細（game は GameResult の中身）
    game: Any = None                       # game: search.game.GameResult（従来の呼び出し元の互換用）
    engine: Any = None                     # 終局（打ち切り）時の局面
    seconds: float = 0.0
    version: int = API_VERSION


def _new_engine(rules, cfg: PlayConfig):
    from .engine.core import Engine
    return Engine.new_game(rules, [list(cfg.deck), list(cfg.opp_deck)], cfg.seed, cfg.first_player)


from .search.game import fair_game  # noqa: E402,F401  P0-3 で search/game.py へ移した（旧名の互換）


def _from_game(cfg, info, res, eng, t0) -> PlayResult:
    from dataclasses import asdict
    return PlayResult(mode="game", info=info, won=res.kill_turn is not None, kill_turn=res.kill_turn, kind=res.kind,
                      nodes=res.nodes, actions=list(eng.log), log=asdict(res), game=res, engine=eng,
                      seconds=time.perf_counter() - t0)


def play(start, cfg: PlayConfig, info: InfoLevel = InfoLevel.FAIR, *, rules=None) -> PlayResult:
    """窓口。start は開始局面の Engine（None なら rules・cfg.deck・cfg.seed から始める。game のみ）。"""
    info = InfoLevel(info)
    t0 = time.perf_counter()
    if cfg.mode == "game":
        if start is None and rules is None:
            raise ValueError("start が None のときは rules が要る")
        if info is InfoLevel.CHEAT:
            from .search.game import play_game
            res, eng = play_game(rules, list(cfg.deck), list(cfg.opp_deck), cfg.seed, first_player=cfg.first_player,
                                 max_turn=cfg.max_turn, budget=cfg.budget, weights=cfg.weights, lock_rounds=cfg.lock_rounds,
                                 start=start, opp=cfg.opp, value_fn=cfg.value_fn,
                                 lock_judge=cfg.lock_judge)
        else:
            if cfg.value_fn is not None or cfg.weights is not None:
                raise NotImplementedError("FAIR の game は value_fn / weights の差し替え未対応（eval.progress 経由で使う）")
            res, eng = fair_game(rules, list(cfg.deck), list(cfg.opp_deck), cfg.seed, cfg.first_player, cfg.max_turn,
                                 cfg.budget, start=start, opp=cfg.opp, n_det=cfg.n_det, lookahead=cfg.lookahead)
        return _from_game(cfg, info, res, eng, t0)
    if info is not InfoLevel.CHEAT:
        raise NotImplementedError(f"mode={cfg.mode} は真の山札順を見る探索。FAIR 版は未実装（info=InfoLevel.CHEAT を明示する）")
    eng = start if start is not None else _new_engine(rules, cfg)
    if cfg.mode == "chain":
        from .search.reachsearch import reach_chain
        kw = {"reserve": cfg.reserve} if cfg.reserve else {}
        r = reach_chain(eng, list(cfg.stages), cfg.me, keep_later=cfg.keep_later, lookahead=cfg.chain_lookahead,
                        width=cfg.width, max_depth=cfg.max_depth, max_turn=cfg.max_turn, prio=cfg.prio, **kw)
        end = r["engine"]
        return PlayResult(mode="chain", info=info, won=r["stages"] == len(cfg.stages) and len(cfg.stages) > 0, kill_turn=None,
                          stages=r["stages"], turns=list(r["turns"]), nodes=r["nodes"], actions=list(end.log),
                          log={"stages": r["stages"], "turns": list(r["turns"])}, engine=end, seconds=time.perf_counter() - t0)
    from .search.bestfirst import beam
    from dmsim.engine.view import turn_of
    r = beam(eng, cfg.me, width=cfg.width, max_depth=cfg.max_depth, max_turn=cfg.max_turn, prio=cfg.prio)
    return PlayResult(mode="beam", info=info, won=r.won, kill_turn=turn_of(r.engine) if r.won else None, nodes=r.nodes,
                      actions=list(r.engine.log), log={"log_len": r.log_len}, engine=r.engine, seconds=time.perf_counter() - t0)


def play_turns(eng, cfg: PlayConfig, info: InfoLevel = InfoLevel.FAIR, *, opp_policy=None, before_turn=None,
               on_turn=None, reuse_search: bool = True, holder: list | None = None, record=None):
    """1局の手番ループ（search.game.run_turns）を、自分のターンごとに呼び出し側の処理を挟んで回す。最後の局面を返す。
    - eng: 開始局面。そのまま進める（clone しない。必要なら呼び出し側で clone）。
    - 設定で使う項目: max_turn・budget・value_fn、FAIR は n_det・lookahead・seed（各ターンの決定化の種は seed*7919+ターン）。
    - opp_policy: 相手の決定 f(eng, d)。None は何もしない相手（charge_only）。妨害モデルの setup は呼び出し側で済ませる。
    - before_turn(eng, ot): 自分のターンの探索の前。on_turn(eng, ot, nodes): 探索の後（eng はそのターン後の局面）。
      どちらかが True を返すとそこで打ち切る。
    - reuse_search: CHEAT の TurnSearch を全ターンで使い回す（False はターンごとに作り直す）。
    - holder: 渡すと holder[0] に常に最新の局面を入れる（途中で例外が出ても呼び出し側が最新の局面を見られる）。
    - record: GameResult を渡すと、各ターンのループ（採った手順の証明書、無ければ指した手順のパターン検出）を
      record.loops / loop_candidates に足す（search.game.record_turn_loops。手順は変えない）。"""
    from .search.game import record_turn_loops, run_turns
    from .search.turn import TurnSearch, charge_only_policy
    info = InfoLevel(info)
    me = cfg.me
    opp_pol = opp_policy or charge_only_policy
    cur = holder if holder is not None else [None]
    cur[:1] = [eng]
    shared = [None]

    def take_turn(e, ot):
        if before_turn is not None and before_turn(e, ot):
            return e, True
        before, at = e, len(e.log)
        if info is InfoLevel.CHEAT:
            if not reuse_search or shared[0] is None:
                shared[0] = TurnSearch(me, cfg.budget, opp_policy=opp_pol, value_fn=cfg.value_fn)
            e, st = shared[0].run(e)
            nodes, chosen, cands = st.nodes, st.chosen, st.loops
        else:
            from .search.fair import FairTurnSearch
            fs = FairTurnSearch(me, cfg.budget, cfg.n_det, cfg.seed * 7919 + ot, opp_policy=opp_pol,
                                value_fn=cfg.value_fn, lookahead=cfg.lookahead)
            e = fs.run(e)
            nodes, chosen, cands = fs.nodes, fs.chosen, fs.loops
        if record is not None:
            record_turn_loops(record, before, e, at, chosen, cands, ot, me)
        cur[0] = e
        stop = on_turn(e, ot, nodes) if on_turn is not None else False
        return e, bool(stop)

    run_turns(cur, me, cfg.max_turn, opp_pol, take_turn)
    return cur[0]


def search_turn(eng, cfg: PlayConfig, info: InfoLevel = InfoLevel.FAIR, *, opp_policy=None,
                burn_stock=None, stock_offsets=None):
    """自分の1ターンだけを探索する（P1-S5: tools の TurnSearch / FairTurnSearch 直接呼び出しをここへ寄せた）。
    返り値は (そのターン後の局面, 探索ノード数)。渡した eng は探索器と同じ扱い（従来の直接呼び出しと同一の結果）。
    - 設定で使う項目: me・budget・weights・value_fn、FAIR は n_det・lookahead・seed（seed はそのまま決定化の種）。
    - opp_policy: 相手の決定 f(eng, d)。None は何もしない相手（charge_only）。
    - burn_stock / stock_offsets: CHEAT の TurnSearch の同名属性（None なら既定のまま）。"""
    from .search.turn import TurnSearch, charge_only_policy
    info = InfoLevel(info)
    opp_pol = opp_policy or charge_only_policy
    if info is InfoLevel.CHEAT:
        ts = TurnSearch(cfg.me, cfg.budget, weights=cfg.weights, opp_policy=opp_pol, value_fn=cfg.value_fn)
        if burn_stock is not None:
            ts.burn_stock = burn_stock
        if stock_offsets is not None:
            ts.stock_offsets = tuple(stock_offsets)
        out, st = ts.run(eng)
        return out, st.nodes
    if burn_stock is not None or stock_offsets is not None:
        raise NotImplementedError("burn_stock / stock_offsets は CHEAT の TurnSearch のみ")
    from .search.fair import FairTurnSearch
    fs = FairTurnSearch(cfg.me, cfg.budget, cfg.n_det, cfg.seed, weights=cfg.weights, opp_policy=opp_pol,
                        value_fn=cfg.value_fn, lookahead=cfg.lookahead)
    out = fs.run(eng)
    return out, fs.nodes
