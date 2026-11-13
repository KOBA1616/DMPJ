"""登録簿の手順を探索の1手として使う口（S3、ロードマップ P3「探索にループ実行の手」、docs/registry-design.md §9）。

- 読むのは S0 の登録簿だけ（dmsim.base.registry.query(for_tuning=True)。holdout は出ない）。S4/S5 は import しない。
- 手（Macro）: 登録簿の項目の entry（入口局面 LoopSpec の minimal）と macro.steps（登録時に S4 が記録した、入口からの
  自分の決定の (種類, 選んだ意味キー) の列。ループの周回と勝ち手段を含む）。勝った局ごとに1本（最大 MAX_MACROS 本）で、1本ずつ手にする。
- 使い方: TurnSearch._search が、局面が入口の条件を満たし、今の決定が手順の最初の決定と同じ種類なら、
  複製した局面で手順を実際のエンジンで再生する（詳しくは replay）。選んだ意味キーが無ければ（引いた札が違う等）その手は不成立として捨てる。
  相手の決定は探索と同じ相手役に答えさせる。成立すれば再生後の局面を子として探索を続ける（通常の候補より先に試す）。
- 既定は無効。enable() / 環境変数 DMSIM_REGISTRY_MACRO=1 で有効。無効なら TurnSearch の挙動は従来と同じ。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from ..base import registry
from ..base.store import REPO
from ..engine.core import IllegalAnswer
from .route_goal import holds

_ENABLED: bool | None = None
_CACHE: dict = {}


@dataclass(frozen=True)
class Macro:
    id: str
    preds: tuple[dict, ...]
    steps: tuple[tuple[str, tuple[str, ...]], ...]
    win: str | None = None
    core: frozenset = frozenset()          # 中核の札 ID。これを含む意味キーの決定（錨）だけは同じ選択を要求する
    seed: int | None = None


def enable(on: bool = True) -> None:
    global _ENABLED
    _ENABLED = on


def enabled() -> bool:
    return _ENABLED if _ENABLED is not None else os.environ.get("DMSIM_REGISTRY_MACRO") == "1"


def load(path=registry.PATH) -> list[Macro]:
    """登録簿（調整用の照会）から、入口と手順の両方を持つ項目を手にする。"""
    key = str(path)
    if key not in _CACHE:
        out = []
        for r in registry.query(for_tuning=True, path=path):
            ms = (r.get("measured") or {}).get("macros") or []
            if not r.get("entry") or not ms:
                continue
            preds = tuple(json.loads((REPO / r["entry"]).read_text(encoding="utf-8"))["minimal"])
            core = frozenset(c["id"] for c in r["core"] if c.get("id"))
            for m in ms:
                out.append(Macro(r["id"], preds, tuple((k, tuple(ks)) for k, ks in m["steps"]), r.get("win"), core, m.get("seed")))
        _CACHE[key] = out
    return _CACHE[key]


def active() -> list[Macro]:
    return load() if enabled() else []


def record(m: Macro) -> dict:
    """採った線のループの記録（GameResult.loops に入る形）。登録時に S4 で検証済みのループなので verified。
    周回数は再生した手順の分だけで、無限かは主張しない（limit なし、stocked 1）。勝ち方は登録簿の win。"""
    return {"source": "registry", "id": m.id, "macro_seed": m.seed, "verified": True, "stocked": 1, "delta": {},
            "win_by": "opp_deck_out" if m.win == "opp_deck_out" else m.win}


def applies(m: Macro, eng, d: dict, me: int) -> bool:
    """入口の条件を満たすか。今の決定の種類は問わない（手順に無い決定は replay が探索の方策で答えて読み飛ばす）。
    1回の探索で手を試す局面は MAX_NODES 個まで（TurnSearch が数える）。"""
    return bool(m.steps) and all(holds(eng, p, me) for p in m.preds)


def _anchor(m: Macro, keys) -> bool:
    return any(c in k for k in keys for c in m.core)


MAX_NODES = 4            # 1回の TurnSearch.run で手を試す局面の数（探索の先頭から。毎局面で再生すると重い）
LOOSE = ("pay_mana",)     # 払い方は局面のマナで変わる: 同じキーが無ければ代わりの方策で払う
MAX_EXTRA = 20           # 手順に無い決定（順番の違う任意の確認など）を代わりの方策で答えてよい回数


def _pick(m: Macro, d: dict, ranked: list[list[int]]) -> list[int]:
    """探索の方策の候補（よい順）から、中核の札に触れない最初の選択（中核の札をチャージ・捨てない）。無ければ先頭。"""
    keys = [o["key"] for o in d["options"]]
    for ch in ranked:
        if not _anchor(m, [keys[i] for i in ch]):
            return ch
    return ranked[0]


def replay(m: Macro, eng, me: int, opp_policy, fallback):
    """eng（自分の決定待ち、変更しない）の複製で手順を再生する。最後まで続いて自分が勝てば再生後の局面、それ以外は None。
    fallback(e, d) は探索の方策の候補（よい順の選択のリスト）。手順の決定と種類が違う決定が来たら、
    そのうち中核の札に触れない最初の選択で答えて読み飛ばす（MAX_EXTRA 回まで）。
    種類が同じで選んだ意味キーが無ければ不成立（払い方 LOOSE だけは fallback で払う）。"""
    e = eng.clone()
    extra = 0
    turn = e.s.turn
    try:
        for kind, keys in m.steps:
            while True:
                d = e.advance()
                if d is None or e.s.result is not None:
                    return _won(e, me)
                if e.s.turn != turn or e.s.active != me:
                    return None           # 手順はこのターンの中だけ。ターンが終われば不成立
                if d["player"] != me:
                    e.answer(opp_policy(e, d))
                    continue
                if d["kind"] == kind:
                    break
                extra += 1
                if extra > MAX_EXTRA:
                    return None
                e.answer(_pick(m, d, fallback(e, d)))
            have = [o["key"] for o in d["options"]]
            pick, used = [], set()
            for k in keys:
                i = next((j for j, x in enumerate(have) if x == k and j not in used), None)
                if i is None:
                    break
                pick.append(i)
                used.add(i)
            if len(pick) != len(keys):
                if kind not in LOOSE and _anchor(m, keys):
                    return None           # 中核の札の選択ができない: 手順が続かない
                pick = _pick(m, d, fallback(e, d))     # 中核の札に関わらない選択（捨てる札・払い方など）は探索の方策に任せる
            e.answer(pick)
    except (IllegalAnswer, KeyError, IndexError, ValueError):
        return None
    e.advance()
    return _won(e, me)


def _won(e, me: int):
    """登録された手順は勝ち手段まで含む。再生して自分が勝っていなければ（周回が足りない・勝ちに届かない）不成立。"""
    r = e.s.result
    return e if r is not None and r.get("winner") == me else None
