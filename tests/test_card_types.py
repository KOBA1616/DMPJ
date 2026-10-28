"""クリーチャー以外のカードタイプ（タマシード・フィールド・クロスギア）とシンカライズ。条文 303 / 308 / 315。"""
import pytest
import yaml
from conftest import answer, setup

from dmsim.defs import DATA, load_rules
from dmsim.defs import card_yaml_files  # noqa: E402


def mk(i, types, kw=None, cost=1, power=0, extra=None):
    d = {"id": i, "name": i, "types": types, "civs": ["nature"], "cost": cost, "text": "x", **(extra or {})}
    if power:
        d["power"] = power
    if kw:
        d["keywords"] = kw
    return d


@pytest.fixture()
def rr(tmp_path):
    f = tmp_path / "ct.yaml"
    f.write_text(yaml.safe_dump({"cards": [
        mk("S001", ["tamaseed"], ["shinka_rise"]),
        mk("S002", ["tamaseed"], extra={"abilities": [{"kind": "trigger", "when": {"event": "move", "to": "bz", "subject": "self"},
                                                        "effect": [{"op": "draw", "count": 1}]}]}),
        mk("F001", ["field"]),
        mk("G001", ["cross_gear"]),
        mk("E001", ["creature", "evolution"], cost=1, power=5000, extra={"evolve_from": {"civs": ["nature"]}}),
    ]}, allow_unicode=True))
    return load_rules(card_yaml_files() + [f])


@pytest.mark.parametrize("cid", ["S001", "F001", "G001"])
def test_permanent_card_is_played_to_battle_zone(rr, cid):
    """タマシード・フィールド・クロスギアは、実行（展開・ジェネレート）するとバトルゾーンに出る。クリーチャーではない。"""
    e = setup(rr, {"hand": [cid], "mana": ["T001"]})
    answer(e, "charge", "pass")
    answer(e, "main", f"play:{cid}")
    e.advance()
    on_bz = [c for c in e.s.zones["bz"][0] if e.s.cards[c].defn == cid]
    assert on_bz and "creature" not in e.chars(on_bz[0])["types"]


def test_tamaseed_enter_trigger(rr):
    e = setup(rr, {"hand": ["S002"], "mana": ["T001"]})
    answer(e, "charge", "pass")
    answer(e, "main", "play:S002")
    e.advance()
    assert len(e.zlist("hand", 0)) == 1


def test_tamaseed_is_not_a_creature_target_for_creature_effects(rr):
    e = setup(rr, {"bz": ["S002"]})
    assert not e.candidates({"zone": "bz", "owner": "you", "filter": {"types": ["creature"]}}, {"you": 0, "self": None, "vars": {}})


def test_shinka_rise_lets_evolution_go_on_tamaseed_only_with_keyword(rr):
    """シンカライズを持つタマシードの上にだけ進化クリーチャーを置ける。持たないタマシードの上には置けない。"""
    e = setup(rr, {"hand": ["E001"], "bz": ["S001"], "mana": ["T001"]})
    answer(e, "charge", "pass")
    d = e.advance()
    assert d["kind"] == "main" and "play:E001" in [o["key"] for o in d["options"]]
    e = setup(rr, {"hand": ["E001"], "bz": ["S002"], "mana": ["T001"]})
    answer(e, "charge", "pass")
    d = e.advance()
    assert "play:E001" not in [o["key"] for o in d["options"]]
