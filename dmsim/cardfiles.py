"""カード定義ファイルの場所。data/cards/*.yaml に加え、弾ごとに分けた data/cards/<種別>/<弾>.yaml も読む。"""
from __future__ import annotations

from pathlib import Path

from .defs import DATA


def card_files(root: Path | None = None) -> list[Path]:
    root = root or DATA / "cards"
    return sorted(root.glob("*.yaml")) + sorted(root.glob("*/*.yaml"))
