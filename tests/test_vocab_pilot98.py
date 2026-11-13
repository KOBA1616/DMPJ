"""語彙パイロット第98弾: enters_from_non_hand_replacement（手札以外から出る時の置換）。

when の from / to / reason / via にリスト指定を許可した（本弾でエンジン拡張）。
「手札以外から出る」は from: [graveyard, mana, deck, shield]、「召喚以外の方法で出る」は
reason: put（出現理由は summon / put の2種のみ）で表す。
"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.cards.defs import card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


CARD = {
    "id": "test-efnh",
    "name": "試験関所獣",
    "types": ["creature"],
    "civs": ["light"],
    "cost": 6,
    "power": 5000,
    "races": ["テスト"],
    "text": "相手のクリーチャーが、相手の手札以外から出る時、その持ち主は、かわりにそのクリーチャーを手札に加える。",
    "abilities": [
        {"kind": "replace",
         "when": {"event": "move", "to": "bz",
                  "from": ["graveyard", "mana", "deck", "shield"],
                  "subject": {"owner": "opp", "filter": {"types": ["creature"]}}},
         "instead": [
             {"op": "move", "select": {"ref": "event.subject"}, "to": "hand", "reason": "put"},
         ]},
    ],
    "source": {"official": "test-efnh", "review": "pending"},
}


def test_from_list_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "replace"


def test_from_list_kept():
    card = parse_card(CARD, TABLES)
    ab = card.abilities[0]
    assert ab["when"]["from"] == ["graveyard", "mana", "deck", "shield"]


def test_from_list_matching(rr):
    """from リスト照合: 墓地・マナからは一致、手札からは不一致。"""
    e = setup(rr, {"bz": ["R077"]}, {"bz": []})
    env = {"you": 0}
    when = {"event": "move", "to": "bz", "from": ["graveyard", "mana", "deck", "shield"]}
    assert e._match_when(when, {"ev": "move", "to": "bz", "from": "graveyard"}, env)
    assert e._match_when(when, {"ev": "move", "to": "bz", "from": "mana"}, env)
    assert not e._match_when(when, {"ev": "move", "to": "bz", "from": "hand"}, env)
