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
    ids = [i for i, d in r.cards.items() if i.startswith("dm") and not rustcore._is_plain(d)][:1] * 40
    with pytest.raises(rustcore.dmcore.Unsupported):
        rustcore.RustSession.open(r, {"decks": [ids, ids], "seed": 1}, b)


@pytest.mark.parametrize("pol", ["first", "random:1", "random:2", "random:3"])
@pytest.mark.parametrize("seed", range(1, 21))
def test_full_game_matches(env, pol, seed):
    """召喚・攻撃・バトル・ブレイク・ダイレクトアタックを含む1局が、1手ごとに決定と digest まで一致して終局する。"""
    a, b = _pair(env, seed, seed % 2)
    res = lockstep(a, b, f"random:{seed}" if pol == "first" else pol)
    assert res["divergence"] is None and res["ok"] is True and res["steps"] >= 5


@pytest.fixture(scope="module")
def real_env():
    """確認前の変換結果（converted.yaml）も含めた全カード。テストの既定は除外しているが、エンジンの一致検査は広い札の集合で行う。"""
    import os
    old = os.environ.pop("DMSIM_SKIP_CONVERTED", None)
    try:
        r = load_rules()
    finally:
        if old is not None:
            os.environ["DMSIM_SKIP_CONVERTED"] = old
    return r, rustcore.rules_bundle(r)


def _portable(r, cost_max=6):
    return [i for i, d in r.cards.items() if i.startswith("dm") and rustcore._is_plain(d) and d.cost <= cost_max]


@pytest.mark.parametrize("seed", range(1, 41))
def test_real_cards_match(real_env, seed):
    """実カード（自分自身への許可・禁止・ブレイク数だけを持つクリーチャー: ブロッカー・スピードアタッカー・スレイヤー・
    W/T/Qブレイカー等）のランダムなデッキで、1局が決定と digest まで一致する。"""
    import random
    r, b = real_env
    pool = _portable(r)
    assert len(pool) > 200
    rnd = random.Random(seed)
    spec = {"kind": "new_game", "decks": [[rnd.choice(pool) for _ in range(40)] for _ in range(2)], "seed": seed,
            "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True


@pytest.mark.parametrize("seed", range(1, 31))
def test_trigger_cards_match(real_env, seed):
    """誘発（出た時・攻撃する時の、引く／任意で引く／自身のタップ・アンタップ）を持つ札を多く入れたデッキで、
    待機・解決順・効果インタプリタ・yes/no の決定まで含めて1局が一致する。"""
    import random
    r, b = real_env
    pool = _portable(r)
    trig = [i for i in pool if any(a["kind"] == "trigger" for a in r.cards[i].abilities)]
    assert len(trig) >= 40
    rnd = random.Random(seed)

    def deck():
        return [rnd.choice(trig) if rnd.random() < 0.5 else rnd.choice(pool) for _ in range(40)]
    spec = {"kind": "new_game", "decks": [deck(), deck()], "seed": seed, "first_player": seed % 2}
    res = lockstep(Session.open(r, spec), rustcore.RustSession.open(r, spec, b), f"random:{seed}")
    assert res["divergence"] is None and res["ok"] is True
