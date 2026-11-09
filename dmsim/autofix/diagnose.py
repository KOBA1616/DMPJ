"""段階指標から「どの段階で落ちるか」を決める（ルールベース。LLMは使わない）。

段階: cards（部品が見える所に揃う）→ board（最小盤面M＝墓地仕込み等が揃う）→ finish（揃ってキルまで届く）。
入力 m は {"kill": [キルターン|None], "board": [..], "cards": [..]}（同一シード順、未到達は None）。"""
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Diagnosis:
    stage: str          # ok / cards / board / finish
    cause: str          # 人が読む原因
    rates: dict         # kill / board / cards の到達率
    hints: tuple = ()   # 段階とは別の取りこぼし（例 prep_unused: 準備札を撃っていない）


def _rate(xs, max_turn):
    return sum(x is not None and x <= max_turn for x in xs) / len(xs) if xs else 0.0


def prep_unused(m: dict, floor: float = 0.5) -> bool:
    """準備札（m["prep"]: 各局で墓地に行った準備札の枚数）を使った局の割合が floor 未満。測っていない時は False。"""
    xs = m.get("prep")
    return bool(xs) and sum(1 for x in xs if x and x > 0) / len(xs) < floor


def diagnose(m: dict, max_turn: int, target: float = 0.5, floor: float = 0.5, ceiling: float | None = None) -> Diagnosis:
    r = {k: _rate(m.get(k, []), max_turn) for k in ("kill", "board", "cards")}
    hints = ("prep_unused",) if prep_unused(m, floor) else ()
    d = _stage(m, r, target, floor)
    if d.stage == "cards" and ceiling is not None and ceiling < floor:
        # 部品がそろう確率がデッキだけで上限 ceiling。実測がそれに近ければ AI でなくデッキの引き込みの問題（探索や評価式の改善では上がらない）
        d = Diagnosis("deck_limited", f"デッキの素引きで部品がそろう確率が{ceiling:.2f}（実測{r['cards']:.2f}。サーチ・ドローで補える分は実測に入る）。デッキ側の課題。探索側の診断は仕込み済み開始で行う", r)
    return replace(d, hints=hints) if hints else d


def _stage(m: dict, r: dict, target: float, floor: float) -> Diagnosis:
    if r["kill"] >= target:
        return Diagnosis("ok", "キル率が目標以上", r)
    if m.get("cards") and r["cards"] < floor:
        return Diagnosis("cards", "部品が揃わない（デッキの部品枚数・引き込み不足）", r)
    if m.get("board") and r["board"] < floor:
        return Diagnosis("board", "部品は揃うが最小盤面に届かない（墓地仕込み等の評価不足）", r)
    return Diagnosis("finish", "盤面は揃うがキルまで届かない（探索予算・評価不足）", r)
