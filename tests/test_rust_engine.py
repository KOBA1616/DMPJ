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


def test_unported_attack_is_structured_unsupported(env):
    a, b = _pair(env, 1, 0)
    res = lockstep(a, b, "first")
    assert res["ok"] is None and "attack" in res["unsupported"]


def test_non_plain_card_rejected_at_open(env):
    r, b, _ = env
    ids = [i for i in r.cards if i.startswith("dm")][:1] * 40
    with pytest.raises(rustcore.dmcore.Unsupported):
        rustcore.RustSession.open(r, {"decks": [ids, ids], "seed": 1}, b)


@pytest.mark.parametrize("pol", ["first", "random:1", "random:2", "random:3"])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_play_matches_until_attack(env, pol, seed):
    """召喚（コスト支払い→保留→バトルゾーン）まで 1 手ごとに digest が一致。攻撃できるクリーチャーが出たら 2-b（戦闘）の未移植として止まる。"""
    a, b = _pair(env, seed, seed % 2)
    res = lockstep(a, b, pol)
    assert res["divergence"] is None and res["ok"] in (True, None)
    assert res["ok"] is True or "attack" in res["unsupported"]
    assert res["steps"] >= 5
