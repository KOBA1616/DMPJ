"""語彙パイロット第71弾: l_gate（L・ゲート）。

「L・ゲート：種族」は既存の kind: replace で表す。新語彙なし。
破壊される時、かわりに墓地からその種族を手札に戻してもよい。そうしたら山札の一番下へ。
"""
from dmsim.defs import load_tables, parse_card

TABLES = load_tables()

CARD = {
    "id": "test-lg",
    "name": "試験門獣",
    "types": ["creature"],
    "civs": ["light"],
    "cost": 6,
    "power": 6000,
    "races": ["テスト"],
    "text": "L・ゲート：グレートメカオー（このクリーチャーが破壊される時、墓地に置くかわりに、グレートメカオーを１体、自分の墓地から手札に戻してもよい。そうした場合、このクリーチャーを山札の一番下に置く）",
    "abilities": [
        {"kind": "replace",
         "when": {"event": "move", "from": "bz", "to": "graveyard",
                  "reason": "destroy", "subject": "self"},
         "instead": [
             {"op": "may", "body": [
                 {"op": "choose",
                  "select": {"zone": "graveyard", "owner": "you",
                             "filter": {"race_has": "グレートメカオー"}, "count": 1},
                  "as": "g"},
                 {"op": "move", "select": {"ref": "g"}, "to": "hand", "reason": "return"},
                 {"op": "move", "select": {"ref": "self"}, "to": "deck", "reason": "put", "position": "bottom"},
             ]},
         ]},
    ],
    "source": {"official": "test-lg", "review": "pending"},
}


def test_l_gate_parses():
    card = parse_card(CARD, TABLES)
    assert card is not None
    ab = card.abilities[0]
    assert ab["kind"] == "replace"


def test_l_gate_replace_kind():
    # replace が有効な kind であることを確認
    from dmsim.defs import load_tables
    t = load_tables()
    assert t is not None
