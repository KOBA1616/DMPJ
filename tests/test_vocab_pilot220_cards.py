"""第220弾の登録形テスト（ラウンド256）: converted.yaml に登録された実カードで
hyper_subject_filter を検証する。

- dm24rp1-036 超化秘伝タノシキチシキ（アタック・チャンス: バウンス＋ドロー）
- dm24ex3-065 超化秘伝アビスアサルト（アタック・チャンス: ミル3＋墓地から出す）
- dm24ex3-062 シザー＝ゾー（墓地から出す＋出た時のパワー-4000）
"""
import os
from pathlib import Path

import pytest

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.scenario import build  # noqa: E402
from tests import _conv_cache  # noqa: E402

CONVERTED = Path(__file__).resolve().parent.parent / "data" / "cards" / "converted.yaml"
TABLES = load_tables()
IDS = ("dm24ex3-062", "dm24ex3-065", "dm24rp1-036", "dm24rp1-045",
       "dm24rp1-050", "dm24rp1-057")


@pytest.fixture(scope="module")
def converted():
    return {c["id"]: c for c in _conv_cache.all_cards(str(CONVERTED))}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_registered_parse(converted):
    for cid in IDS:
        assert cid in converted, cid
        parse_card(converted[cid], TABLES)


def setup(rules, p0, p1):
    return build(rules, {"p0": p0, "p1": p1, "filler": "T002",
                          "seed": 1, "deck_size": 20})


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)]


def _drive(e, handler, turns=5, limit=4000, stop_when=None):
    for _ in range(limit):
        if e.s.turn > turns:
            break
        d = e.advance()
        if d is None:
            break
        if stop_when is not None and stop_when(e, d):
            break
        if handler(e, d):
            continue
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def _hyper_attack_handler(chance_id=None):
    """ターン3に T569 をハイパー解放して攻撃する。宣言（chance_id）と
    yes_no はすべて受理する。"""
    state = {"released": False, "attacked": False}

    def h(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "yes_no":
            e.answer([0])
            return True
        if d["kind"].startswith("declare") and chance_id:
            idx = [i for i, k in enumerate(keys) if k.startswith(f"declare:{chance_id}")]
            if idx:
                e.answer(idx)
                return True
        if not state["released"] and d["kind"] == "main" and e.s.turn == 3 \
                and "hyper:T569" in keys:
            state["released"] = True
            e.answer([keys.index("hyper:T569")])
            return True
        if not state["attacked"] and d["kind"] == "attack" and e.s.turn == 3 \
                and "attack:T569:player" in keys:
            state["attacked"] = True
            e.answer([keys.index("attack:T569:player")])
            return True
        return False

    return h, state


def test_dm24rp1_036_attack_chance(rules):
    h, state = _hyper_attack_handler("dm24rp1-036")
    e = setup(rules, {"bz": ["T569", "T002"], "hand": ["dm24rp1-036"]},
              {"bz": ["T551"]})
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["released"] and state["attacked"]
    assert "dm24rp1-036" in _defns(e, "graveyard", 0)   # 無料で唱えた
    assert "T551" in _defns(e, "hand", 1)               # 相手クリーチャーが手札に戻った


def test_dm24ex3_065_attack_chance(rules):
    h, state = _hyper_attack_handler("dm24ex3-065")
    e = setup(rules, {"bz": ["T569", "T002"], "hand": ["dm24ex3-065"],
                      "graveyard": ["T551"]}, {})
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["released"] and state["attacked"]
    assert "dm24ex3-065" in _defns(e, "graveyard", 0)
    assert "T551" in _defns(e, "bz", 0)                 # 墓地のコスト4以下を出した


def test_dm24ex3_062_graveyard_put_and_cip(rules):
    h, state = _hyper_attack_handler()
    e = setup(rules, {"bz": ["T569", "T002"], "graveyard": ["dm24ex3-062"]},
              {"bz": ["T551"]})
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["released"] and state["attacked"]
    assert "dm24ex3-062" in _defns(e, "bz", 0)          # 墓地から出た
    # 出た時: 相手クリーチャー（T551 パワー1000）を -4000 → パワー0以下で破壊
    assert "T551" in _defns(e, "graveyard", 1)
