"""語彙パイロット第331弾: name_addition（pure 2件）。

対象:
- dm23ex1-039 ボルメテウス・剣誠・ドラゴン: 「バトルゾーンに
  ある間、このクリーチャーは名前に《ボルメテウス・武者・
  ドラゴン》を追加する」
- dm28-008 竜装 ムシャ・レジェンド（クロスギア）: 「これを
  クロスしたクリーチャーは…名前に《ボルメテウス・武者・
  ドラゴン》を追加する」（partial は add_races と power を
  既に持ち、add_names だけが欠けていた）

結論はドリフト（文書化）: mod の add_names はエンジン実装済み
（バンドC2 U97。core.py の chars 集約で主名を変えず名前の集合
names に足し、filter の name は追加の名前にも当たる）だが、
converted.yaml の使用例が0件だったため rejects に残っていた。
本弾で確立形として固定する:
- 本人: {kind: static, affects: self, mod: {add_names: [名前]}}
- クロスギア: partial の affects: crossed の mod に
  add_names を足す（power / add_races と同居できる）

dm23ex1-039 の残りも既存語彙で足りる: G・ゼロは top-level の
free_if（dm23ex1-075 等。条件は all＋cmp(count race_has)＋
not exists(name)）、攻撃時誘発は may＋destroy power_le の
確立形。

proto:
- T1005: dm23ex1-039 型（G・ゼロ＋攻撃時誘発＋add_names）。
- T1006: dm28-008 型（クロスギア）。
- T1007: 駆動用（追加された名前で名指し破壊する呪文）。

ドライバは tests.conftest を import せず scenario.build を直接
使う（第329弾以降の作法。conftest は DMSIM_SKIP_CONVERTED を
立てる）。クロスは第170弾と同じく状態へ直接紐付ける。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

ADDED = "試験用ボルメテウス・武者・ドラゴン"
OWN = "試験用ボルメテウス・剣誠・ドラゴン"

FREE_IF = {"all": [
    {"cmp": [{"count": {"zone": "bz", "owner": "you",
                        "filter": {"race_has": "サムライ"}}}, ">=", 5]},
    {"not": {"exists": {"zone": "bz", "owner": "you",
                        "filter": {"name": OWN}}}}]}

ATTACK_TRIGGER = {
    "kind": "trigger", "when": {"event": "attack", "subject": "self"},
    "effect": [{"op": "may", "body": [
        {"op": "destroy",
         "select": {"zone": "bz", "owner": "opp",
                    "filter": {"types": ["creature"], "power_le": 6000},
                    "count": 1}}]}]}

ADD_NAME_STATIC = {"kind": "static", "affects": "self",
                   "mod": {"add_names": [ADDED]}}

GEAR_STATIC = {"kind": "static", "affects": "crossed",
               "mod": {"power": 2000,
                       "add_races": ["アーマード・ドラゴン", "サムライ"],
                       "add_names": [ADDED]}}

GEAR_TRIGGER = {
    "kind": "trigger", "when": {"event": "attack", "subject": "crossed"},
    "effect": [{"op": "may", "body": [
        {"op": "move", "select": {"zone": "shield", "owner": "you",
                                  "count": 1},
         "to": "graveyard", "reason": "put", "as": "paid"},
        {"op": "if", "cond": {"exists": {"ref": "paid"}},
         "then": [{"op": "destroy",
                   "select": {"zone": "bz", "owner": "opp",
                              "filter": {"types": ["creature"],
                                         "power_le": 6000},
                              "count": 1}}]}]}]}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _in_zone(e, p, zone, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def _cross(e, gear_defn, host_defn, player=0):
    e.s.cards[_bz(e, player, gear_defn)].crossed = \
        e.s.ref(_bz(e, player, host_defn))


def test_proto_forms():
    c = proto_card("T1005")
    assert c["free_if"] == FREE_IF
    assert c["abilities"] == [ATTACK_TRIGGER, ADD_NAME_STATIC]
    assert c["keywords"] == ["double_breaker"]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 2
    c = proto_card("T1006")
    assert c["abilities"] == [GEAR_STATIC, GEAR_TRIGGER]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 2
    c = proto_card("T1007")
    assert c["spell"][0]["select"]["filter"] == {"name": ADDED}
    parse_card(c, TABLES)


def test_bad_add_names_rejected():
    base = proto_card("T1005")
    for bad_mod in ({"add_names": []}, {"add_names": "名前"},
                    {"add_names": [5]}):
        bad = dict(base)
        bad["abilities"] = [ATTACK_TRIGGER,
                            {"kind": "static", "affects": "self",
                             "mod": bad_mod}]
        with pytest.raises(DefError):
            parse_card(bad, TABLES)


def test_added_name_in_chars(rules):
    e = _build(rules, {"bz": ["T1005", "T341"]}, {})
    names = e.chars(_bz(e, 0, "T1005"))["names"]
    assert OWN in names and ADDED in names
    names341 = e.chars(_bz(e, 0, "T341"))["names"]
    assert ADDED not in names341 and len(names341) == 1


def test_name_destroy_hits_added_name(rules):
    e = _build(rules, {"hand": ["T1007"], "mana": ["T005", "T001"]},
               {"bz": ["T1005", "T341"]})
    cast = False
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and "play:T1007" in keys:
            e.answer([keys.index("play:T1007")])
            cast = True
            continue
        if cast and d["kind"] in ("charge", "main", "attack"):
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert cast
    # 名指しは追加された名前でのみ当たり、T341 には当たらない
    assert _in_zone(e, 1, "graveyard", "T1005")
    assert _in_zone(e, 1, "bz", "T341")


def test_crossed_gear_adds_name_power_races(rules):
    e = _build(rules, {"bz": ["T001", "T1006"], "hand": ["T1007"],
                       "mana": ["T005", "T001"]},
               {"bz": ["T341"]})
    _cross(e, "T1006", "T001")
    ch = e.chars(_bz(e, 0, "T001"))
    assert ADDED in ch["names"]
    assert ch["power"] == 4000
    assert "アーマード・ドラゴン" in ch["races"]
    assert "サムライ" in ch["races"]
    # 追加された名前で相手の名指し破壊にも当たる
    e2 = _build(rules, {"bz": ["T001", "T1006"]},
                {"hand": ["T1007"], "mana": ["T005", "T001"]})
    _cross(e2, "T1006", "T001")
    cast = False
    for _ in range(200):
        d = e2.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 1 \
                and "play:T1007" in keys:
            e2.answer([keys.index("play:T1007")])
            cast = True
            continue
        if cast and d["kind"] in ("charge", "main", "attack"):
            break
        if "pass" in keys:
            e2.answer([keys.index("pass")])
        else:
            e2.answer(list(range(d["min"])))
    assert cast
    assert _in_zone(e2, 0, "graveyard", "T001")


def test_g_zero_free_if(rules):
    five = ["T341", "T341", "T342", "T342", "T352"]
    e = _build(rules, {"bz": five, "hand": ["T1005"]}, {})
    assert "play:T1005:free" in [o["key"] for o in e._play_options(0)]
    # 自分の同名が既にいれば無料にならない（5体目が T1005 自身）
    e = _build(rules, {"bz": ["T341", "T341", "T342", "T342", "T1005"],
                       "hand": ["T1005"]}, {})
    assert "play:T1005:free" not in [o["key"] for o in e._play_options(0)]
    # サムライ4体では足りない
    e = _build(rules, {"bz": five[:4], "hand": ["T1005"]}, {})
    assert "play:T1005:free" not in [o["key"] for o in e._play_options(0)]


def test_attack_trigger_may_destroy(rules):
    e = _build(rules, {"bz": ["T1005"]}, {"bz": ["T001"]})
    t = _bz(e, 0, "T1005")
    e.s.cards[t].entered_turn = -1
    attacked = False
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 \
                and "attack:T1005:player" in keys:
            e.answer([keys.index("attack:T1005:player")])
            attacked = True
            continue
        if attacked and _in_zone(e, 1, "graveyard", "T001"):
            return
        if d["kind"] == "yes_no":
            yes = next((k for k in keys if k.endswith(":yes")), keys[0])
            e.answer([keys.index(yes)])
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("attack trigger did not destroy T001")
