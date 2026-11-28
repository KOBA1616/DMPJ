"""デッキ読み込みの窓口（S1）。デッキ YAML を読むのはここの load_deck だけ（直に yaml を読まない: tests/test_loading_window.py）。

  load_deck("data/decks/saga.yaml") -> ["id", ...]（40枚の並び）
形式は {deck: [id, ...]} か {cards: {id: 枚数}}。相対パスはリポジトリ直下から解く（実行場所に依らない）。
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ..base.store import REPO


def load_deck_doc(path: str | Path) -> dict:
    """デッキ YAML の中身そのまま（deck 以外の項目も要る時用）。"""
    p = Path(path)
    return yaml.safe_load((p if p.is_absolute() else REPO / p).read_text(encoding="utf-8")) or {}


def load_deck(path: str | Path) -> list[str]:
    y = load_deck_doc(path)
    if "deck" in y:
        return list(y["deck"])
    return [cid for cid, n in y["cards"].items() for _ in range(n)]
