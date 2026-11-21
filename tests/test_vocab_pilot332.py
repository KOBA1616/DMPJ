"""語彙パイロット第332弾: destroyed_during_battle_trigger（pure 2件）。

対象:
- dm24rp4-070 ライラ・理・アイニー: 「バトル中、この
  クリーチャーが破壊された時、相手のシールドを１つブレイク
  してもよい」
- dm22rp2x-026 真価と代価のチェスト: 「自分のクリーチャーが
  バトル中に破壊された時、そのターンの終わりに、その
  クリーチャーを墓地から出す」（シビルカウント2件は partial
  で表現済み）

結論は小さなエンジン拡張: バトルの敗者の move レコードは
もともと battle: True を持っていた（combat.py が刻む）が、
収集レコードへの伝播も when の照合も無かった。本弾で5点:
1. events.py _apply_one の収集レコードへ battle を伝播。
2. events.py _record_for（置換照合側）へも battle を伝播
   （他のフラグと同じく対にする）。
3. events.py の when 照合に battle フラグを追加（blocked 等の
   bool フラグと同じ形）。
4. defs.py Checker.when に battle の bool 検証を追加。
5. schema.py の when プロパティに battle を追加し
   card.schema.json を再生成。

確立形:
- 本人: {kind: trigger, when: {event: move, from: bz,
  to: graveyard, reason: destroy, battle: true,
  subject: self}, effect: [may [break {player: opp, count: 1}]]}
- 見る側: subject を {owner: you, filter} にし、破壊された
  クリーチャーは choose の as で束縛して delayed_trigger の
  effect が vars 経由で参照する（ニンジャ・ストライクの先例。
  delayed の env は event を保持しないため）。ターン終わりの
  帰還は dmex14-090 の delayed_trigger {when: turn_end} 先例。

proto:
- T1008: dm24rp4-070 型。
- T1009: dm22rp2x-026 型。

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

TRIGGER_070 = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy", "battle": True, "subject": "self"},
    "effect": [{"op": "may", "body": [
        {"op": "break", "player": "opp", "count": 1}]}]}

CIVIL_LIGHT = {
    "kind": "static",
    "affects": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}},
    "if": {"cmp": [{"count": {"zone": "bz", "owner": "you",
                              "filter": {"civs": ["light"],
                                         "types": ["creature", "tamaseed"]}}},
                   ">=", 3]},
    "mod": {"grant": ["blocker"]}}

CIVIL_DARK = {
    "kind": "static",
    "affects": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}},
    "if": {"cmp": [{"count": {"zone": "bz", "owner": "you",
                              "filter": {"civs": ["darkness"],
                                         "types": ["creature", "tamaseed"]}}},
                   ">=", 3]},
    "mod": {"grant": ["slayer"]}}

RETURN_TRIGGER = {
    "kind": "trigger",
    "when": {"event": "move", "from": "bz", "to": "graveyard",
             "reason": "destroy", "battle": True,
             "subject": {"owner": "you",
                         "filter": {"types": ["creature"]}}},
    "effect": [
        {"op": "choose", "select": {"ref": "event.subject"},
         "as": "dead"},
        {"op": "delayed_trigger", "when": {"event": "turn_end"},
         "effect": [{"op": "move", "select": {"ref": "dead"},
                     "to": "bz", "reason": "summon"}]}]}


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


def test_proto_forms():
    c = proto_card("T1008")
    assert c["abilities"] == [TRIGGER_070]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = proto_card("T1009")
    assert c["abilities"] == [CIVIL_LIGHT, CIVIL_DARK, RETURN_TRIGGER]
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3


def test_bad_battle_flag_rejected():
    base = proto_card("T1008")
    bad = dict(base)
    w = dict(TRIGGER_070["when"], battle="yes")
    bad["abilities"] = [dict(TRIGGER_070, when=w)]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def _attack_and_block(e, attacker, blocker="T1004"):
    """attacker でプレイヤーを攻撃し、blocker にブロックさせる。
    バトル解決後の最初の落ち着いた決定まで進める。"""
    t = _bz(e, 0, attacker)
    e.s.cards[t].entered_turn = -1
    blocked = False
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 \
                and f"attack:{attacker}:player" in keys:
            e.answer([keys.index(f"attack:{attacker}:player")])
            continue
        if d["kind"] == "block":
            pick = next((k for k in keys if blocker in k), None)
            assert pick is not None, keys
            e.answer([keys.index(pick)])
            blocked = True
            continue
        if blocked and d["kind"] in ("yes_no", "charge", "main", "attack"):
            return d
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("battle did not resolve")


def _answer_yes(e, d):
    keys = _keys(d)
    yes = next((k for k in keys if k.endswith(":yes")), keys[0])
    e.answer([keys.index(yes)])


def _drive_to_next_turn(e, player=1):
    for _ in range(400):
        d = e.advance()
        assert d is not None, "game ended"
        if d["kind"] == "charge" and d.get("player") == player:
            return
        keys = _keys(d)
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("turn did not change")


def test_battle_destroy_breaks_shield(rules):
    e = _build(rules, {"bz": ["T1008"]}, {"bz": ["T1004"]})
    shields_before = len(e.zlist("shield", 1))
    d = _attack_and_block(e, "T1008")
    assert _in_zone(e, 0, "graveyard", "T1008")
    assert d["kind"] == "yes_no"           # ブレイクしてもよい
    _answer_yes(e, d)
    _drive_to_next_turn(e)
    assert len(e.zlist("shield", 1)) == shields_before - 1


def test_spell_destroy_no_trigger(rules):
    e = _build(rules, {"bz": ["T1008"], "hand": ["T1003"],
                       "mana": ["T053"]}, {})
    shields_before = len(e.zlist("shield", 1))
    cast = False
    saw_yes_no = False
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and not cast \
                and "play:T1003" in keys:
            e.answer([keys.index("play:T1003")])
            cast = True
            continue
        if d["kind"] == "yes_no":
            saw_yes_no = True
        if cast and d["kind"] == "charge" and d.get("player") == 1:
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert cast and _in_zone(e, 0, "graveyard", "T1008")
    assert not saw_yes_no                  # バトルでなければ誘発しない
    assert len(e.zlist("shield", 1)) == shields_before


def test_delayed_return_at_turn_end(rules):
    e = _build(rules, {"bz": ["T1009", "T001"]}, {"bz": ["T1004"]})
    t = _bz(e, 0, "T001")
    e.s.cards[t].entered_turn = -1
    attacked = False
    blocked = False
    for _ in range(400):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "attack" and d.get("player") == 0 and not attacked \
                and "attack:T001:player" in keys:
            e.answer([keys.index("attack:T001:player")])
            attacked = True
            continue
        if d["kind"] == "block":
            pick = next((k for k in keys if "T1004" in k), None)
            assert pick is not None, keys
            e.answer([keys.index(pick)])
            blocked = True
            continue
        if blocked and d["kind"] == "charge" and d.get("player") == 1:
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert attacked and blocked
    # ターンの終わりに墓地から戻っている。攻撃したクリーチャーは
    # タップしたまま残るはずで、アンタップで場にあるのは
    # 「破壊されて墓地から戻った」証拠になる（破壊と帰還は
    # 同じ前進チェーンの中で起き、墓地の状態は決定点では
    # 観測できないため、タップ状態で区別する）。
    t1 = _bz(e, 0, "T001")
    assert not e.s.cards[t1].tapped
    assert not _in_zone(e, 0, "graveyard", "T001")


def test_no_return_when_destroyed_by_spell(rules):
    e = _build(rules, {"bz": ["T1009", "T001"], "hand": ["T1003"],
                       "mana": ["T053"]}, {})
    cast = False
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and not cast \
                and "play:T1003" in keys:
            e.answer([keys.index("play:T1003")])
            cast = True
            continue
        if cast and d["kind"] == "charge" and d.get("player") == 1:
            break
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert cast and _in_zone(e, 0, "graveyard", "T001")
    assert not _in_zone(e, 0, "bz", "T001")   # 戻らない


def test_civil_count_grants(rules):
    e = _build(rules, {"bz": ["T1009", "T001", "T004", "T004"]}, {})
    kw = e.chars(_bz(e, 0, "T001"))["keywords"]
    assert "blocker" in kw                  # 光3つ（T1009＋T004×2）
    assert "slayer" not in kw               # 闇は T1009 の1つだけ
    e = _build(rules, {"bz": ["T1009", "T001"]}, {})
    kw = e.chars(_bz(e, 0, "T001"))["keywords"]
    assert "blocker" not in kw and "slayer" not in kw
