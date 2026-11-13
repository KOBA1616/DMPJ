"""語彙拡張: ウェーブストライカー（キーワードは印、能力は if で「他に2体以上」を見る）と、誘発条件を誘発時にも見る規則（603.4）。"""
from pathlib import Path

import pytest
from conftest import answer, setup

from dmsim.cards.defs import card_yaml_files, load_rules


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def play(rr, others):
    e = setup(rr, {"hand": ["R054"], "mana": ["T001"], "bz": ["R054"] * others})
    d = e.advance()
    assert d["kind"] == "charge"
    e.answer([[o["key"] for o in d["options"]].index("pass")])
    answer(e, "main", "play:R054")
    e.advance()
    return e


def hand(e):
    return len(e.zlist("hand", 0))


def test_ability_gained_only_with_two_other_wave_strikers(rr):
    """他に2体以上いる時だけ、出た時にカードを1枚引く。"""
    h0, h1, h2 = (hand(play(rr, n)) for n in (0, 1, 2))
    assert h0 == h1 and h2 == h1 + 1


def test_static_abilities_follow_the_condition(rr):
    """常在型も同じ条件で働く。自身への修整と自分のクリーチャー全体への修整のどちらも。"""
    two = setup(rr, {"bz": ["R055", "R054", "R054"]})
    pw = sorted(two.chars(c)["power"] for c in two.bz_tops(0))
    assert pw == [2000, 2000, 6000]                       # R055: 1000+4000+1000, R054 ×2: 1000+1000
    one = setup(rr, {"bz": ["R055", "R054"]})
    assert sorted(one.chars(c)["power"] for c in one.bz_tops(0)) == [1000, 1000]


def test_rule_convert_gates_every_ability_after_wave_striker():
    """ルール変換でも、ウェーブストライカーに続く能力は「他に2体以上」の条件つきにする（付け忘れは常時働く誤変換）。"""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import rule_convert
    row = {"id": "x-1", "name": "試験", "card_type": "クリーチャー", "civilization": "自然", "cost": "2", "power": "1000",
           "race": "ワイルド・ベジーズ", "mana": "1",
           "text": "ウェーブストライカー(バトルゾーンに「ウェーブストライカー」を持つクリーチャーが他に２体以上あれば、このクリーチャーは次の能力を得る)\nパワーアタッカー +3000(攻撃中、このクリーチャーのパワーは+3000される)"}
    card = rule_convert.convert(row)
    assert card["keywords"] == ["wave_striker"]
    assert [ab["if"] for ab in card["abilities"]] == [rule_convert.WAVE_COND]
