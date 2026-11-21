"""語彙パイロット第333弾: power_transfer（pure 2件）。

対象:
- dm24rp4-045 ブルーアイズ・ドラゴンフライ: 「自分のコスト６
  以上のクリーチャーが出た時、次の自分のターンのはじめまで、
  そのクリーチャーのパワーをこのクリーチャーのパワーに加える」
- dmrp11-zs01 零: 「このクリーチャーが攻撃する時、相手の
  クリーチャーを１体選ぶ。そのターン、そのパワーをこの
  クリーチャーに追加し、選んだクリーチャーのパワーを０にする」
  （＋自分のターン終わりの相手の手札破棄＋零龍がいる間の闇の
  コスト軽減）

結論はエンジン拡張（power mod の amount に式を許可）:
power mod の辞書形 {amount, count} は amount が整数のみだった。
本弾で amount に {power_of: {ref: 名前}}（と {var: 名前}）を
許可した（第324弾の breaks_add {var:} と同じ発想）。op_modify
の _bake_refs が生成時にリテラルへ固定するため、chars は
従来どおり整数だけを見る。常在型に直接書くと chars が整数を
前提とするため使えない（生成時ベイク専用。defs.py に注記）。
schema.py の power の amount も anyOf [integer, object] にし、
card.schema.json を再生成。

確立形:
- dm24rp4-045: trigger {when: {event: move, to: bz,
  subject: {owner: you, filter: {types: [creature], cost_ge: 6}}},
  effect: [modify {select: {ref: event.subject},
  mod: {power: {amount: {power_of: {ref: self}}}},
  duration: until_next_own_turn_start}]}
- dmrp11-zs01: 攻撃時 trigger で choose {as: victim} し、
  modify self {power: {amount: {power_of: {ref: victim}}}}
  （end_of_turn の既定）→ modify victim {power_set: 0}。
  順序が大事（先に吸い上げてから 0 にする）。ターン終わりの
  手札破棄は discard {chooser: opp} の確立形。零龍がいる間の
  コスト軽減は static {affects: {zone: hand, owner: you,
  filter: {civs: [darkness]}}, if: {exists: {race_has: 零龍}},
  mod: {cost: -1, cost_min: 0}}（「自分の零龍」は《》が無い
  ため種族参照。by_product に種族・名前に零龍を持つカードは
  無く、駆動用に T1012 を用意した）。常在型の発生源は場の零
  自身なので、手札の零自身のコストは軽減されない（場に出て
  から他の闇カードに効く）。

proto:
- T1010: dm24rp4-045 型。
- T1011: dmrp11-zs01 型。
- T1012: 駆動用（種族 零龍）。

ドライバは tests.conftest を import せず scenario.build を直接
使う（第329弾以降の作法）。
"""
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

TRIGGER_045 = {
    "kind": "trigger",
    "when": {"event": "move", "to": "bz",
             "subject": {"owner": "you",
                         "filter": {"types": ["creature"],
                                    "cost_ge": 6}}},
    "effect": [{"op": "modify", "select": {"ref": "event.subject"},
                "mod": {"power": {"amount": {"power_of": {"ref": "self"}}}},
                "duration": "until_next_own_turn_start"}]}

TRANSFER = {
    "kind": "trigger", "when": {"event": "attack", "subject": "self"},
    "effect": [
        {"op": "choose",
         "select": {"zone": "bz", "owner": "opp",
                    "filter": {"types": ["creature"]}, "count": 1},
         "as": "victim"},
        {"op": "modify", "select": {"ref": "self"},
         "mod": {"power": {"amount": {"power_of": {"ref": "victim"}}}},
         "duration": "end_of_turn"},
        {"op": "modify", "select": {"ref": "victim"},
         "mod": {"power_set": 0}, "duration": "end_of_turn"}]}

END_DISCARD = {
    "kind": "trigger", "when": {"event": "turn_end"},
    "if": {"is_turn": "you"},
    "effect": [{"op": "discard",
                "select": {"zone": "hand", "owner": "opp",
                           "chooser": "opp", "count": 1}}]}

COST_CUT = {
    "kind": "static",
    "affects": {"zone": "hand", "owner": "you",
                "filter": {"civs": ["darkness"]}},
    "if": {"exists": {"zone": "bz", "owner": "you",
                      "filter": {"race_has": "零龍"}}},
    "mod": {"cost": -1, "cost_min": 0}}


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


def _drive_to(e, kind, player):
    for _ in range(400):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] == kind and d.get("player") == player:
            return d
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError(f"did not reach {kind} p{player}")


def test_proto_forms():
    c = proto_card("T1010")
    assert c["abilities"] == [TRIGGER_045]
    assert c["keywords"] == ["powered_breaker"]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = proto_card("T1011")
    assert c["abilities"] == [TRANSFER, END_DISCARD, COST_CUT]
    assert c["keywords"] == ["powered_breaker"]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3
    parse_card(proto_card("T1012"), TABLES)


def test_bad_power_amount_rejected():
    base = proto_card("T1010")
    for bad_amt in ("1000", 5.5, {"unknown": 1}, {"var": 5}):
        bad = dict(base)
        bad["abilities"] = [{"kind": "trigger",
                             "when": TRIGGER_045["when"],
                             "effect": [{"op": "modify",
                                         "select": {"ref": "event.subject"},
                                         "mod": {"power": {"amount": bad_amt}},
                                         "duration": "until_next_own_turn_start"}]}]
        with pytest.raises(DefError):
            parse_card(bad, TABLES)


def test_dragonfly_transfers_power(rules):
    e = _build(rules, {"bz": ["T1010"], "hand": ["T142"],
                       "mana": ["T001"] * 7}, {})
    played = False
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and "play:T142" in keys:
            e.answer([keys.index("play:T142")])
            played = True
            continue
        if played and d["kind"] in ("charge", "main", "attack"):
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert played and _in_zone(e, 0, "bz", "T142")
    # 13000（T142）＋1000（ドラゴンフライ）で 14000
    assert e.chars(_bz(e, 0, "T142"))["power"] == 14000
    assert e.chars(_bz(e, 0, "T1010"))["power"] == 1000
    # 次の自分のターンのはじめまで: p1 のターンを挟み、p0 の
    # 次のターンのメインで戻る
    _drive_to(e, "main", 0)
    assert e.chars(_bz(e, 0, "T142"))["power"] == 13000


def test_dragonfly_ignores_small_creature(rules):
    e = _build(rules, {"bz": ["T1010"], "hand": ["T001"],
                       "mana": ["T001"] * 2}, {})
    played = False
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and "play:T001" in keys:
            e.answer([keys.index("play:T001")])
            played = True
            continue
        if played and d["kind"] in ("charge", "main", "attack"):
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert played
    assert e.chars(_bz(e, 0, "T001"))["power"] == 2000


def test_zero_drains_and_zeroes(rules):
    e = _build(rules, {"bz": ["T1011"]}, {"bz": ["T004"]})
    t = _bz(e, 0, "T1011")
    e.s.cards[t].entered_turn = -1
    attacked = False
    checked = False
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 and not attacked \
                and "attack:T1011:player" in keys:
            e.answer([keys.index("attack:T1011:player")])
            attacked = True
            continue
        if attacked and not checked:
            # 攻撃の解決の直後（最初の決定の時点）で移転が効いている
            # （選んだクリーチャーはパワー0になり、状況起因処理で
            # 破壊される）
            assert e.chars(_bz(e, 0, "T1011"))["power"] == 8000
            assert _in_zone(e, 1, "graveyard", "T004")
            checked = True
        if attacked and d["kind"] in ("charge", "main", "attack"):
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert attacked and checked
    # 次のターンには戻る（手札が空だと main の決定自体が出ない
    # ため、次の自分の charge で見る）
    _drive_to(e, "charge", 0)
    assert e.chars(_bz(e, 0, "T1011"))["power"] == 5000
    assert _in_zone(e, 1, "graveyard", "T004")


def test_zero_end_discard(rules):
    e = _build(rules, {"bz": ["T1011"]},
               {"hand": ["T001", "T001", "T001"]})
    hand_before = len(e.zlist("hand", 1))
    t001_before = sum(1 for c in e.zlist("hand", 1)
                      if e.s.cards[c].defn == "T001")
    _drive_to(e, "charge", 1)
    # p1 はターン開始に1枚引き、自分のターン終わりに1枚捨てる
    # （T001 が1枚減っている）
    assert len(e.zlist("hand", 1)) == hand_before
    t001_after = sum(1 for c in e.zlist("hand", 1)
                     if e.s.cards[c].defn == "T001")
    assert t001_after == t001_before - 1


def test_zero_cost_cut_needs_zero_dragon(rules):
    """零龍がいる間のコスト軽減。常在型の発生源は場の零自身なので、
    軽減の対象は手札の他の闇カード（零自身のコストは場に出る前
    には軽減されない）。
    """
    # 零龍がいなければ軽減なし: 闇2マナで T053（コスト3）は出せない
    e = _build(rules, {"bz": ["T1011"], "hand": ["T053"],
                       "mana": ["T053"] * 2}, {})
    opts = [o["key"] for o in e._play_options(0)]
    assert "play:T053" not in opts
    # 零龍がいればコスト1減: T053 が2マナで出せる
    e = _build(rules, {"bz": ["T1011", "T1012"], "hand": ["T053"],
                       "mana": ["T053"] * 2}, {})
    opts = [o["key"] for o in e._play_options(0)]
    assert "play:T053" in opts
    # コスト1の闇カードは0になる: T1003（コスト1）をマナ無しで
    e = _build(rules, {"bz": ["T1011", "T1012"], "hand": ["T1003"]}, {})
    opts = [o["key"] for o in e._play_options(0)]
    assert "play:T1003" in opts
