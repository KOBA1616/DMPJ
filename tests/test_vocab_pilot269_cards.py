"""語彙パイロット第269弾のカード適用テスト（登録形）。

ラウンド304で s_trigger_x の6件を新規登録、差し戻しなし。
- 登録6件: dm23ex1-066（天装 カガヤキ・ミガタメ。出た時／クロス先の攻撃時に
  タップ＋次相手ターンのはじめにアンタップしない）、dm29-034（装刃
  レオ・インパクト。出た時の無償クロス＋シールド・プラス）、dm15-023
  （クイック・ディフェンス。ブロッカー付与＋クロス先の破壊時に付け替え）、
  dm15-026（マキシマム・ディフェンス。パワー+5000＋ブロッカー＋攻撃不可）、
  dm15-029（パワード・マスク。タップ状態のクリーチャー数ぶんパワー）、
  dm15-032（インフェルノ・シザース。クロス先の攻撃時に合計3000以下を破壊）。
- promoy4-014 は dm15-032 の同名別印刷として aliases に折り畳まれた。
- converted 10,107 / rejects 2,229、重複0・漏れ0。s_trigger_x ギャップは
  残り0件でファミリー解消。cross_free_op は残り7件（他ギャップとの複合）。
"""
import copy
import json
import os
from pathlib import Path

import pytest

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

from dmsim.cards import cardstore

import _conv_cache  # noqa: E402
from dmsim.cards.defs import DATA, load_rules, load_tables, parse_card
from dmsim.scenario import build

TABLES = load_tables()
CONVERTED = cardstore.converted_path(DATA)
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"


def _setup(rules, p0, p1=None):
    # tests.conftest の setup と同形。conftest を import すると
    # DMSIM_SKIP_CONVERTED=1 が復活するため、ここで直接 build を呼ぶ。
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": "T001",
                         "seed": 1, "deck_size": 20})


REGISTERED = ("dm23ex1-066", "dm29-034", "dm15-023",
              "dm15-026", "dm15-029", "dm15-032")


def _converted(cid):
    c = _conv_cache.find(CONVERTED, cid)
    if c is not None:
        return c
    raise KeyError(cid)


def _reject(cid):
    for line in open(REJECTS, encoding="utf-8"):
        r = json.loads(line)
        if r["id"] == cid:
            return r
    raise KeyError(cid)


def _by_defn(e, zone, p):
    if zone == "bz":
        return {e.cdef(c).id: c for c in e.bz_tops(p)}
    return {e.cdef(c).id: c for c in e.zlist(zone, p)}


def _gear(e, defn, p=1):
    return _by_defn(e, "bz", p).get(defn)


def _drive(e, stop, declare=None, attack_keys=None, play=None, limit=1000):
    """ブレイク→S・トリガー宣言→生成→無償クロスまで進めるドライバ。

    attack_keys: {player: 攻撃選択肢}（そのプレイヤーの攻撃ステップで取る。
    無ければ pass）。クリーチャーはタップ状態のものしか攻撃できないため、
    攻撃対象をタップさせる必要がある時は、対象側のターンにも攻撃を入れる。
    play: main で1回出す play フック。
    choose_cards は所有者で区別する: 自分のクリーチャー＝クロス先（T001 が
    いればそれ、なければ付け替え先の T002）、相手のクリーチャー＝タップ先／
    破壊先（T002 がいればそれ）。
    """
    seen = {}
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind in ("charge", "main"):
            if kind == "main" and play is not None:
                ans = play(e, d, seen)
                if ans is not None:
                    e.answer(ans)
                    if stop(e):
                        return
                    continue
            e.answer([keys.index("pass")])
        elif kind == "attack":
            key = (attack_keys or {}).get(e.s.active)
            if key is not None and key in keys:
                e.answer([keys.index(key)])
            else:
                e.answer([keys.index("pass")])
        elif kind == "block":
            e.answer([keys.index("no_block")] if "no_block" in keys
                     else list(range(d.get("min", 0))))
        elif kind == "choose_breaker":
            e.answer([max(range(len(keys)), key=lambda i: int(keys[i].split(":")[1]))])
        elif kind == "choose_shields":
            e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            if declare is None:
                e.answer([])
            else:
                hit = [i for i, k in enumerate(keys) if k == f"strigger:{declare}"]
                assert hit, f"strigger:{declare} not in {keys}"
                e.answer(hit)
        elif kind == "declare_sback":
            e.answer([])
        elif kind == "yes_no":
            e.answer([keys.index("yes")])
        elif kind == "choose_cards":
            # 所有者で区別する: 自分のクリーチャー＝クロス先（T001 がいればそれ、
            # なければ自分の残り＝付け替え先の T002）、相手のクリーチャー＝
            # タップ先／破壊先（T002 がいればそれ）。
            own = [i for i, o in enumerate(d["options"])
                   if e.s.cards[o["cid"]].controller == 1]
            opp = [i for i, o in enumerate(d["options"])
                   if e.s.cards[o["cid"]].controller == 0]
            own_t001 = [i for i in own if e.cdef(d["options"][i]["cid"]).id == "T001"]
            opp_t002 = [i for i in opp if e.cdef(d["options"][i]["cid"]).id == "T002"]
            if own_t001:
                e.answer(own_t001[:1])
            elif own:
                e.answer(own[:1])
            elif opp_t002:
                e.answer(opp_t002[:1])
            elif opp:
                e.answer(opp[:1])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "order_pending":
            e.answer([0])
        elif kind == "pay_mana":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if stop(e):
            return
    raise AssertionError("limit reached")


def _play_key(key, player=0):
    def play(e, d, seen):
        if e.s.active != player or seen.get("opt"):
            return None
        keys = [o["key"] for o in d["options"]]
        if key in keys:
            seen["opt"] = True
            return [keys.index(key)]
        return None
    return play


def _crossed_onto(e, gear_defn, host_defn, host_player=1):
    g = _gear(e, gear_defn, host_player)
    if g is None or e.s.cards[g].crossed is None:
        return False
    host = _by_defn(e, "bz", host_player).get(host_defn)
    return host is not None and list(e.s.cards[g].crossed) == list(e.s.ref(host))


# ---------- 登録形 ----------

def test_registered_forms():
    c = _converted("dm23ex1-066")
    parse_card(copy.deepcopy(c), TABLES)
    assert c["name"] == "天装 カガヤキ・ミガタメ"
    assert c["types"] == ["cross_gear"] and c["civs"] == ["light"]
    assert c["cost"] == 4 and c["races"] == ["エンジェル・コマンド", "アーマード・サムライ"]
    assert c["keywords"] == ["s_trigger_x"]
    assert c["abilities"] == [
        {"kind": "trigger",
         "when": {"event": "move", "to": "bz", "subject": "self"},
         "effect": [{"op": "tap",
                     "select": {"zone": "bz", "owner": "opp",
                                "filter": {"types": ["creature"]}, "count": 1},
                     "no_untap_next": True}]},
        {"kind": "trigger",
         "when": {"event": "attack", "subject": "crossed"},
         "effect": [{"op": "tap",
                     "select": {"zone": "bz", "owner": "opp",
                                "filter": {"types": ["creature"]}, "count": 1},
                     "no_untap_next": True}]}]

    c = _converted("dm29-034")
    parse_card(copy.deepcopy(c), TABLES)
    assert c["name"] == "装刃 レオ・インパクト"
    assert c["keywords"] == ["s_trigger_x"]
    assert c["abilities"][0] == {
        "kind": "trigger",
        "when": {"event": "move", "to": "bz", "subject": "self"},
        "effect": [{"op": "may", "body": [
            {"op": "cross_free", "gear": {"ref": "self"},
             "to": {"zone": "bz", "owner": "you",
                    "filter": {"types": ["creature"]}}}]}]}
    assert c["abilities"][1] == {
        "kind": "trigger",
        "when": {"event": "attack", "subject": "crossed"},
        "effect": [{"op": "may", "body": [{"op": "shield_plus"}]}]}

    c = _converted("dm15-023")
    parse_card(copy.deepcopy(c), TABLES)
    assert c["name"] == "クイック・ディフェンス"
    assert c["keywords"] == ["s_trigger_x"]
    assert c["abilities"][0] == {"kind": "static", "affects": "crossed",
                                 "mod": {"grant": ["blocker"]}}
    assert c["abilities"][1] == {
        "kind": "trigger",
        "when": {"event": "move", "from": "bz", "to": "graveyard",
                 "reason": "destroy", "subject": "crossed"},
        "effect": [{"op": "may", "body": [
            {"op": "cross_free", "gear": {"ref": "self"},
             "to": {"zone": "bz", "owner": "you",
                    "filter": {"types": ["creature"]}}}]}]}

    c = _converted("dm15-026")
    parse_card(copy.deepcopy(c), TABLES)
    assert c["name"] == "マキシマム・ディフェンス"
    assert c["keywords"] == ["s_trigger_x"]
    assert c["abilities"][-1] == {"kind": "static", "affects": "crossed",
                                  "mod": {"power": 5000,
                                          "grant": ["blocker", "cannot_attack"]}}

    c = _converted("dm15-029")
    parse_card(copy.deepcopy(c), TABLES)
    assert c["name"] == "パワード・マスク"
    assert c["keywords"] == ["s_trigger_x"]
    assert c["abilities"][-1] == {
        "kind": "static", "affects": "crossed",
        "mod": {"power": {"amount": 1000,
                          "count": {"zone": "bz", "owner": "any",
                                    "filter": {"types": ["creature"],
                                               "tapped": True}}}}}

    c = _converted("dm15-032")
    parse_card(copy.deepcopy(c), TABLES)
    assert c["name"] == "インフェルノ・シザース"
    assert c["keywords"] == ["s_trigger_x"]
    assert (c.get("source") or {}).get("aliases") == ["promoy4-014"]
    assert c["abilities"][-1] == {
        "kind": "trigger",
        "when": {"event": "attack", "subject": "crossed"},
        "effect": [{"op": "destroy",
                    "select": {"zone": "bz", "owner": "opp",
                               "filter": {"types": ["creature"]},
                               "total_power_le": 3000, "count": "any"}}]}


def test_round304_no_rejects_left():
    """6件とも rejects から消え、s_trigger_x ギャップは残っていない。"""
    for cid in REGISTERED:
        with pytest.raises(KeyError):
            _reject(cid)
    with pytest.raises(KeyError):
        _reject("promoy4-014")
    for line in open(REJECTS, encoding="utf-8"):
        r = json.loads(line)
        assert "s_trigger_x" not in r.get("gaps", [])


# ---------- 実挙動（登録形） ----------

def test_026_strigger_x_cross_grants_power_and_blocker():
    """dm15-026: S・トリガーXで出てクロスすると、ホストは+5000とブロッカーを得る。"""
    e = _setup(load_rules(), {"bz": ["T001"]},
               {"shield": ["dm15-026"], "bz": ["T001"]})
    _drive(e, lambda ev: _crossed_onto(ev, "dm15-026", "T001"),
           declare="dm15-026", attack_keys={0: "attack:T001:player"})
    host = _by_defn(e, "bz", 1)["T001"]
    assert e.chars_ro(host)["power"] == 7000
    assert "blocker" in e.chars_ro(host)["keywords"]
    assert "cannot_attack" in e.chars_ro(host)["keywords"]


def test_029_dynamic_power_counts_tapped():
    """dm15-029: タップ状態のクリーチャー1体（攻撃者）ぶん+1000される。"""
    e = _setup(load_rules(), {"bz": ["T001"]},
               {"shield": ["dm15-029"], "bz": ["T001"]})
    _drive(e, lambda ev: _crossed_onto(ev, "dm15-029", "T001"),
           declare="dm15-029", attack_keys={0: "attack:T001:player"})
    host = _by_defn(e, "bz", 1)["T001"]
    assert e.chars_ro(host)["power"] == 3000   # 2000 + タップ中の攻撃者1体ぶん


def test_066_entry_trigger_taps():
    """dm23ex1-066: S・トリガーXで出た時の誘発で、相手の T002 をタップする。"""
    e = _setup(load_rules(), {"bz": ["T001", "T002"]},
               {"shield": ["dm23ex1-066"], "bz": ["T001"]})

    def stop(ev):
        if not _crossed_onto(ev, "dm23ex1-066", "T001"):
            return False
        tgt = _by_defn(ev, "bz", 0).get("T002")
        return tgt is not None and ev.s.cards[tgt].tapped
    _drive(e, stop, declare="dm23ex1-066", attack_keys={0: "attack:T001:player"})
    tgt = _by_defn(e, "bz", 0)["T002"]
    assert e.s.cards[tgt].tapped


def test_032_attack_destroy_total_power():
    """dm15-032: クロス先が攻撃すると、合計3000以下の相手クリーチャーを破壊する。"""
    e = _setup(load_rules(), {"bz": ["T001", "T002"]},
               {"shield": ["dm15-032"], "bz": ["T001"]})
    _drive(e, lambda ev: _crossed_onto(ev, "dm15-032", "T001"),
           declare="dm15-032", attack_keys={0: "attack:T001:player"})
    # p1 のターン: ホスト T001 でプレイヤーを攻撃し、誘発で T002 を破壊する
    _drive(e, lambda ev: "T002" in _by_defn(ev, "graveyard", 0),
           declare=None, attack_keys={1: "attack:T001:player"})
    assert "T002" in _by_defn(e, "graveyard", 0)


def test_034_entry_cross_free_from_hand():
    """dm29-034: 手札からジェネレートすると、出た時の無償クロスでホストに付く。"""
    e = _setup(load_rules(),
               {"bz": ["T001"]},
               {"hand": ["dm29-034"], "bz": ["T001"],
                "mana": ["T001"] * 4})
    _drive(e, lambda ev: _crossed_onto(ev, "dm29-034", "T001"),
           play=_play_key("play:dm29-034", player=1))
    assert _gear(e, "dm29-034") is not None


def test_023_recross_when_host_destroyed():
    """dm15-023: クロス先がバトルで破壊されると、別の自分のクリーチャーに付け替わる。"""
    e = _setup(load_rules(), {"bz": ["T001"]},
               {"shield": ["dm15-023"], "bz": ["T001", "T002"]})
    _drive(e, lambda ev: _crossed_onto(ev, "dm15-023", "T001"),
           declare="dm15-023", attack_keys={0: "attack:T001:player"})
    # p1 ターン: ホストで攻撃してタップさせる（タップ状態のクリーチャーしか
    # 攻撃できない）。次の p0 ターン: ホスト T001 を攻撃し、バトルで両方破壊され、
    # 付け替え誘発が走る
    _drive(e, lambda ev: _crossed_onto(ev, "dm15-023", "T002"),
           declare=None,
           attack_keys={1: "attack:T001:player", 0: "attack:T001:T001"})
    assert _crossed_onto(e, "dm15-023", "T002")
    assert "T001" in _by_defn(e, "graveyard", 1)   # ホストは破壊された
