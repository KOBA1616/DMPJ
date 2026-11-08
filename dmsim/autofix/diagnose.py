"""段階指標から「どの段階で落ちるか」を決める（ルールベース。LLMは使わない）。

段階: cards（部品が見える所に揃う）→ board（最小盤面M＝墓地仕込み等が揃う）→ finish（揃ってキルまで届く）。
入力 m は {"kill": [キルターン|None], "board": [..], "cards": [..]}（同一シード順、未到達は None）。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Diagnosis:
    stage: str          # ok / cards / board / finish
    cause: str          # 人が読む原因
    rates: dict         # kill / board / cards の到達率


def _rate(xs, max_turn):
    return sum(x is not None and x <= max_turn for x in xs) / len(xs) if xs else 0.0


def diagnose(m: dict, max_turn: int, target: float = 0.5, floor: float = 0.5) -> Diagnosis:
    r = {k: _rate(m.get(k, []), max_turn) for k in ("kill", "board", "cards")}
    if r["kill"] >= target:
        return Diagnosis("ok", "キル率が目標以上", r)
    if m.get("cards") and r["cards"] < floor:
        return Diagnosis("cards", "部品が揃わない（デッキの部品枚数・引き込み不足）", r)
    if m.get("board") and r["board"] < floor:
        return Diagnosis("board", "部品は揃うが最小盤面に届かない（墓地仕込み等の評価不足）", r)
    return Diagnosis("finish", "盤面は揃うがキルまで届かない（探索予算・評価不足）", r)
