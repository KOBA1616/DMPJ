"""コストの増減（mod cost）とシンパシー・コスト常在型パターン。支払うコストだけが変わり、カードのコスト（参照）は変わらない。"""
import sys
from pathlib import Path

import pytest
import yaml
from conftest import answer, setup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import rule_convert as rc  # noqa: E402

from dmsim.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402

BASE = {"card_type": "クリーチャー", "civilization": "自然", "cost": "5", "power": "3000", "race": "テスト", "name": "試験"}


def card(cid, text, **kw):
    r = rc.convert({**BASE, "id": cid, "text": text, **kw})
    assert r is not None, text
    parse_card(r, load_tables())
    return r


@pytest.fixture()
def build(tmp_path):
    def make(*cards):
        f = tmp_path / "c.yaml"
        f.write_text(yaml.safe_dump({"cards": list(cards)}, allow_unicode=True), encoding="utf-8")
        return load_rules(sorted((DATA / "cards").glob("*.yaml")) + [f])
    return make


def keys(e):
    d = e.advance()
    if d["kind"] != "main":   # 出せるカードが無ければ攻撃へ進む
        return []
    return [o["key"] for o in d["options"]]


def test_sympathy_reduces_cost_per_creature_and_keeps_printed_cost(build):
    """シンパシー: バトルゾーンの自分のクリーチャー1体につきコストが少なくなる（コスト5・クリーチャー3体 → 2）。参照するコストは5のまま。"""
    sy = card("Y1", "シンパシー：クリーチャー（このクリーチャーを召喚する時支払うコストは、バトルゾーンにある自分のクリーチャー1体につき1少なくなる）")
    rr = build(sy)
    e = setup(rr, {"hand": ["Y1"], "bz": ["T001", "T001", "T001"], "mana": ["T001", "T001"]})
    answer(e, "charge", "pass")
    assert "play:Y1" in keys(e)                       # 5 - 3 = 2 でマナ2枚で召喚できる
    y = e.zlist("hand", 0)[0]
    assert e.chars(y)["cost"] == 5 and e.chars(y)["pay_cost"] == 2
    e = setup(rr, {"hand": ["Y1"], "bz": ["T001"], "mana": ["T001", "T001"]})
    answer(e, "charge", "pass")
    assert "play:Y1" not in keys(e)                   # 5 - 1 = 4 は払えない


def test_sympathy_amount_comes_from_note():
    r = card("Y2", "シンパシー：クリーチャー（このクリーチャーを召喚する時支払うコストは、バトルゾーンにある自分のクリーチャー1体につき2少なくなる）")
    assert r["abilities"][0]["mod"]["cost"]["amount"] == -2
    assert rc.convert({**BASE, "id": "y3", "text": "シンパシー：クリーチャー"}) is None        # 注釈がなく量が分からない → モデルへ


def test_cost_floor_is_zero(build):
    sy = card("Y4", "シンパシー：クリーチャー（このクリーチャーを召喚する時支払うコストは、バトルゾーンにある自分のクリーチャー1体につき9少なくなる）")
    e = setup(build(sy), {"hand": ["Y4"], "bz": ["T001", "T001"]})
    assert e.chars(e.zlist("hand", 0)[0])["pay_cost"] == 0


def test_static_cost_reduction_for_my_race_and_increase_for_opponent_spells(build):
    red = card("Y5", "自分のドラゴン・クリーチャーの召喚コストを2少なくする。")
    inc = card("Y6", "相手の呪文を唱えるコストは2多くなる。")
    assert red["abilities"][0]["affects"]["filter"] == {"types": ["creature"], "race_has": "ドラゴン"}
    assert inc["abilities"][0]["mod"] == {"cost": 2}
    rr = build(red, inc, {"id": "D1", "name": "竜", "types": ["creature"], "civs": ["fire"], "cost": 5, "power": 1000, "races": ["アーマード・ドラゴン"], "text": "x"})
    e = setup(rr, {"bz": ["Y5"], "hand": ["D1"]}, {"bz": ["Y6"]})
    assert e.chars(e.zlist("hand", 0)[0])["pay_cost"] == 3
    e2 = setup(rr, {"bz": ["Y5"], "hand": ["D1"]})
    assert e2.chars(e2.zlist("hand", 0)[0])["pay_cost"] == 3
    e3 = setup(rr, {"hand": ["D1"]})
    assert e3.chars(e3.zlist("hand", 0)[0])["pay_cost"] == 5
