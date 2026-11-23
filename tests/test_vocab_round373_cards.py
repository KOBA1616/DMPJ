"""再変換ラウンド373（第338弾 opponent_chooses_deck_position）の記録テスト。

- 新規登録4件: dm22rp1-034 氷結呪文「フリズン」 /
  dm23rp1-035 Uta-Awase選手宣誓のスピーチ / dm25rp4-036
  ツインヘッドの海幻 / dmrp16-s02 頻波羅 ビリヤ棒ド。
  いずれも登録形は確立形と完全一致。
- alias 畳み込み0件・差し戻し0件（submit 時の警告なし）。
- converted 10,297→10,301 / rejects 2,017→2,013、
  canonical 重なり0・漏れ0。opponent_chooses_deck_position
  の行は残っていない（ファミリー解消）。

実挙動は登録カード自身で固定する（フリズンを唱えると
modal の決定が相手に渡り、相手が選んだ位置に置かれる。
ビリヤ棒ドは捨てた手札の枚数だけ対象が増える）。
ドライバは scenario.build の薄い包みで、tests.conftest は
import しない（第319弾以降の作法）。
"""
import json
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards import cardstore  # noqa: E402

from tests import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"


def _modal_deck(var, player):
    return {"op": "modal", "player": player, "modes": [
        [{"op": "move", "select": {"ref": var, "count": "all"},
          "to": "deck", "reason": "put", "position": "top"}],
        [{"op": "move", "select": {"ref": var, "count": "all"},
          "to": "deck", "reason": "put", "position": "bottom"}]]}


SPELL_034 = [
    {"op": "choose",
     "select": {"zone": "bz", "owner": "opp",
                "filter": {"types": ["creature", "tamaseed"]},
                "count": 1},
     "as": "target"},
    _modal_deck("target", "opp"),
]
FORM_S02 = [
    {"kind": "trigger",
     "when": {"event": "move", "to": "bz", "subject": "self"},
     "effect": [{"op": "repeat", "times": 2,
                 "body": [{"op": "may",
                           "body": [{"op": "draw", "count": 1}]}]}]},
    {"kind": "trigger",
     "when": {"event": "attack", "subject": "self"},
     "effect": [{"op": "repeat", "times": 2, "body": [
         {"op": "move",
          "select": {"zone": "hand", "owner": "you", "count": 1,
                     "up_to": True},
          "to": "graveyard", "reason": "discard", "as": "d"},
         {"op": "if", "cond": {"exists": {"ref": "d"}}, "then": [
             {"op": "choose",
              "select": {"zone": "bz", "owner": "opp",
                         "filter": {"types": ["creature"]},
                         "count": 1},
              "as": "el"},
             _modal_deck("el", "opp")]}]}]},
]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _reject_rows():
    out = {}
    for line in open(REJECTS, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def test_round373_disposition():
    rej = _reject_rows()
    assert len(rej) == 2013
    conv = _conv_cache.all_cards(CONVERTED)
    ids = {c["id"] for c in conv}
    assert len(ids) == 10301
    assert not (ids & set(rej))          # canonical 重なり0
    for t in ("dm22rp1-034", "dm23rp1-035", "dm25rp4-036",
              "dmrp16-s02"):
        c = _conv_cache.find(CONVERTED, t)
        assert c is not None, t
        assert not (c.get("source") or {}).get("unsupported")
        parse_card(c, TABLES)
    c = _conv_cache.find(CONVERTED, "dm22rp1-034")
    assert c["spell"] == SPELL_034
    c = _conv_cache.find(CONVERTED, "dmrp16-s02")
    assert c["abilities"] == FORM_S02
    left = {rid for rid, r in rej.items()
            if "opponent_chooses_deck_position" in (r.get("gaps") or [])}
    assert left == set(), left            # ファミリー解消


# ---------- 実挙動ドライバ（scenario.build 直包み） ----------

def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _pick(keys, defn):
    return next(i for i, k in enumerate(keys)
                if f":{defn}:" in k or k.endswith(f":{defn}"))


def _deck_defns(e, p):
    return [e.s.cards[c].defn for c in e.zlist("deck", p)]


def test_registered_freeze_opponent_decides(rules):
    e = _build(rules, {"hand": ["dm22rp1-034"], "bz": ["T001"],
                       "mana": ["T009", "T001", "T001", "T001"]},
               {"bz": ["T005"]})
    played = False
    modal_player = None
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if played and modal_player is not None \
                and d["kind"] == "attack" and d.get("player") == 0:
            break
        if d["kind"] == "main" and d.get("player") == 0 and not played \
                and "play:dm22rp1-034" in keys:
            e.answer([keys.index("play:dm22rp1-034")])
            played = True
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "charge" and not played:
            e.answer([keys.index("pass")] if "pass" in keys else [0])
            continue
        if d["kind"] == "choose_cards":
            e.answer([_pick(keys, "T005")])
            continue
        if d["kind"] == "choose_mode":
            modal_player = d.get("player")
            e.answer([keys.index("mode:1")])   # 山札の下
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert modal_player == 1
    assert _deck_defns(e, 1)[-1] == "T005"
    assert e.bz_tops(1) == []


def test_registered_billy_attack_scales(rules):
    e = _build(rules, {"hand": ["dmrp16-s02", "T001", "T003"],
                       "mana": ["T009"] + ["T001"] * 6},
               {"bz": ["T005", "T009"]})
    summoned = False
    attacked = False
    modal_players = []
    modal_modes = iter([0, 1])
    discards = iter(["T001", "T003"])
    targets = iter(["T005", "T009"])
    for _ in range(900):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "choose_shields":
            break
        if d["kind"] == "main" and d.get("player") == 0 and not summoned \
                and "play:dmrp16-s02" in keys:
            e.answer([keys.index("play:dmrp16-s02")])
            summoned = True
            continue
        if d["kind"] == "attack" and d.get("player") == 0 and summoned \
                and not attacked and "attack:dmrp16-s02:player" in keys:
            e.answer([keys.index("attack:dmrp16-s02:player")])
            attacked = True
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "yes_no" and not attacked:
            e.answer([keys.index("no")])
            continue
        if d["kind"] == "choose_cards" and attacked:
            if any(k.startswith("hand:") for k in keys):
                e.answer([_pick(keys, next(discards))])
            else:
                e.answer([_pick(keys, next(targets))])
            continue
        if d["kind"] == "choose_mode":
            modal_players.append(d.get("player"))
            e.answer([keys.index(f"mode:{next(modal_modes)}")])
            continue
        if d["kind"] == "block":
            e.answer([keys.index("no_block")])
            continue
        if d["kind"] == "declare_strigger":
            e.answer([])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    else:
        raise AssertionError("attack trigger did not resolve")
    assert modal_players == [1, 1]
    assert [e.s.cards[c].defn for c in e.zlist("hand", 0)] == ["T002"]
    assert [e.s.cards[c].defn for c in e.zlist("graveyard", 0)] == \
        ["T001", "T003"]
    deck = _deck_defns(e, 1)
    assert deck[0] == "T005" and deck[-1] == "T009"
    assert e.bz_tops(1) == []
