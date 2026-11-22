"""語彙パイロット第338弾: opponent_chooses_deck_position。

対象（pure 4件）:
- dm22rp1-034 氷結呪文「フリズン」（相手のクリーチャー／
  タマシードを1つ選び、相手はそれを山札の上または下に置く）
- dm23rp1-035 Uta-Awase選手宣誓のスピーチ（エレメントを
  1つ選ぶ。その持ち主は、それを山札の上または下に置く）
- dm25rp4-036 ツインヘッドの海幻（出た時、相手のエレメント
  を1つ選ぶ。相手はそれを山札の上か下に置く。その後、自分を
  NEO／進化クリーチャーの下に置いてもよい）
- dmrp16-s02 頻波羅 ビリヤ棒ド（攻撃する時、手札を2枚まで
  捨てる。捨てた1枚につき相手のクリーチャーを1体選び、
  相手はそれを自身の山札の上または下に置く）

エンジン拡張: modal に player を追加（ops.py の @op と
op_modal、base/opvocab.py、defs.py の players 検証、
schema.py の players 型、card.schema.json 再生成の5点）。
player は "you"/"opp"/{var:}（_rel で解決）に加えて
{owner_of: 変数名}（束縛したカードの持ち主）を取れる。
モード内の move は position: top/bottom の確立形。

ビリヤ棒ドの「捨てた枚数だけ」は、discard の move に
as で束縛し、if {exists: {ref: d}} でゲートする形。

proto: T1024（フリズン型）/ T1025（スピーチ型）/
T1026（海幻型）/ T1027（ビリヤ棒ド型）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が復活するので
scenario.build を直接包む（第319弾以降の作法）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()


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
STATIC_034 = [{
    "kind": "static", "zone": "shield", "affects": "self",
    "if": {"cmp": [{"count": {"zone": "bz", "owner": "you",
                              "filter": {"civs": ["water"],
                                         "types": ["creature",
                                                   "tamaseed"]}}},
                    ">=", 2]},
    "mod": {"allow": ["s_trigger"]},
}]

SPELL_035 = [
    {"op": "choose",
     "select": {"zone": "bz", "owner": "any", "count": 1},
     "as": "el"},
    _modal_deck("el", {"owner_of": "el"}),
]
STP_035 = [{
    "op": "modify",
    "select": {"zone": "bz", "owner": "opp",
               "filter": {"types": ["creature"]}, "count": 2},
    "mod": {"deny": ["attack_player", "attack_creature", "block"]},
    "duration": "until_next_own_turn_start",
}]

FORM_036 = [
    {"kind": "static", "choukon": True, "affects": "self",
     "mod": {"grant": ["powered_breaker"]}},
    {"kind": "static", "choukon": True, "affects": "self",
     "mod": {"power": 3000}},
    {"kind": "trigger",
     "when": {"event": "move", "to": "bz", "subject": "self"},
     "effect": [
         {"op": "choose",
          "select": {"zone": "bz", "owner": "opp", "count": 1},
          "as": "el"},
         _modal_deck("el", "opp"),
         {"op": "may", "body": [
             {"op": "choose",
              "select": {"zone": "bz", "owner": "you",
                         "filter": {"types": ["creature"],
                                    "any_of": [{"neo": True},
                                               {"evolution": True}]},
                         "count": 1},
              "as": "host"},
             {"op": "put_under",
              "select": {"ref": "self", "count": "all"},
              "onto": {"ref": "host"}}]}]},
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


def test_proto_forms(rules):
    c = proto_card("T1024")
    assert c["spell"] == SPELL_034 and c["abilities"] == STATIC_034
    parse_card(c, TABLES)
    c = proto_card("T1025")
    assert c["spell"] == SPELL_035 and c["stp_spell"] == STP_035
    parse_card(c, TABLES)
    c = proto_card("T1026")
    assert c["abilities"] == FORM_036
    parse_card(c, TABLES)
    c = proto_card("T1027")
    assert c["abilities"] == FORM_S02
    assert c["mugen_climb"] == {"tap": 3, "cost": 3, "civs": ["water"]}
    parse_card(c, TABLES)


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


def _cast_and_modal(e, play_key, pick_defn, mode):
    """呪文を唱え、対象を選んで modal（相手の決定）で置く。
    modal 決定の player を返す。"""
    played = False
    modal_player = None
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if played and modal_player is not None \
                and d["kind"] == "attack" and d.get("player") == 0:
            return modal_player
        if d["kind"] == "main" and d.get("player") == 0 and not played \
                and play_key in keys:
            e.answer([keys.index(play_key)])
            played = True
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "charge" and not played:
            e.answer([keys.index("pass")] if "pass" in keys else [0])
            continue
        if d["kind"] == "choose_cards":
            e.answer([_pick(keys, pick_defn)])
            continue
        if d["kind"] == "choose_mode":
            modal_player = d.get("player")
            e.answer([keys.index(f"mode:{mode}")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("cast/modal did not resolve")


def test_t1024_opponent_puts_on_bottom(rules):
    e = _build(rules, {"hand": ["T1024"], "bz": ["T001"],
                       "mana": ["T009", "T001", "T001", "T001"]},
               {"bz": ["T005"]})
    who = _cast_and_modal(e, "play:T1024", "T005", 1)
    assert who == 1                       # 置く位置は相手が選ぶ
    deck = _deck_defns(e, 1)
    assert deck[-1] == "T005" and "T005" not in deck[:-1]
    assert e.bz_tops(1) == []


def test_t1024_opponent_puts_on_top(rules):
    e = _build(rules, {"hand": ["T1024"], "bz": ["T001"],
                       "mana": ["T009", "T001", "T001", "T001"]},
               {"bz": ["T005"]})
    who = _cast_and_modal(e, "play:T1024", "T005", 0)
    assert who == 1
    assert _deck_defns(e, 1)[0] == "T005"


def test_t1025_owner_decides_for_own_element(rules):
    e = _build(rules, {"hand": ["T1025"], "bz": ["T001", "T004"],
                       "mana": ["T009", "T001", "T001", "T001"]},
               {"bz": ["T005"]})
    who = _cast_and_modal(e, "play:T1025", "T001", 0)
    assert who == 0                       # 自分のカードは自分が選ぶ
    assert _deck_defns(e, 0)[0] == "T001"


def test_t1025_owner_decides_for_opponent_element(rules):
    e = _build(rules, {"hand": ["T1025"], "bz": ["T004"],
                       "mana": ["T009", "T001", "T001", "T001"]},
               {"bz": ["T005"]})
    who = _cast_and_modal(e, "play:T1025", "T005", 1)
    assert who == 1
    assert _deck_defns(e, 1)[-1] == "T005"


def test_t1026_cip_and_put_under(rules):
    e = _build(rules, {"hand": ["T1026"], "bz": ["T057"],
                       "mana": ["T009", "T001", "T001", "T001"]},
               {"bz": ["T005"]})
    played = False
    modal_player = None
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        host = next((c for c in e.bz_tops(0)
                     if e.s.cards[c].defn == "T057"), None)
        if played and host is not None and e.s.cards[host].under:
            break
        if d["kind"] == "main" and d.get("player") == 0 and not played \
                and "play:T1026" in keys:
            e.answer([keys.index("play:T1026")])
            played = True
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "charge" and not played:
            e.answer([keys.index("pass")] if "pass" in keys else [0])
            continue
        if d["kind"] == "choose_cards":
            tgt = "T005" if any("T005" in k for k in keys) else "T057"
            e.answer([_pick(keys, tgt)])
            continue
        if d["kind"] == "choose_mode":
            modal_player = d.get("player")
            e.answer([keys.index("mode:1")])   # 山札の下
            continue
        if d["kind"] == "yes_no":
            e.answer([keys.index("yes")])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    else:
        raise AssertionError("tamaseed CIP did not resolve")
    assert modal_player == 1
    assert _deck_defns(e, 1)[-1] == "T005"
    host = next(c for c in e.bz_tops(0) if e.s.cards[c].defn == "T057")
    under = [e.s.cards[c].defn for c in e.s.cards[host].under]
    assert under == ["T1026"], under


def test_t1027_attack_discard_scales_targets(rules):
    e = _build(rules, {"hand": ["T1027", "T001", "T003"],
                       "mana": ["T009"] + ["T001"] * 6},
               {"bz": ["T005", "T009"]})
    summoned = False
    attacked = False
    modal_players = []
    modal_modes = iter([0, 1])            # 1枚目は上、2枚目は下
    discards = iter(["T001", "T003"])
    targets = iter(["T005", "T009"])
    for _ in range(900):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "choose_shields":
            break                          # 誘発は解決済みのはず
        if d["kind"] == "main" and d.get("player") == 0 and not summoned \
                and "play:T1027" in keys:
            e.answer([keys.index("play:T1027")])
            summoned = True
            continue
        if d["kind"] == "attack" and d.get("player") == 0 and summoned \
                and not attacked and "attack:T1027:player" in keys:
            e.answer([keys.index("attack:T1027:player")])
            attacked = True
            continue
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if d["kind"] == "yes_no" and not attacked:
            e.answer([keys.index("no")])  # 出た時のドローは断る
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
    assert modal_players == [1, 1]         # 置く位置は毎回相手が選ぶ
    # 手札に残るのは第2ターンの開始時に引いたフィラーだけ
    assert [e.s.cards[c].defn for c in e.zlist("hand", 0)] == ["T002"]
    assert [e.s.cards[c].defn for c in e.zlist("graveyard", 0)] == \
        ["T001", "T003"]
    deck = _deck_defns(e, 1)
    assert deck[0] == "T005" and deck[-1] == "T009"
    assert e.bz_tops(1) == []
