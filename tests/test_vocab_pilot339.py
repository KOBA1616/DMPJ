"""語彙パイロット第339弾: opponent_cards_enter_tapped（ドリフト）。

対象（pure 2件）:
- dmrp21-5a グーゴル ＜XENOM.Star＞（相手のカードはマナゾーンと
  バトルゾーンにタップして置かれる）
- dm23ex3-006 偽りの名 スコーピオ（水晶武装4: 自分のマナゾーンに
  裏向きのカードが4枚以上あれば、同じ効果）

確立形は2つの既存機構の組み合わせ:
- バトルゾーン側: static {affects: {zone: bz, owner: opp},
  mod: {grant: [enters_tapped]}}（dmex19-m20「非道」の鬼
  ゴウケン齋型と同型。入るカードの chars に enters_tapped が
  含まれ、events の移動適用でタップして置かれる）
- マナゾーン側: キーワード opp_mana_tapped（相手がマナゾーンに
  置くカードがタップして置かれる。events が持ち主の bz トップの
  chars を見る）。条件付きの場合は static {affects: self,
  if: 条件, mod: {grant: [opp_mana_tapped]}} で自分に条件付きで
  持たせる。

スコーピオのゲートは {cmp: [{count: {zone: mana, owner: you,
filter: {face_down: true}}}, ">=", 4]}（水晶武装4）。

proto: T1028（グーゴル型）/ T1029（スコーピオ型）。

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

CRYSTAL4 = {"cmp": [{"count": {"zone": "mana", "owner": "you",
                               "filter": {"face_down": True}}},
                     ">=", 4]}

FORM_5A = [
    {"kind": "trigger",
     "when": {"event": "attack", "subject": "self"},
     "effect": [{"op": "discard",
                 "select": {"zone": "hand", "owner": "opp",
                            "count": 1}}]},
    {"kind": "static", "affects": {"zone": "bz", "owner": "opp"},
     "mod": {"grant": ["enters_tapped"]}},
]

FORM_006 = [
    {"kind": "trigger",
     "when": {"event": "move", "to": "bz", "subject": "self"},
     "effect": [{"op": "may", "body": [
         {"op": "flip_down",
          "select": {"zone": "mana", "owner": "you", "count": 1}}]}]},
    {"kind": "trigger",
     "when": {"event": "turn_start"},
     "if": {"is_turn": "you"},
     "effect": [{"op": "may", "body": [
         {"op": "flip_down",
          "select": {"zone": "mana", "owner": "you", "count": 1}}]}]},
    {"kind": "static", "affects": {"zone": "bz", "owner": "opp"},
     "if": CRYSTAL4, "mod": {"grant": ["enters_tapped"]}},
    {"kind": "static", "affects": "self",
     "if": CRYSTAL4, "mod": {"grant": ["opp_mana_tapped"]}},
]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    c = proto_card("T1028")
    assert c["abilities"] == FORM_5A
    assert c["keywords"] == ["double_breaker", "opp_mana_tapped"]
    parse_card(c, TABLES)
    c = proto_card("T1029")
    assert c["abilities"] == FORM_006
    parse_card(c, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _keys(d):
    return [o["key"] for o in d["options"]]


def _zone_card(e, zone, p, defn):
    return next(c for c in e.zlist(zone, p)
                if e.s.cards[c].defn == defn)


def _drive(e, plan, limit=900):
    """plan(d, keys) が True を返したら止める汎用ドライバ。
    plan は決定への回答も自分で行う（止める時は回答しない）。"""
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        if plan(d, _keys(d)):
            return d
    raise AssertionError("plan never stopped")


def test_t1028_opponent_cards_enter_tapped(rules):
    e = _build(rules, {"bz": ["T1028"]},
               {"hand": ["T005", "T003"],
                "mana": ["T005", "T001", "T001"]})
    state = {"charged": False, "played": False}

    def plan(d, keys):
        if state["played"] and d["kind"] == "charge" \
                and d.get("player") == 0:
            return True   # 相手のターンが終わる前（アンタップ前）に止める
        if d["kind"] == "charge" and d.get("player") == 1 \
                and not state["charged"] and "charge:T003" in keys:
            e.answer([keys.index("charge:T003")])
            state["charged"] = True
            return False
        if d["kind"] == "main" and d.get("player") == 1 \
                and not state["played"] and "play:T005" in keys:
            e.answer([keys.index("play:T005")])
            state["played"] = True
            return False
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        return False

    _drive(e, plan)
    # チャージしたカードはタップして置かれる
    assert e.s.cards[_zone_card(e, "mana", 1, "T003")].tapped is True
    # 召喚したクリーチャーはタップして出る
    assert e.s.cards[_zone_card(e, "bz", 1, "T005")].tapped is True


def test_t1029_gate_opens_at_four_face_down(rules):
    e = _build(rules, {"bz": ["T1029"],
                       "mana": ["T001", "T001", "T001", "T001"]},
               {"hand": ["T005", "T009", "T003", "T004"],
                "mana": ["T005", "T009", "T001"]})
    mana0 = list(e.zlist("mana", 0))
    for cid in mana0[:3]:
        e.s.cards[cid].face_down = True     # 裏向き3枚（ゲート閉）
    state = {"p1turns": 0, "p0mays": 0, "played2": False}

    def plan(d, keys):
        if d["kind"] == "charge" and d.get("player") == 1:
            state["p1turns"] += 1
            if state["p1turns"] == 1 and "charge:T003" in keys:
                e.answer([keys.index("charge:T003")])
                return False
            if state["p1turns"] == 2 and "charge:T004" in keys:
                e.answer([keys.index("charge:T004")])
                return False
        if d["kind"] == "main" and d.get("player") == 1:
            if state["p1turns"] == 1 and "play:T005" in keys:
                e.answer([keys.index("play:T005")])
                return False
            if state["p1turns"] == 2 and "play:T009" in keys:
                e.answer([keys.index("play:T009")])
                state["played2"] = True
                return False
        if state["played2"] and d["kind"] == "charge" \
                and d.get("player") == 0:
            return True   # 相手のターンが終わる前（アンタップ前）に止める
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            return False
        if d["kind"] == "yes_no" and d.get("player") == 0:
            # ターン開始の裏向き化: 1ターン目は断り、2ターン目は
            # 受けて4枚目を裏向きにする（エンジン経由でキャッシュも
            # 正しく無効化される）
            state["p0mays"] += 1
            e.answer([keys.index("yes" if state["p0mays"] >= 2
                                 else "no")])
            return False
        if d["kind"] == "choose_cards" and d.get("player") == 0:
            # 裏向き化の対象は表向きの4枚目（cid で特定する）
            idx = next(i for i, o in enumerate(d["options"])
                       if o.get("cid") == mana0[3])
            e.answer([idx])
            return False
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
        return False

    _drive(e, plan)
    # ゲートが閉じている間はタップしない
    assert e.s.cards[_zone_card(e, "mana", 1, "T003")].tapped is False
    assert e.s.cards[_zone_card(e, "bz", 1, "T005")].tapped is False
    # ゲートが開いた後はタップして置かれる
    assert e.s.cards[_zone_card(e, "mana", 1, "T004")].tapped is True
    assert e.s.cards[_zone_card(e, "bz", 1, "T009")].tapped is True
