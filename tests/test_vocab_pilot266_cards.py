"""語彙パイロット第266弾のカード適用テスト（登録形）。

ラウンド301で exile_doron_go の4件を新規登録、差し戻しなし。
- 登録4件: dm22ex1-021（神聖牙 US パンク。出た時・他のクリーチャー任意数
  破壊→同数ドロー→手札からエグザイルを出す／ウルトラ・ドロン・ゴー
  《神》／制限《神》）、dm22ex1-080（神豚 ブータンPUNK / ブータン両成敗。
  ツインパクト。ウルトラ・ドロン・ゴー《神豚》／制限《神》／呪文面は相手が
  選んで破壊した後、自分も1体破壊）、dm22ex1-090（友情の カツドン。
  ウルトラ・ドロン・ゴー（名前制限なし）／制限《友情の カツドン》）、
  dm22ex1-cho22（チーム・エグザイル。ウルトラ・ドロン・ゴー（名前制限
  なし）。無視能力は制限側の常在型の if で表すため自身の def には書かない）。
- dmx22b-014 は dm22ex1-cho22 の同名別版として aliases に折り畳まれた。
- converted 10,094 / rejects 2,243、重複0・漏れ0。
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

IGNORE_IF = {"not": {"exists": {"zone": ["hand", "bz"], "owner": "you",
                                "filter": {"name_has": "チーム・エグザイル"}}}}


def _setup(rules, p0, p1=None):
    # tests.conftest の setup と同形。conftest を import すると
    # DMSIM_SKIP_CONVERTED=1 が復活するため、ここで直接 build を呼ぶ。
    return build(rules, {"p0": p0, "p1": p1 or {}, "filler": "T001",
                         "seed": 1, "deck_size": 20})


REGISTERED = ("dm22ex1-021", "dm22ex1-080", "dm22ex1-090", "dm22ex1-cho22")


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


def _triggers(card, event=None):
    return [ab for ab in card.get("abilities") or []
            if ab.get("kind") == "trigger"
            and (event is None or ab["when"].get("event") == event)]


def _statics(card):
    return [ab for ab in card.get("abilities") or []
            if ab.get("kind") == "static"]


def _restriction_statics(card, name_has):
    """出場制限の常在型5つ（T734 型）。"""
    out = []
    for ab in _statics(card):
        if ab.get("mod") != {"deny": ["enter_bz"]}:
            continue
        aff = ab.get("affects") or {}
        if aff.get("filter") == {"types": ["exile_creature"],
                                 "name_has": name_has}:
            assert aff.get("owner") == "you"
            assert ab.get("if") == IGNORE_IF
            out.append(ab)
    return out


def _ultra_trigger(card, name_has=None):
    trig = [ab for ab in _triggers(card, "move")
            if ab["when"] == {"event": "move", "from": "bz",
                              "subject": "self"}]
    assert len(trig) == 1
    may = trig[0]["effect"][0]
    assert may["op"] == "may"
    mv = may["body"][0]
    assert mv["op"] == "move" and mv["to"] == "bz" \
        and mv["reason"] == "put"
    filt = {"types": ["exile_creature"]}
    if name_has is not None:
        filt["name_has"] = name_has
    assert mv["select"] == {"zone": "hand", "owner": "you",
                            "filter": filt, "count": 1}
    return trig[0]


def _drive(e, stop, choose=None, play=None, attack_with=None, attacker=0,
           limit=800):
    for _ in range(limit):
        d = e.advance()
        assert d is not None, "game ended"
        kind = d["kind"]
        keys = [o["key"] for o in d["options"]]
        if kind == "choose_evo_source":
            e.answer([0])
            if stop(e):
                return
            continue
        if kind == "choose_cards" and choose is not None:
            ans = choose(e, d)
            if ans is not None:
                e.answer(ans)
                if stop(e):
                    return
                continue
        if kind == "main" and play is not None:
            ans = play(e, d)
            if ans is not None:
                e.answer(ans)
                if stop(e):
                    return
                continue
        if kind == "attack" and attack_with is not None \
                and e.s.active == attacker:
            hit = next((i for i, k in enumerate(keys)
                        if k.startswith(f"attack:{attack_with}:")), None)
            if hit is not None:
                e.answer([hit])
                if stop(e):
                    return
                continue
        if kind == "block":
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "pay_mana":
            e.answer([0])
        elif kind == "yes_no":
            e.answer([0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
        if stop(e):
            return
    raise AssertionError("limit reached")


def _in_zone(e, zone, p, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist(zone, p))


def _count_zone(e, zone, p, defn):
    return sum(1 for c in e.zlist(zone, p)
               if e.s.cards[c].defn == defn)


def _play(defn, seen, max_n=1, player=0):
    def play(e, d):
        if e.s.active != player:
            return None
        keys = [o["key"] for o in d["options"]]
        if f"play:{defn}" in keys and seen["n"] < max_n:
            seen["n"] += 1
            return [keys.index(f"play:{defn}")]
        return None
    return play


def _play_key(key, seen, player=0):
    def play(e, d):
        if e.s.active != player:
            return None
        keys = [o["key"] for o in d["options"]]
        if key in keys and not seen.get("opt"):
            seen["opt"] = True
            return [keys.index(key)]
        return None
    return play


def _pick_defn(defn, max_n=None):
    """choose_cards で defn のカードを選ぶ（最大 max_n 枚、既定は決定の max）。"""
    def choose(e, d):
        idx = [i for i, o in enumerate(d["options"])
               if e.s.cards[o["cid"]].defn == defn]
        assert idx, f"選択対象の {defn} が候補に無い"
        n = max_n if max_n is not None else d.get("max", len(idx))
        return idx[:n]
    return choose


def _play_keys(e, p=0):
    return [o["key"] for o in e._play_options(p)]


def test_registered_forms():
    for cid in REGISTERED:
        card = _converted(cid)
        parse_card(copy.deepcopy(card), TABLES)
        assert (card.get("source") or {}).get("official") == cid
    for cid in ("dm22ex1-021", "dm22ex1-090", "dm22ex1-cho22"):
        assert "exile_creature" in _converted(cid)["types"]
    assert _converted("dm22ex1-080")["faces"][0]["types"] == [
        "creature", "exile_creature"]


def test_round301_specific_forms():
    c = _converted("dm22ex1-021")
    assert c["keywords"] == ["g_strike", "blocker", "triple_breaker"]
    assert (c.get("source") or {}).get("aliases") is None
    trig = _triggers(c, "move")
    assert len(trig) == 2
    cip = trig[0]
    assert cip["when"] == {"event": "move", "to": "bz", "subject": "self"}
    assert cip["effect"][0] == {
        "op": "destroy",
        "select": {"zone": "bz", "owner": "you",
                   "filter": {"types": ["creature"]},
                   "other": True, "count": "any"},
        "as": "k"}
    assert cip["effect"][1] == {"op": "draw",
                                "count": {"count": {"ref": "k"}}}
    assert cip["effect"][2] == {
        "op": "move",
        "select": {"zone": "hand", "owner": "you",
                   "filter": {"types": ["exile_creature"]}, "count": 1},
        "to": "bz", "reason": "put"}
    _ultra_trigger(c, "神")
    assert sorted(ab["affects"]["zone"]
                  for ab in _restriction_statics(c, "神")) == [
        "deck", "graveyard", "hand", "mana", "shield"]

    c = _converted("dm22ex1-080")
    assert (c.get("source") or {}).get("aliases") is None
    face = c["faces"][0]
    assert face["types"] == ["creature", "exile_creature"]
    assert face["civs"] == ["zero"] and face["cost"] == 3
    assert face["power"] == 4000
    assert face["races"] == ["アウトレイジMAX", "オラクル"]
    _ultra_trigger(face, "神豚")
    assert sorted(ab["affects"]["zone"]
                  for ab in _restriction_statics(face, "神")) == [
        "deck", "graveyard", "hand", "mana", "shield"]
    spell = c["faces"][1]
    assert spell["types"] == ["spell"] and spell["civs"] == ["darkness"]
    assert spell["cost"] == 3
    assert spell["keywords"] == ["s_trigger"]
    assert spell["spell"][0] == {
        "op": "destroy",
        "select": {"zone": "bz", "owner": "opp", "chooser": "opp",
                   "filter": {"types": ["creature"]}, "count": 1}}
    assert spell["spell"][1] == {
        "op": "destroy",
        "select": {"zone": "bz", "owner": "you",
                   "filter": {"types": ["creature"]}, "count": 1}}
    assert c["mana"] == 1

    c = _converted("dm22ex1-090")
    assert c["keywords"] == ["speed_attacker"]
    assert (c.get("source") or {}).get("aliases") is None
    _ultra_trigger(c)
    assert sorted(ab["affects"]["zone"]
                  for ab in _restriction_statics(c, "友情の カツドン")) == [
        "deck", "graveyard", "hand", "mana", "shield"]

    c = _converted("dm22ex1-cho22")
    assert c["keywords"] == ["triple_breaker"]
    assert c["cost"] == 999 and c["power"] == 17000
    assert (c.get("source") or {}).get("aliases") == ["dmx22b-014"]
    _ultra_trigger(c)
    assert _restriction_statics(c, "チーム・エグザイル") == []
    assert [ab for ab in _statics(c)
            if ab.get("mod") == {"deny": ["enter_bz"]}] == []
    assert len(_triggers(c, "move")) == 1


def test_dmx22b_014_alias_level_stale():
    """dmx22b-014 は dm22ex1-cho22 の aliases に折り畳まれたため、
    rejects には存在しない（alias-level stale 行は残らない）。"""
    c = _converted("dm22ex1-cho22")
    assert "dmx22b-014" in (c.get("source") or {}).get("aliases", [])
    with pytest.raises(KeyError):
        _reject("dmx22b-014")


def test_021_cip_destroys_draws_puts():
    """dm22ex1-021: 出た時、他のクリーチャー2体を破壊し、2枚引いて、
    手札からエグザイル（T739）を出す。手札枚数は元に戻る。
    （021 は無色コスト11のため、マナは無色の T423 を11枚使う。火マナでは
    文明が合わず play 選択肢が出ない）"""
    e = _setup(load_rules(),
               {"bz": ["T001", "T001"], "hand": ["dm22ex1-021", "T739"],
                "mana": ["T423"] * 11},
               {"bz": []})
    h0 = len(e.zlist("hand", 0))
    seen = {"n": 0}

    def choose(e, d):
        idx = [i for i, o in enumerate(d["options"])
               if e.s.cards[o["cid"]].defn == "T001"]
        if idx:
            return idx
        return list(range(d.get("min", 0)))

    _drive(e, lambda e: _in_zone(e, "bz", 0, "T739")
           and _count_zone(e, "graveyard", 0, "T001") == 2,
           choose=choose, play=_play("dm22ex1-021", seen))
    assert seen["n"] == 1
    assert _in_zone(e, "bz", 0, "dm22ex1-021")
    assert len(e.zlist("hand", 0)) == h0


def test_021_cip_cannot_put_restricted():
    """dm22ex1-021: CIP で手札の《神》エグザイル（T735）は出せない。
    自身の制限が場に出た瞬間から働くため、破壊→ドローまでは進み、
    T735 は手札に残る。"""
    e = _setup(load_rules(),
               {"bz": ["T001"], "hand": ["dm22ex1-021", "T735"],
                "mana": ["T423"] * 11},
               {"bz": []})
    h0 = len(e.zlist("hand", 0))
    seen = {"n": 0}

    def choose(e, d):
        idx = [i for i, o in enumerate(d["options"])
               if e.s.cards[o["cid"]].defn == "T001"]
        if idx:
            return idx
        return list(range(d.get("min", 0)))

    _drive(e, lambda e: _in_zone(e, "bz", 0, "dm22ex1-021")
           and _count_zone(e, "graveyard", 0, "T001") == 1
           and len(e.zlist("hand", 0)) == h0,
           choose=choose, play=_play("dm22ex1-021", seen))
    assert seen["n"] == 1
    assert _in_zone(e, "hand", 0, "T735")
    assert len(e.zlist("hand", 0)) == h0


def test_021_restriction_blocks_summon():
    """dm22ex1-021 が場にいる間、名前に《神》とある T735 は召喚できない。
    名前の違うエグザイル（T739）は出せる。"""
    e = _setup(load_rules(),
               {"bz": ["dm22ex1-021"], "hand": ["T735", "T739"],
                "mana": ["T005"] * 3}, {})
    keys = _play_keys(e)
    assert "play:T735" not in keys
    assert "play:T739" in keys


def test_021_ultra_puts_on_destroy():
    """dm22ex1-021: 破壊で離れた時、may で手札の《神》エグザイル（T735）を出す。
    021 自身は墓地へ。T739 は名前に《神》が無いので対象にならない。"""
    e = _setup(load_rules(),
               {"bz": ["dm22ex1-021"], "hand": ["T011", "T735"],
                "mana": ["T005"] * 3}, {})
    seen = {"n": 0}
    _drive(e, lambda e: _in_zone(e, "bz", 0, "T735"),
           choose=_pick_defn("dm22ex1-021", max_n=1),
           play=_play("T011", seen))
    assert seen["n"] == 1
    assert _in_zone(e, "graveyard", 0, "dm22ex1-021")
    assert "T735" not in [e.s.cards[c].defn for c in e.zlist("hand", 0)]


def test_080_spell_face_destroys_both():
    """dm22ex1-080 呪文面：相手が自身のクリーチャー1体を選んで破壊し、
    その後、自分のクリーチャー1体を破壊する。"""
    e = _setup(load_rules(),
               {"bz": ["T001"], "hand": ["dm22ex1-080"],
                "mana": ["T008"] * 3},
               {"bz": ["T001"]})
    seen = {}
    _drive(e, lambda e: _count_zone(e, "graveyard", 0, "T001") == 1
           and _count_zone(e, "graveyard", 1, "T001") == 1,
           choose=_pick_defn("T001", max_n=1),
           play=_play_key("play:dm22ex1-080:1", seen))
    assert seen.get("opt")
    assert _in_zone(e, "graveyard", 0, "dm22ex1-080")


def test_080_ultra_puts_on_destroy():
    """dm22ex1-080: 破壊で離れた時、may で手札の2枚目の 080 を出す。
    1枚目が離れた後は制限が解ける。"""
    e = _setup(load_rules(),
               {"bz": ["dm22ex1-080"], "hand": ["T011", "dm22ex1-080"],
                "mana": ["T005"] * 3}, {})
    seen = {"n": 0}
    _drive(e, lambda e: _count_zone(e, "bz", 0, "dm22ex1-080") == 1
           and _count_zone(e, "graveyard", 0, "dm22ex1-080") == 1,
           choose=_pick_defn("dm22ex1-080", max_n=1),
           play=_play("T011", seen))
    assert seen["n"] == 1


def test_090_ultra_puts_any_exile():
    """dm22ex1-090: 破壊で離れた時、may で手札のエグザイル（T739）を出す。
    名前制限がない。"""
    e = _setup(load_rules(),
               {"bz": ["dm22ex1-090"], "hand": ["T011", "T739"],
                "mana": ["T005"] * 3}, {})
    seen = {"n": 0}
    _drive(e, lambda e: _in_zone(e, "bz", 0, "T739"),
           choose=_pick_defn("dm22ex1-090", max_n=1),
           play=_play("T011", seen))
    assert seen["n"] == 1
    assert _in_zone(e, "graveyard", 0, "dm22ex1-090")


def test_090_restriction_blocks_same_name():
    """dm22ex1-090 が場にいる間、もう1枚の 090 は出せない。
    名前の違うエグザイル（T739）は出せる。"""
    e = _setup(load_rules(),
               {"bz": ["dm22ex1-090"], "hand": ["dm22ex1-090", "T739"],
                "mana": ["T005"] * 5}, {})
    keys = _play_keys(e)
    assert "play:dm22ex1-090" not in keys
    assert "play:T739" in keys


def test_cho22_ultra_puts_on_destroy():
    """dm22ex1-cho22: 破壊で離れた時、may で手札のエグザイル（T739）を出す。"""
    e = _setup(load_rules(),
               {"bz": ["dm22ex1-cho22"], "hand": ["T011", "T739"],
                "mana": ["T005"] * 3}, {})
    seen = {"n": 0}
    _drive(e, lambda e: _in_zone(e, "bz", 0, "T739"),
           choose=_pick_defn("dm22ex1-cho22", max_n=1),
           play=_play("T011", seen))
    assert seen["n"] == 1
    assert _in_zone(e, "graveyard", 0, "dm22ex1-cho22")


def test_cho22_ignore_from_hand():
    """チーム・エグザイルが手札にある時、021 の制限は働かない。
    T735 を召喚できる。"""
    e = _setup(load_rules(),
               {"bz": ["dm22ex1-021"],
                "hand": ["T735", "dm22ex1-cho22"],
                "mana": ["T005"] * 3}, {})
    assert "play:T735" in _play_keys(e)


def test_cho22_ignore_from_bz():
    """チーム・エグザイルがバトルゾーンにある時も、021 の制限は働かない。"""
    e = _setup(load_rules(),
               {"bz": ["dm22ex1-021", "dm22ex1-cho22"], "hand": ["T735"],
                "mana": ["T005"] * 3}, {})
    assert "play:T735" in _play_keys(e)
