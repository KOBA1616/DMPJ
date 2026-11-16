"""from_under 機構: 対象10件の登録済みカードの検証（再変換ラウンド194で登録）。

登録形は rejects の partial に from_under 誘発を足し、unsupported から
from_under_trigger を外したもの（submit が split のキーワード等を統合した形）。

変換の型:
- dm34 系5件（カード自身＋宿主フィルタ）:
  when {event: move, to: graveyard, subject: self, from_under: {filter: {types: [evolution]}}}
- dmsd06-012 マイケル・ギャンドル（観測者。「破壊された時」と「下から墓地に置かれた時」は
  同じ移動で重ならないよう、破壊側に from_under: false を付けて分ける）:
  when {event: move, to: graveyard, reason: destroy, subject: {owner: you, filter: {race_has: 魔導具}}, from_under: false}
  when {event: move, to: graveyard, subject: {owner: you, filter: {race_has: 魔導具}}, from_under: true}
- 邪眼帝2件（宿主自身）:
  when {event: move, from_under: self} ＋ modal（シールド化／相手クリーチャー破壊）
- dm25ex3-or4 ジャシン（観測者＋宿主 owner）:
  when {event: move, subject: {owner: you}, from_under: {owner: you}}
- dm25rp4-033（観測者＋宿主 owner。動いたカード自身を手札に戻す）:
  when {event: move, to: graveyard, subject: {owner: you}, from_under: {owner: you}}
  effect の select は {ref: event.subject}
"""
import copy
import _conv_cache  # noqa: E402
from pathlib import Path

import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()
CONVERTED = Path(__file__).parent.parent / "data" / "cards" / "converted.yaml"

DRAW_MAY = [{"op": "may", "body": [{"op": "draw", "count": 1}]}]

DM34_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "to": "graveyard", "subject": "self",
             "from_under": {"filter": {"types": ["evolution"]}}},
    "effect": DRAW_MAY,
}

DMSD06_TRIGGERS = [
    {"kind": "trigger",
     "when": {"event": "move", "to": "graveyard", "reason": "destroy",
              "subject": {"owner": "you", "filter": {"race_has": "魔導具"}},
              "from_under": False},
     "effect": DRAW_MAY},
    {"kind": "trigger",
     "when": {"event": "move", "to": "graveyard",
              "subject": {"owner": "you", "filter": {"race_has": "魔導具"}},
              "from_under": True},
     "effect": DRAW_MAY},
]

JAGAN_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from_under": "self"},
    "effect": [{"op": "modal", "modes": [
        [{"op": "move", "select": {"zone": "deck", "owner": "you", "from_top": 1},
          "to": "shield", "reason": "put"}],
        [{"op": "destroy", "select": {"zone": "bz", "owner": "opp", "count": 1,
                                      "filter": {"types": ["creature"]}}}]]}],
}

JASHIN_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "subject": {"owner": "you"}, "from_under": {"owner": "you"}},
    "effect": [{"op": "discard", "select": {"zone": "hand", "owner": "opp",
                                            "chooser": "opp", "count": 1}},
               {"op": "may", "body": [{"op": "break", "player": "opp", "count": 1}]}],
}

AQUA_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "to": "graveyard", "subject": {"owner": "you"},
             "from_under": {"owner": "you"}},
    "effect": [{"op": "may", "body": [
        {"op": "move", "select": {"ref": "event.subject"}, "to": "hand", "reason": "return"}]}],
}

CASES = {
    "dm34-038": [DM34_TRIGGER],
    "dm34-042": [DM34_TRIGGER],
    "dm34-046": [DM34_TRIGGER],
    "dm34-050": [DM34_TRIGGER],
    "dm34-054": [DM34_TRIGGER],
    "dmsd06-012": DMSD06_TRIGGERS,
    "dm26rp3-sp002": [JAGAN_TRIGGER],
    "dm25ex3-rp2s06": [JAGAN_TRIGGER],
    "dm25ex3-or4": [JASHIN_TRIGGER],
    "dm25rp4-033": [AQUA_TRIGGER],
}


def _registered():
    data = {"cards": _conv_cache.all_cards(CONVERTED)}
    return {c["id"]: c for c in data["cards"] if c["id"] in CASES}


def test_all_ten_targets_parse():
    registered = _registered()
    assert set(registered) == set(CASES), f"converted に無い対象: {set(CASES) - set(registered)}"
    for cid, added in CASES.items():
        card = copy.deepcopy(registered[cid])
        assert not (card.get("source") or {}).get("unsupported"), f"{cid}: unsupported が残る"
        for trig in added:
            assert trig in (card.get("abilities") or []), f"{cid}: from_under 誘発が登録形と違う"
        parsed = parse_card(card, TABLES)
        whens = [a["when"] for a in parsed.abilities if a["kind"] == "trigger"]
        assert any("from_under" in w for w in whens), f"{cid}: from_under 誘発が無い"
