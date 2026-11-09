"""Rust エンジン（段階1）が Python 版と決定・digest を 1 手ずつ一致させることの基準（lockstep）。
段階1の範囲: ターン進行・ドロー・マナチャージ・パス・デッキ切れ。プレイ（play）は未移植 → Unsupported が構造化されて返ること。"""
import pytest

from dmsim import rustcore
from dmsim.defs import load_rules
from dmsim.engine_api import Session, lockstep

pytestmark = pytest.mark.skipif(not rustcore.available(), reason="dmcore 未ビルド")


@pytest.fixture(scope="module")
def env():
    r = load_rules()
    plain = [i for i, d in r.cards.items() if rustcore._is_plain(d)]
    return r, rustcore.rules_bundle(r), [plain[i % len(plain)] for i in range(40)]


def _pair(env, seed, fp):
    r, b, deck = env
    spec = {"kind": "new_game", "decks": [deck, deck], "seed": seed, "first_player": fp}
    return Session.open(r, spec), rustcore.RustSession.open(r, spec, b)


@pytest.mark.parametrize("seed", [1, 2, 3, 99])
@pytest.mark.parametrize("fp", [0, 1])
def test_passive_game_matches_to_deckout(env, seed, fp):
    a, b = _pair(env, seed, fp)
    res = lockstep(a, b, "passive")
    assert res["ok"] is True and res["steps"] > 20


def test_non_plain_is_structured_unsupported(env):
    """未移植の語彙は Unsupported として構造化して返る（ここでは、出た時に封印を解放するコマンド種族）"""
    r, b, _ = env
    cmd = [i for i, d in r.cards.items() if d.types == ["creature"] and d.power > 0 and any("コマンド" in x for x in d.races)
           and not rustcore._is_plain(d)][:1]
    assert cmd
    with pytest.raises(rustcore.dmcore.Unsupported):
        rustcore.RustSession.open(r, {"decks": [cmd * 40, cmd * 40], "seed": 1}, b)


def test_non_plain_card_rejected_at_open(env):
    r, b, _ = env
    ids = [i for i in r.cards if i.startswith("dm")][:1] * 40
    with pytest.raises(rustcore.dmcore.Unsupported):
        rustcore.RustSession.open(r, {"decks": [ids, ids], "seed": 1}, b)


@pytest.mark.parametrize("pol", ["first", "random:1", "random:2", "random:3"])
@pytest.mark.parametrize("seed", range(1, 21))
def test_full_game_matches(env, pol, seed):
    """召喚・攻撃・バトル・ブレイク・ダイレクトアタックを含む1局が、1手ごとに決定と digest まで一致して終局する。"""
    a, b = _pair(env, seed, seed % 2)
    res = lockstep(a, b, f"random:{seed}" if pol == "first" else pol)
    assert res["divergence"] is None and res["ok"] is True and res["steps"] >= 5
