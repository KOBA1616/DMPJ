"""評価ハーネスと LogWriter(explog)の接続。1局の終了時エンジンの決定ログ(eng.log)を、開始局面から決定的に再生して
1手ごとの記録（状態ダイジェスト・合法手・選択）にする。探索中のクローンには触れない（runner は終了時に sink(eng) を呼ぶだけ）。

保存先: <out_dir>/<experiment_id>/<セル名>.jsonl（既定 out_dir = logs/explog。.gitignore 済みでローカルのみ）。
量の上限（ExpLogSpec）: セルごとの記録局数・1局の手数・1ファイルのバイト数。超えたら打ち切り、index.jsonl に truncated を残す。"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from ..engine.core import Engine
from .explog import LogWriter
from ..engine_view import digest_of, turn_of


@dataclass
class ExpLogSpec:
    out_dir: str = "logs/explog"
    max_games_per_cell: int = 20      # セルごとに記録する局数（先頭から）
    max_steps_per_game: int = 400     # 1局あたりの手数上限
    max_bytes_per_file: int = 8_000_000
    policy_id: str = "turn_search"
    vocab_ver: str = "unknown"
    engine_ver: str | None = None


def _safe(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z._=+-]", "_", name)


def replay_steps(rules, eng_final: Engine, deck, opp_deck, seed, first_player, start=None, opp=None):
    """eng_final.log を開始局面から再生し、(手ごとの dict 列, 全手を再生できたか) を返す。"""
    if start is not None:
        eng = start.clone()
    else:
        eng = Engine.new_game(rules, [deck, opp_deck], seed, first_player)
    if opp is not None:
        opp.setup(eng)
    steps = []
    for ent in eng_final.log:
        d = eng.advance()
        if d is None:
            break
        steps.append({"state": digest_of(eng), "legal": [o["key"] for o in d["options"]], "chosen": list(ent["keys"]),
                      "p": d["player"], "kind": d["kind"], "turn": turn_of(eng)})
        eng.answer(ent["choice"])
    return steps, len(steps) == len(eng_final.log)


class CellLogger:
    """1セル分の書き込み。games ごとに add_game を呼ぶ。"""

    def __init__(self, spec: ExpLogSpec, exp_cfg: dict, cell: str, opp_id: str):
        self.spec, self.cell, self.opp_id = spec, cell, opp_id
        self.games = 0
        self.truncated = False
        self.path = Path(spec.out_dir)
        self.w = LogWriter(self.path / _expid(exp_cfg) / f"{_safe(cell)}.jsonl", {**exp_cfg, "cell": cell},
                           spec.engine_ver, spec.vocab_ver)

    def add_game(self, rules, eng, res, deck, opp_deck, first_player, start=None, opp=None) -> None:
        if self.games >= self.spec.max_games_per_cell or self.w.path.stat().st_size > self.spec.max_bytes_per_file:
            self.truncated = True
            return
        self.w._f.flush()
        steps, ok = replay_steps(rules, eng, deck, opp_deck, res.seed, first_player, start, opp)
        if len(steps) > self.spec.max_steps_per_game:
            steps, self.truncated = steps[:self.spec.max_steps_per_game], True
        last = len(steps) - 1
        for i, st in enumerate(steps):
            result = {"kill_turn": res.kill_turn, "kind": res.kind, "replay_ok": ok} if i == last else None
            self.w.step(state=st["state"], legal=st["legal"], chosen=st["chosen"], policy_id=self.spec.policy_id,
                        opp_id=self.opp_id, seed=res.seed, turn=st["turn"], result=result, p=st["p"], kind=st["kind"],
                        first_player=first_player)
        self.games += 1

    def close(self) -> dict:
        self.w.close()
        return {"path": str(self.w.path), "games": self.games, "truncated": self.truncated}


def _expid(cfg: dict) -> str:
    from .explog import experiment_id
    return experiment_id(cfg)
