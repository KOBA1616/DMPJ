"""1人回しの相手役（妨害モデル）。既定（None）は solitaire.charge_only_policy で従来どおり何も妨げない。

OppModel は設定で切り替える:
- shields   開始時のシールド枚数（既定 5。山札との間でカードを動かす。足りない分は山札から、余りは手札へ）
- bz        開始時に戦闘ゾーンへ置くカードID（相手の山札から1枚ずつ。ブロッカー等の盤面妨害）
- block     攻撃に対してブロッカーでブロックする
- strigger  シールドが割れた時に S・トリガーを使う
- play      "none" 何も出さない / "blockers" ブロッカーだけ出す / "all" 使えるカードを出す（除去・手札破壊は山札の中身次第）
マナチャージは常にする（ロック判定が相手の成長を見分けるため）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .engine import Engine
from .play import passive_policy


@dataclass(frozen=True)
class OppModel:
    name: str = "custom"
    shields: int = 5
    bz: tuple = ()
    block: bool = False
    strigger: bool = False
    play: str = "none"

    def setup(self, eng: Engine, p: int = 1) -> None:
        """開始局面の調整（ゲーム準備用の移動。イベントは起きない）。"""
        s = eng.s
        while len(s.zones["shield"][p]) > self.shields:
            eng._raw_move(s.zones["shield"][p][0], "hand")
        while len(s.zones["shield"][p]) < self.shields and s.zones["deck"][p]:
            eng._raw_move(s.zones["deck"][p][0], "shield")
        for defn in self.bz:
            cid = next((c for c in s.zones["deck"][p] if s.cards[c].defn == defn), None)
            if cid is None:
                raise ValueError(f"相手の山札に {defn} がない")
            eng._raw_move(cid, "bz")

    def policy(self, eng: Engine, d: dict) -> list[int]:
        keys = [o["key"] for o in d["options"]]
        k = d["kind"]
        if k == "charge":
            return [next((i for i, x in enumerate(keys) if x != "pass"), keys.index("pass"))]
        if k == "block" and self.block:
            return [next((i for i, x in enumerate(keys) if x != "no_block"), keys.index("no_block"))]
        if k == "declare_strigger" and self.strigger:
            return list(range(len(keys)))
        if k == "main" and self.play != "none":
            best = self._pick_play(eng, keys)
            if best is not None:
                return [best]
        return passive_policy(eng, d)

    def _pick_play(self, eng: Engine, keys: list[str]) -> int | None:
        best, score = None, None
        for i, x in enumerate(keys):
            if not x.startswith("play:"):
                continue
            c = eng.rules.cards[x[5:]]
            blk = "blocker" in c.keywords
            if self.play == "blockers" and not blk:
                continue
            sc = (blk, c.cost)
            if score is None or sc > score:
                best, score = i, sc
        return best


PRESETS: dict[str, OppModel | None] = {
    "none": None,
    "shields3": OppModel("shields3", shields=3),
    "blockers": OppModel("blockers", block=True, play="blockers"),
    "strigger": OppModel("strigger", strigger=True),
    "full": OppModel("full", block=True, strigger=True, play="all"),
}
