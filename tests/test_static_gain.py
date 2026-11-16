"""常在型の mod.gain（サバイバー「自分の他のサバイバーも上の能力を得る」）がバトルゾーンの他の札に能力を与える。"""
import copy

import pytest
import yaml

from conftest import setup
from dmsim import load_rules
from dmsim.cards.defs import card_yaml_files

SURV = {"owner": "you", "filter": {"races": ["サバイバー"]}, "other": True}
UNTAP = {"kind": "trigger", "when": {"event": "turn_end"}, "if": {"is_turn": "you"},
         "effect": [{"op": "untap", "select": {"ref": "self"}}]}
DISCARD = {"kind": "trigger", "when": {"event": "attack", "subject": "self"},
           "effect": [{"op": "discard", "select": {"zone": "hand", "owner": "opp", "count": 1, "chooser": "opp"}}]}


def _card(cid, ab):
    return {"id": cid, "name": cid, "types": ["creature"], "civs": ["light"], "cost": 5, "power": 3000,
            "races": ["サバイバー"], "abilities": [copy.deepcopy(ab), {"kind": "static", "affects": copy.deepcopy(SURV), "mod": {"gain": [copy.deepcopy(ab)]}}]}


@pytest.fixture(scope="module")
def rules(tmp_path_factory):
    f = tmp_path_factory.mktemp("gain") / "gain.yaml"
    f.write_text(yaml.safe_dump({"cards": [_card("dm05-022", UNTAP), _card("dm05-013", DISCARD)]},
                                allow_unicode=True), encoding="utf-8")
    return load_rules(list(card_yaml_files()) + [f])


def _id(e, defn):
    return next(c for c in e.bz_tops(0) if e.s.cards[c].defn == defn)


def _whens(e, cid, kind="trigger"):
    return [ab["when"]["event"] for _, ab in e.abilities(cid, kind)]


def test_survivor_gain_both_ways(rules):
    e = setup(rules, {"bz": ["dm05-022", "dm05-013"]}, {})
    bals, tiara = _id(e, "dm05-022"), _id(e, "dm05-013")
    assert "turn_end" in _whens(e, tiara)        # バルスβの「ターンの終わりにアンタップ」をティアラが得る
    assert "attack" in _whens(e, bals)           # ティアラの「攻撃時に相手が捨てる」をバルスが得る
    assert _whens(e, bals).count("turn_end") == 1     # 自分自身には重ねて与えない（other: true）


def test_survivor_gain_not_to_opponent(rules):
    e = setup(rules, {"bz": ["dm05-022"]}, {"bz": ["dm05-013"]})
    tiara = next(c for c in e.bz_tops(1) if e.s.cards[c].defn == "dm05-013")
    assert "turn_end" not in _whens(e, tiara)
