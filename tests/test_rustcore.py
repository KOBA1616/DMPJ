"""Rust 試作コア（rust/dmcore）が Python 版と同じ初期状態・digest・乱数を作ることの回帰基準。
dmcore が入っていない環境では飛ばす（ビルド: cd rust/dmcore && maturin build --release && pip install target/wheels/*.whl）。"""
import json

import pytest

from dmsim import rustcore
from dmsim.defs import load_rules
from dmsim.engine.core import Engine

pytestmark = pytest.mark.skipif(not rustcore.available(), reason="dmcore 未ビルド")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _deck(rules, n=40):
    ids = sorted(i for i in rules.cards if i.startswith("dm"))
    return [ids[i % len(ids)] for i in range(n)]


@pytest.mark.parametrize("seed", [1, 2, 3, 12345, 2**63 + 5])
@pytest.mark.parametrize("first_player", [0, 1])
def test_new_game_matches_python(rules, seed, first_player):
    decks = [_deck(rules), ["T001"] * 40]
    py = Engine.new_game(rules, decks, seed, first_player).s
    rs = rustcore.new_game(rules, decks, seed, first_player)
    assert rs.to_json() == py.to_json()    # バイト列まで一致（sort_keys・区切り・非 ASCII）
    assert rs.digest() == py.digest()


def test_json_roundtrip_and_clone(rules):
    py = Engine.new_game(rules, [_deck(rules), ["T001"] * 40], 7, 0).s
    rs = rustcore.dmcore.State.from_json(py.to_json())
    assert rs.to_json() == py.to_json()
    c = rs.clone()
    c.rng_next()
    assert rs.digest() == py.digest() and c.digest() != py.digest()   # clone は独立


def test_rng_matches_python(rules):
    from dmsim.state import rng_next
    py = Engine.new_game(rules, [_deck(rules), ["T001"] * 40], 99, 0).s
    rs = rustcore.dmcore.State.from_json(py.to_json())
    for _ in range(100):
        assert rs.rng_next() == rng_next(py)
    assert json.loads(rs.to_json())["rng"] == py.rng
