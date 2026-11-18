"""第221弾の登録形テスト（ラウンド257）: converted.yaml に登録された実カードで
bio_t（バイオ・T）を検証する。

- dm23-011 アクア・スイッチ（手札比例パワー）
- dm23-039 風雲闘機マスターフィンガー（パワー＋終了時アンタップ）
- dm23-040 封魔グレミー（両バウンス）
- dm23-046 デスハンター・ドラグーン（スレイヤー付与）
- dm23-049 お祭番長ゴリヤンキー（パワーアタッカー+4000付与）
- dm23-054 霊騎ゼブルス・アームズ（パワー固定）

攻撃役は各レースのバニラ実カード。防御側 T005（3000）はターン2に
プレイヤーへ攻撃させてタップしておき、ターン3に攻撃役がタップ状態の
T005へ攻撃する（505.2 の既定。マッハ不要）。
"""
import os
from pathlib import Path

import pytest

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from conftest import setup  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from tests import _conv_cache  # noqa: E402

CONVERTED = Path(__file__).resolve().parent.parent / "data" / "cards" / "converted.yaml"
TABLES = load_tables()
IDS = ("dm23-011", "dm23-039", "dm23-040", "dm23-046", "dm23-049", "dm23-054")


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


def _defns(e, zone, p):
    return [e.s.cards[c].defn for c in e.zlist(zone, p)
            if e.s.cards[c].controller == p] if zone == "bz" else \
           [e.s.cards[c].defn for c in e.zlist(zone, p)]


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


def _make_handler(logs, attacker, defender="T005", hand_log=None):
    """ターン2に defender がプレイヤーへ攻撃してタップし、ターン3に
    attacker が defender へ攻撃する。yes_no はすべて受理する。"""
    state = {"defender_attacked": False, "attacked": False}

    def h(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "yes_no":
            logs.append((e.s.turn, d.get("player")))
            if hand_log is not None:
                hand_log.append(len(e.zlist("hand", d.get("player"))))
            e.answer([0])
            return True
        if not state["defender_attacked"] and d["kind"] == "attack" \
                and e.s.turn == 2 and d.get("player") == 1 \
                and f"attack:{defender}:player" in keys:
            state["defender_attacked"] = True
            e.answer([keys.index(f"attack:{defender}:player")])
            return True
        if not state["attacked"] and d["kind"] == "attack" \
                and e.s.turn == 3 and d.get("player") == 0 \
                and f"attack:{attacker}:{defender}" in keys:
            state["attacked"] = True
            e.answer([keys.index(f"attack:{attacker}:{defender}")])
            return True
        return False

    return h, state


def _battle(rules, card, attacker, defender="T005"):
    return setup(rules, {"bz": [attacker], "hand": [card]},
                 {"bz": [defender]}, filler="T002")


def test_dm23_011_power_per_hand(rules):
    # may 時の手札は4枚（本札＋ターン3のドロー1＋ターン2に T005 の
    # W・ブレイカーで割られたシールド2）。捨てて残り3枚→+3000。
    # アクア・シューター 2000+3000=5000>3000 で勝ち残る。
    hand_log = []
    logs = []
    h, state = _make_handler(logs, "dm18-102", hand_log=hand_log)
    e = _battle(rules, "dm23-011", "dm18-102")
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["defender_attacked"] and state["attacked"]
    assert logs == [(3, 0)]
    assert hand_log == [4]
    assert "dm23-011" in _defns(e, "graveyard", 0)   # 捨てた
    assert "dm18-102" in _defns(e, "bz", 0)          # 勝ち残り
    assert "T005" in _defns(e, "graveyard", 1)       # 守備側は破壊


def test_dm23_039_power_and_untap(rules):
    logs = []
    h, state = _make_handler(logs, "dm23-041")
    e = _battle(rules, "dm23-039", "dm23-041")
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["defender_attacked"] and state["attacked"]
    assert logs == [(3, 0)]
    assert "dm23-039" in _defns(e, "graveyard", 0)
    assert "dm23-041" in _defns(e, "bz", 0)          # 3000+1500=4500>3000
    assert "T005" in _defns(e, "graveyard", 1)
    # 遅延アンタップはターン3の終わりに発火した（前ターンの履歴に残る）。
    assert e.s.prev_counters.get("hist:untap:0") == 1
    assert e.s.turn_counters.get("hist:untap:0") is None


def test_dm23_040_bounce_both(rules):
    logs = []
    h, state = _make_handler(logs, "dm25-046")
    e = _battle(rules, "dm23-040", "dm25-046")
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["defender_attacked"] and state["attacked"]
    assert logs == [(3, 0)]
    assert "dm23-040" in _defns(e, "graveyard", 0)
    assert "dm25-046" in _defns(e, "hand", 0)        # 攻撃側も手札へ戻る
    assert "T005" in _defns(e, "hand", 1)            # 防御側も手札へ戻る


def test_dm23_046_grant_slayer(rules):
    # 守備側は T571（4000）。チルドホーン 3000<4000 でバトルに負けるが、
    # スレイヤーで T571 も破壊される。
    logs = []
    h, state = _make_handler(logs, "dm19-089", defender="T571")
    e = _battle(rules, "dm23-046", "dm19-089", defender="T571")
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["defender_attacked"] and state["attacked"]
    assert logs == [(3, 0)]
    assert "dm23-046" in _defns(e, "graveyard", 0)
    assert "dm19-089" in _defns(e, "graveyard", 0)   # 3000<4000 でバトルに負ける
    assert "T571" in _defns(e, "graveyard", 1)       # が、スレイヤーで道連れ


def test_dm23_049_gain_power_attacker(rules):
    logs = []
    h, state = _make_handler(logs, "dm32-106")
    e = _battle(rules, "dm23-049", "dm32-106")
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["defender_attacked"] and state["attacked"]
    assert logs == [(3, 0)]
    assert "dm23-049" in _defns(e, "graveyard", 0)
    assert "dm32-106" in _defns(e, "bz", 0)          # 攻撃中 2000+4000=6000
    assert "T005" in _defns(e, "graveyard", 1)


def test_dm23_054_flat_power(rules):
    logs = []
    h, state = _make_handler(logs, "dm19-109")
    e = _battle(rules, "dm23-054", "dm19-109")
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert state["defender_attacked"] and state["attacked"]
    assert logs == [(3, 0)]
    assert "dm23-054" in _defns(e, "graveyard", 0)
    assert "dm19-109" in _defns(e, "bz", 0)          # 2000+2000=4000>3000
    assert "T005" in _defns(e, "graveyard", 1)
