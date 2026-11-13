"""Rust 側の Card / GameState のフィールドが Python 版の dataclass と一致していること（ビルド不要の静的検査）。
Python 側にフィールドが増えたのに Rust 側が追従していないと、lockstep と digest が全局で食い違う。"""
import dataclasses
import re
from pathlib import Path

from dmsim.engine.state import Card, GameState

SRC = Path(__file__).resolve().parents[1] / "rust" / "dmcore" / "src" / "state.rs"


def _fields(struct: str) -> list[str]:
    body = re.search(r"pub struct %s \{(.*?)\n\}" % struct, SRC.read_text(encoding="utf-8"), re.S).group(1)
    return [m.group(1).removeprefix("r#") for m in re.finditer(r"pub ([\w#]+):", body)]


def test_card_fields_match():
    assert sorted(_fields("Card")) == sorted(f.name for f in dataclasses.fields(Card))


def test_state_fields_match():
    assert sorted(_fields("GameState")) == sorted(f.name for f in dataclasses.fields(GameState))


def test_rust_fields_are_alphabetical():
    for s in ("Card", "GameState"):
        f = [x for x in _fields(s)]
        assert f == sorted(f), s   # JSON の出力順 = sort_keys と一致させるため
