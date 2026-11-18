"""第219弾の登録形テスト（ラウンド255）: converted.yaml に登録された実カードで
draw_replacement_extra_card の2形と付随条項を検証する。

- dm07-s02 アストラル・メデューサ（ターン頭形・進化）
- dm12-029 ウイングアイ・モス（条件つきターン頭形）
- dm14-017 アクア・オフィサー（2枚まで＋ターン終わりタップ）
- dm16-s02 ルナ・コスモビュー（1枚目形。G・ゼロは parse で確認）
- dm19-018 封魔バーガンティス（1枚目形＋ブロックされなかった攻撃で全捨て）
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
IDS = ("dm07-s02", "dm12-029", "dm14-017", "dm16-s02", "dm19-018")


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


def setup(rules, p0, p1, filler="T002", seed=1, deck_size=20):
    return build(rules, {"p0": p0, "p1": p1, "filler": filler,
                          "seed": seed, "deck_size": deck_size})


def _deck(e, p):
    return len(e.zlist("deck", p))


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
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))


def test_dm07_turn_draw(rules):
    logs = []

    def h(e, d):
        if d["kind"] == "yes_no":
            logs.append((e.s.turn, d.get("player")))
            e.answer([0])
            return True
        return False

    e = setup(rules, {"bz": ["dm07-s02"]}, {})
    start = _deck(e, 0)
    _drive(e, h, turns=3)
    assert logs == [(3, 0)]
    assert start - _deck(e, 0) == 2   # ターンドロー + 余分1枚


def test_dm12_conditional(rules):
    logs = []

    def h(e, d):
        if d["kind"] == "yes_no":
            logs.append((e.s.turn, d.get("player")))
            e.answer([1])
            return True
        return False

    e = setup(rules, {"bz": ["dm12-029"]}, {"bz": ["T002"]})   # 3000 > 1000
    _drive(e, h, turns=3)
    assert logs == [(3, 0)]

    logs.clear()
    e = setup(rules, {"bz": ["dm12-029"]}, {"bz": ["T201"]})   # 3000 < 9000
    _drive(e, h, turns=3)
    assert logs == []


def test_dm14_up_to_two_and_tap(rules):
    def h(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_one" and keys and keys[0].startswith("num:"):
            e.answer([2])
            return True
        return False

    e = setup(rules, {"bz": ["dm14-017", "T002", "T002"]}, {})
    start = _deck(e, 0)
    _drive(e, h, turns=5, stop_when=lambda e, d: e.s.turn >= 4)
    assert start - _deck(e, 0) == 3
    mine = [c for c in e.zlist("bz", 0) if e.s.cards[c].controller == 0]
    assert sum(1 for c in mine if e.s.cards[c].tapped) == 2


def test_dm16_first_draw(rules):
    logs = []

    def h(e, d):
        if d["kind"] == "yes_no":
            logs.append((e.s.turn, d.get("player")))
            e.answer([0])
            return True
        return False

    e = setup(rules, {"bz": ["dm16-s02"]}, {})
    start = _deck(e, 0)
    _drive(e, h, turns=3)
    assert logs == [(3, 0)]
    assert start - _deck(e, 0) == 2


def test_dm19_first_draw_and_unblocked_discard(rules):
    # 1枚目形
    logs = []

    def h(e, d):
        if d["kind"] == "yes_no":
            logs.append((e.s.turn, d.get("player")))
            e.answer([1])   # ドロー分は断る（手札枚数を読みやすくする）
            return True
        return False

    e = setup(rules, {"bz": ["dm19-018"]}, {})
    _drive(e, h, turns=3)
    assert logs == [(3, 0)]

    # ブロックされなかった攻撃で手札をすべて捨てる
    # （バーガンティスはブロッカーではないので攻撃はそのまま通り、シールドが
    # 1枚割れて手札に加わった後、attack_end 誘発で手札をすべて捨てる）
    attacked = []
    hand_at_turn3_may = []

    def h2(e, d):
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "yes_no":
            if e.s.turn == 3 and not hand_at_turn3_may:
                hand_at_turn3_may.append(len(e.zlist("hand", 0)))
            e.answer([1])
            return True
        if d["kind"] == "attack" and d.get("player") == 1 and "attack:T002:player" in keys \
                and not attacked:
            attacked.append(True)
            e.answer([keys.index("attack:T002:player")])
            return True
        return False

    e = setup(rules, {"bz": ["dm19-018"], "hand": ["T002", "T002"]}, {"bz": ["T002"]})
    _drive(e, h2, turns=3)
    assert attacked, "相手が攻撃できていない"
    assert len(e.zlist("shield", 0)) == 4      # シールドが1枚割れた
    # ターン3のドロー提示時点の手札は、ターンドローの1枚だけ
    # （攻撃後に手札3枚〈元2枚＋割れたシールド〉をすべて捨てた証拠）
    assert hand_at_turn3_may == [1]
