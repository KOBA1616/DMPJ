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


def test_hyper_energy_taps_creatures_with_different_costs(build):
    he = card("H1", "ハイパーエナジー（このクリーチャーを召喚する時、コストが異なる自分のクリーチャーを好きな数タップしてもよい。こうしてタップしたクリーチャー１体につき、このクリーチャーの召喚コストを２少なくする。ただし、コストは０以下にはならない）", cost="6")
    assert r_keywords(he) == ["hyper_energy"]
    mk = lambda i, c: {"id": i, "name": i, "types": ["creature"], "civs": ["nature"], "cost": c, "power": 1000, "races": ["テスト"], "text": "x"}
    rr = build(he, mk("A1", 1), mk("A2", 2), mk("A3", 1))
    e = setup(rr, {"hand": ["H1"], "bz": ["A1", "A2", "A3"], "mana": ["T001", "T001"]})
    answer(e, "charge", "pass")
    d = e.advance()
    assert d["kind"] == "main"
    e.answer([[o["key"] for o in d["options"]].index("play:H1")])
    d = e.advance()
    assert d["kind"] == "choose_cards" and len(d["options"]) == 3
    e.answer([0])                                     # 1体目（コスト1）
    d = e.advance()
    assert len(d["options"]) == 1                     # 同じコストのもう1体は選べない
    e.answer([0])                                     # コスト2
    e.advance()                                       # 6 - 4 = 2: マナ2枚で払い、支払いの選択肢は1通りなので自動で進む
    assert [e.s.cards[c].tapped for c in e.zlist("mana", 0)] == [True, True]
    assert sum(e.s.cards[c].tapped for c in e.zlist("bz", 0) if e.s.cards[c].defn != "H1") == 2
    assert any(e.s.cards[c].defn == "H1" for c in e.zlist("bz", 0))


def r_keywords(r):
    return r.get("keywords")


def test_sasagale_destroys_to_reduce_dispector_cost(build):
    sa = card("S1", "ササゲール２（ディスペクターを召喚する時、コストを２少なくしてもよい。そうしたら、このクリーチャーを破壊する。そのディスペクターのコストは０以下にはならない）", cost="1")
    assert sa["abilities"][0]["mod"] == {"sac_reduce": 2}
    dis = {"id": "S2", "name": "ディス", "types": ["creature"], "civs": ["nature"], "cost": 3, "power": 1000, "races": ["ディスペクター"], "text": "x"}
    e = setup(build(sa, dis), {"hand": ["S2"], "bz": ["S1"], "mana": ["T001"]})
    answer(e, "charge", "pass")
    d = e.advance()
    e.answer([[o["key"] for o in d["options"]].index("play:S2")])
    d = e.advance()
    assert d["kind"] == "choose_cards"                 # 3 - 2 = 1 でマナ1枚。S1 を破壊する
    e.answer([0])
    e.advance()
    names = [e.s.cards[c].defn for c in e.zlist("bz", 0)]
    assert names == ["S2"] and e.s.cards[e.zlist("graveyard", 0)[0]].defn == "S1"


def test_bad_reduces_cost_and_destroys_at_turn_end(build):
    b = card("B1", "B・A・D２（このクリーチャーを、コストを２少なくして召喚してもよい。そうしたら、このターンの終わりにこのクリーチャーを破壊する）", cost="3")
    assert b["abilities"][0]["mod"]["opt_reduce"] == {"amount": 2, "then": "destroy"}
    e = setup(build(b), {"hand": ["B1"], "mana": ["T001"]})
    answer(e, "charge", "pass")
    d = e.advance()
    e.answer([[o["key"] for o in d["options"]].index("play:B1")])
    d = e.advance()
    assert [o["key"] for o in d["options"]] == ["reduce", "normal"]
    e.answer([0])
    e.advance()                                        # 召喚→そのターンの終わりに破壊されるところまで進む
    assert e.s.turn_counters is not None
    assert [e.s.cards[c].defn for c in e.zlist("graveyard", 0)] == ["B1"] and not e.zlist("bz", 0)


def test_joe_puts_bottom_of_deck_and_draws_at_turn_end(build):
    j = card("J1", "J・O・E２(このクリーチャーを、コストを２少なくして召喚してもよい。そうしたら、このターンの終わりに、これを自分の山札の一番下に置く。下に置いたら、カードを１枚引く)", cost="3")
    assert j["abilities"][0]["mod"]["opt_reduce"]["then"] == "deck_bottom_draw"
    e = setup(build(j), {"hand": ["J1"], "mana": ["T001"], "deck": ["T001", "T001"]})
    answer(e, "charge", "pass")
    d = e.advance()
    e.answer([[o["key"] for o in d["options"]].index("play:J1")])
    d = e.advance()
    e.answer([0])
    e.advance()
    assert not e.zlist("bz", 0) and e.s.cards[e.zlist("deck", 0)[-1]].defn == "J1"
