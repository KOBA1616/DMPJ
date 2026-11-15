"""段階4: 対局・探索への接続（RustEngine）。DMSIM_RUST=1 の時、全札が Rust で動く局は Rust で進め、結果は Python と完全に一致する。
未対応の語彙に当たったら、起点から決定を Python で再生して続ける（自動の切り替え）。"""
import random

import pytest

from dmsim.engine import rustcore

pytestmark = pytest.mark.skipif(not rustcore.available(), reason="dmcore が無い")


@pytest.fixture(scope="module")
def env():
    import os
    from dmsim.cards.defs import load_rules
    from dmsim.eval.measure import load_deck
    from dmsim.search.opponent import resistance
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)   # 確認前の変換結果も含めた全カード（エンジンの一致検査と同じ）
    try:
        r = load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old
    return r, load_deck("data/decks/saga_entry.yaml"), list(resistance(0)[1])


def _play(e, seed):
    rnd = random.Random(seed)
    while (d := e.advance()) is not None:
        mn, mx, k = d["min"], d["max"], len(d["options"])
        e.answer(list(range(mn)) if mn == mx else [rnd.randrange(k)] if mn <= 1 <= mx else list(range(mn)))
    return e.log, e.s.result, e.s.digest()


@pytest.mark.parametrize("seed", range(6))
def test_random_games_match(env, seed):
    from dmsim.engine.core import Engine
    r, deck, opp = env
    assert rustcore.supports(r, Engine.new_game(r, [deck, opp], seed, seed % 2).s)
    a = _play(Engine.new_game(r, [deck, opp], seed, seed % 2), seed)
    b = _play(rustcore.RustEngine(r, Engine.new_game(r, [deck, opp], seed, seed % 2).s, []), seed)
    assert a == b


def test_clone_and_inject(env):
    """clone は独立した枝、s への代入（決定化の注入）は新しい起点になる。"""
    from dmsim.engine.core import Engine
    r, deck, opp = env
    e = rustcore.RustEngine(r, Engine.new_game(r, [deck, opp], 3, 1).s, [])
    p = Engine.new_game(r, [deck, opp], 3, 1)
    for _ in range(5):
        e.advance(); p.advance()
        e.answer([0]); p.answer([0])
    c = e.clone()
    c.advance(); c.answer([0]); c.advance()
    e.advance()
    p.advance()
    assert e.s.digest() == p.s.digest()
    st = p.s.clone()
    e.s = st
    assert e.s.digest() == st.digest()


def test_fallback_to_python(env, monkeypatch):
    """Rust が扱えない札を含む局（扱えると偽って開く）は、当たった所から Python で続き、結果は Python と同じ。"""
    from dmsim.engine.core import Engine
    r, deck, opp = env
    bad = "dm26rp2-t005"   # モード選択（modal）の呪文（未移植。他は扱える語彙だけ）
    assert not rustcore._is_plain(r.cards[bad])
    deck2 = [bad] * 10 + deck[10:]
    orig = rustcore._is_plain
    monkeypatch.setattr(rustcore, "_is_plain", lambda d: orig(d) or d.id == bad)
    monkeypatch.setattr(rustcore, "_BUNDLES", {})
    hit = 0
    for seed in range(8):
        e = rustcore.RustEngine(r, Engine.new_game(r, [deck2, deck2], seed, seed % 2).s, [])
        b = _play(e, seed)
        a = _play(Engine.new_game(r, [deck2, deck2], seed, seed % 2), seed)
        assert a == b
        hit += e._fb is not None
    assert hit > 0


def test_maybe_rust_switch(env, monkeypatch):
    from dmsim.engine.core import Engine
    r, deck, opp = env
    monkeypatch.setenv("DMSIM_RUST", "1")
    assert isinstance(rustcore.maybe_rust(Engine.new_game(r, [deck, opp], 1, 0)), rustcore.RustEngine)
    assert not isinstance(rustcore.maybe_rust(Engine.new_game(r, [["dmd24-024"] * 40, opp], 1, 0)), rustcore.RustEngine)
    monkeypatch.setenv("DMSIM_RUST", "0")
    assert not isinstance(rustcore.maybe_rust(Engine.new_game(r, [deck, opp], 1, 0)), rustcore.RustEngine)
