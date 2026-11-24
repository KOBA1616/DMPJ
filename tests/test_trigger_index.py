"""Phase 9: 誘発の発生源索引（可能性登録＋付与有効フラグ）の検証。

- 索引で読み飛ばした発生源に本当にその出来事の誘発が無いことは、check モードの
  自己照合（_collect_triggers 内の assert）が対戦を通じて担保する。
- あわせて、盤面キャッシュが Rules 共有の _xcache にあるため、別デッキの対戦が
  同じプロセスで続いてもキャッシュが衝突しないこと（Phase 9 で発見した
  Phase 8 の潜在バグの回帰防止）を確認する。
"""
import os
import random

import pytest


@pytest.fixture(scope="module", autouse=True)
def _full_rules():
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    yield
    if old is not None:
        os.environ["DMSIM_SKIP_CONVERTED"] = old


def _play(deck_a, deck_b, seed, check=True):
    from dmsim.engine.core import Engine
    from dmsim.engine.play import run, random_policy
    e = Engine.new_game(_RULES, [deck_a, deck_b], seed, 0, check=check)
    return run(e, [random_policy(random.Random(seed))] * 2)


@pytest.fixture(scope="module")
def decks():
    from dmsim.cards.defs import load_rules
    from tools.bench_2p import load_deck
    global _RULES
    _RULES = load_rules()
    return {n: load_deck(f"data/decks/{n}.yaml")
            for n in ("saga", "akashic", "tenmon")}


def test_index_check_mode_games(decks):
    # check モードの自己照合つきで複数デッキを回す（assert が発火したら失敗）
    for name in ("saga", "akashic", "tenmon"):
        res = _play(decks[name], decks[name], 100)
        assert res is not None and "winner" in res


def test_board_cache_no_cross_game_collision(decks):
    # 別デッキの対戦を同じプロセスで続ける。盤面キャッシュ（gainable 等）が
    # 対戦をまたいで衝突すると、check モードの照合 assert が発火する
    _play(decks["saga"], decks["saga"], 100)
    res = _play(decks["akashic"], decks["akashic"], 100)
    assert res is not None and "winner" in res
    res = _play(decks["saga"], decks["tenmon"], 200)
    assert res is not None and "winner" in res


def test_pot_kinds_and_grant_kinds(decks):
    from dmsim.engine.core import Engine
    e = Engine.new_game(_RULES, [decks["saga"], decks["saga"]], 1, 0)
    # 定義の可能性登録: 誘発を持つ定義は最低1種別、持たない定義は空
    some = [d for d in decks["saga"] if e._pot_kinds(d)]
    assert some
    # 付与有効フラグ: 初期盤面では add_from が無ければ frozenset が返る
    kinds = e._active_grant_kinds()
    assert kinds is None or isinstance(kinds, frozenset)
