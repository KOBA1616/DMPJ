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
    bad = "dm04-008"   # 次の自分のターンのはじめまで続く modify（Rust は解決時に Unsupported。他は扱える語彙だけ）
    assert not rustcore._is_plain(r.cards[bad])
    deck2 = [bad] * 16 + deck[16:]
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
    assert not isinstance(rustcore.maybe_rust(Engine.new_game(r, [["dm05-013"] * 40, opp], 1, 0)), rustcore.RustEngine)
    monkeypatch.setenv("DMSIM_RUST", "0")
    assert not isinstance(rustcore.maybe_rust(Engine.new_game(r, [deck, opp], 1, 0)), rustcore.RustEngine)


@pytest.mark.parametrize("seed", range(4))
def test_thin_readers_match_view(env, seed, monkeypatch):
    """探索が読む欄の薄い読み取り口（zone_ids / zone_names / card_sig / tkey_extra / waiting_fast / eval_feats / skel_raw）が、
    作り直した Python の状態から計算した値と一致する。決定化の注入（s の差し替え）の後も古い写しを返さない。"""
    from dmsim.engine.core import Engine
    from dmsim.engine import loop
    r, deck, opp = env
    monkeypatch.setenv("DMSIM_RUST", "1")
    e = rustcore.maybe_rust(Engine.new_game(r, [deck, opp], seed, seed % 2))
    assert isinstance(e, rustcore.RustEngine)
    rnd = random.Random(seed)
    n = 0
    while (d := e.advance()) is not None and n < 300:
        s = e._view().s
        for p in (0, 1):
            for z in ("hand", "bz", "mana", "graveyard", "shield"):
                assert e.zone_ids(z, p) == s.zones[z][p]
                assert e.zone_names(z, p) == [s.cards[c].defn for c in s.zones[z][p]]
        for c in s.zones["bz"][0] + s.zones["bz"][1]:
            assert e.card_sig(c) == (s.cards[c].defn, tuple(sorted(s.cards[u].defn for u in s.cards[c].under)))
        assert e.waiting_fast()[0] == s.waiting
        e2 = Engine(r, s.clone())
        hk = set(e.zone_names("hand", 0)[:2])
        for per in ("in_turn", "cross_turn"):
            assert loop.abstract(e, per) == loop.abstract(e2, per)
            assert loop.abstract(e, per, hk) == loop.abstract(e2, per, hk)
        assert e.eval_feats(0)[1] is not None
        mn, mx, k = d["min"], d["max"], len(d["options"])
        e.answer(list(range(mn)) if mn == mx else [rnd.randrange(k)] if mn <= 1 <= mx else list(range(mn)))
        n += 1
        if n == 40:                                   # 注入の後に写しが捨てられること
            e.s = e._view().s.clone()


def test_engine_stamp_is_current():
    """Rust で一致を確かめた Python エンジンの版の記録（rust/dmcore/verified_engine.txt）が今のエンジンと同じ。
    落ちたら: dmcore を作り直し、tests/test_rust_*.py を通してから python tools/rust_stamp.py で記録し直す。
    記録が古い間は、対局・探索は Rust を使わない（rustcore.enabled が偽）。"""
    from pathlib import Path
    assert Path(rustcore.STAMP).read_text().split()[0] == rustcore.engine_hash()
