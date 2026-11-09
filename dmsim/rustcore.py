"""Rust 製エンジンコア（rust/dmcore）との橋渡し（試作）。

dmcore が入っていない環境でも、このモジュールの import は失敗しない（available() が False を返す）。
境界は「状態そのもの」: Rust 側の State を Python から clone / digest / to_json する。ルール・カード定義の読み込みと検証は
Python に残し、準備に必要な最小の情報（new_game_spec）だけを JSON で渡す。
"""
from __future__ import annotations

import json

try:
    import dmcore  # maturin develop / pip install rust/dmcore/target/wheels/*.whl
except ImportError:  # pragma: no cover - dmcore が無い環境
    dmcore = None


def available() -> bool:
    return dmcore is not None


def new_game_spec(rules, decks: list[list[str]], seed: int, first_player: int) -> dict:
    z = rules.zones
    return {"decks": decks, "zones": list(z),
            "public": {k: v["public"] for k, v in z.items()},
            "ordered": {k: v["ordered"] for k, v in z.items()},
            "shared": {k: v["shared"] for k, v in z.items()},
            "multi_civ": {k: len(c.civs) > 1 for k, c in rules.cards.items()},
            "steps": list(rules.steps), "seed": seed, "first_player": first_player}


def new_game(rules, decks: list[list[str]], seed: int, first_player: int = 0):
    """Engine.new_game と同じ準備を Rust で行い、State を返す。"""
    return dmcore.State.new_game(json.dumps(new_game_spec(rules, decks, seed, first_player)))
