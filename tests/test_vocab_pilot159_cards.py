"""語彙パイロット第159弾: first_attack_of_turn の対象19件の検証（再変換ラウンド195で登録）。

登録形は rejects の partial に ord 照合の誘発を足し、unsupported から
first_attack_of_turn を外したもの（submit が split のキーワード等を統合した形）。
差し戻した dm26sd1-m001 は第160弾で解け、ラウンド196で登録された（登録形で検証）。

変換の型:
- 煽動型14件: when {event: attack, subject: {owner: you, filter: {types: [creature]}},
  ord: {kind: attack, eq: 1}}
- 自分型2件（dmr20-005 / dmrp03-s06）: when {event: attack, subject: self,
  ord: {kind: attack_by, eq: 1}} ＋ if 条件。dmrp03-s06 は連結表記で split が
  効かなかったキーワード（スピードアタッカー／W・ブレイカー）と
  パワーアタッカー+1000000（static の power_when）も補う。
- 全体型1件（dmsp01-036）: subject owner: any ＋ ord {kind: attack, eq: 1}、
  効果は modify の breaks_add を duration: during_attack でその攻撃だけに与える。
- 相手型1件（dmr14-003）: 2条項とも書く。ターン開始の「可能であれば攻撃する」は
  dmrp15-006 と同型（modify の require: [attack]、end_of_turn）。初回攻撃の条項は
  subject owner: opp ＋ ord {kind: attack, eq: 1}、出したファンキー・ナイトメアは
  delayed_trigger（turn_end）で破壊する。
- 差し戻し1件（dm26sd1-m001）: マッハファイター付与（第139弾の常在形）と
  ターン終わりの墓地／マナからの出し（modal でゾーンを選ぶ）まで書き、
  「相手のクリーチャーがはじめて攻撃するなら、可能ならこのクリーチャーを攻撃する」
  だけを unsupported（need: first_attack_taunt）に残す。must_be_attacked は
  攻撃側の通し番号で条件づけられないため、エンジン拡張が別途要る。
"""
import copy
import _conv_cache  # noqa: E402
import json
from pathlib import Path

import yaml

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()
REJECTS = Path(__file__).parent.parent / "data" / "cards" / "raw" / "rejects.jsonl"
CONVERTED = Path(__file__).parent.parent / "data" / "cards" / "converted.yaml"

ATK_YOU = {"event": "attack", "subject": {"owner": "you", "filter": {"types": ["creature"]}},
           "ord": {"kind": "attack", "eq": 1}}
ATK_SELF_FIRST = {"event": "attack", "subject": "self", "ord": {"kind": "attack_by", "eq": 1}}


def _trig(when, effect, **kw):
    t = {"kind": "trigger", "when": when, "effect": effect}
    t.update(kw)
    return t


CASES = {
    "dmr19-028": [_trig(ATK_YOU, [
        {"op": "tap", "select": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}, "count": 1},
         "no_untap_next": True}])],
    "dmr19-033": [_trig(ATK_YOU, [
        {"op": "modify", "select": {"ref": "event.subject"}, "mod": {"grant": ["unblockable"]},
         "duration": "end_of_turn"}])],
    "dmr19-042": [_trig(ATK_YOU, [
        {"op": "destroy", "select": {"zone": "bz", "owner": "opp",
                                     "filter": {"types": ["creature"], "power_le": 3000}, "count": 1}}])],
    "dmr19-047": [_trig(ATK_YOU, [
        {"op": "modify", "select": {"ref": "event.subject"}, "mod": {"power": 5000, "breaks_add": 1},
         "duration": "end_of_turn"}])],
    "dmr19-062": [_trig(ATK_YOU, [
        {"op": "may", "body": [{"op": "draw", "count": 1}]}])],
    "dmr19-071": [_trig(ATK_YOU, [
        {"op": "modify", "select": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"]}, "count": 1},
         "mod": {"grant": ["slayer"]}, "duration": "end_of_turn"}])],
    "dmr19-076": [_trig(ATK_YOU, [
        {"op": "may", "body": [
            {"op": "discard", "select": {"zone": "hand", "owner": "you", "count": 1}},
            {"op": "draw", "count": 2}]}])],
    "dmr19-084": [_trig(ATK_YOU, [
        {"op": "may", "body": [
            {"op": "move", "select": {"zone": "deck", "owner": "you", "from_top": 1},
             "to": "mana", "reason": "put"}]}])],
    "dmr20-037": [_trig(ATK_YOU, [
        {"op": "destroy", "select": {"zone": "bz", "owner": "opp",
                                     "filter": {"types": ["creature"], "keyword": "blocker"}, "count": 1}}])],
    "dmr20-042": [_trig(ATK_YOU, [
        {"op": "may", "body": [
            {"op": "choose", "select": {"zone": "deck", "owner": "you", "from_top": 1, "look": True, "count": 1},
             "as": "t"},
            {"op": "if", "cond": {"exists": {"ref": "t", "filter": {"types": ["creature"]}}},
             "then": [{"op": "move", "select": {"ref": "t", "count": "all"}, "to": "hand", "reason": "draw"}],
             "else": [{"op": "mana_put", "select": {"ref": "t", "count": "all"}}]}]}])],
    "dmr20-044": [_trig(ATK_YOU, [
        {"op": "modify", "select": {"ref": "event.subject"}, "mod": {"power": 2000},
         "duration": "end_of_turn"}])],
    "dmr20-049": [_trig(ATK_YOU, [
        {"op": "choose", "select": {"zone": "shield", "owner": "any", "count": 1, "look": True},
         "as": "seen"}])],
    "dmr20-055": [_trig(ATK_YOU, [
        {"op": "discard", "select": {"zone": "hand", "owner": "opp", "chooser": "opp", "count": 1}}])],
    "dmr20-069": [_trig(ATK_YOU, [
        {"op": "modify", "select": {"ref": "event.subject"}, "mod": {"power": 3000},
         "duration": "end_of_turn"}])],
    "dmr20-005": [_trig(ATK_SELF_FIRST, [
        {"op": "untap", "select": {"ref": "self"}}],
        **{"if": {"cmp": [{"count": {"zone": "bz", "owner": "you", "filter": {"types": ["creature"]}}},
                          ">=", {"count": {"zone": "shield", "owner": "you"}}]}})],
    "dmsp01-036": [_trig(
        {"event": "attack", "subject": {"owner": "any", "filter": {"types": ["creature"]}},
         "ord": {"kind": "attack", "eq": 1}},
        [{"op": "modify", "select": {"ref": "event.subject"}, "mod": {"breaks_add": 1},
          "duration": "during_attack"}])],
    "dmr14-003": [
        _trig({"event": "turn_start", "player": "opp"}, [
            {"op": "modify", "select": {"zone": "bz", "owner": "opp", "filter": {"types": ["creature"]}, "count": 1},
             "mod": {"require": ["attack"]}, "duration": "end_of_turn"}]),
        _trig({"event": "attack", "subject": {"owner": "opp", "filter": {"types": ["creature"]}},
               "ord": {"kind": "attack", "eq": 1}}, [
            {"op": "may", "body": [
                {"op": "move", "select": {"zone": "hand", "owner": "you",
                                          "filter": {"types": ["creature"], "race_has": "ファンキー・ナイトメア",
                                                     "cost_le": 6, "evolution": False}, "count": 1},
                 "to": "bz", "reason": "put", "as": "fn"},
                {"op": "delayed_trigger", "when": {"event": "turn_end"},
                 "effect": [{"op": "destroy", "select": {"ref": "fn"}}]}]}]),
    ],
}

# dmrp03-s06: 誘発に加えてキーワードとパワーアタッカーの常在型を補う
S06_TRIGGER = _trig(ATK_SELF_FIRST, [
    {"op": "untap", "select": {"ref": "self"}}],
    **{"if": {"cmp": [{"sum": [
        {"count": {"zone": "bz", "owner": "you", "filter": {"race_has": "ジョーカーズ"}}},
        {"count": {"zone": "mana", "owner": "you", "filter": {"race_has": "ジョーカーズ"}}}]},
        ">=", 4]}})
S06_ADD = {
    "keywords": ["speed_attacker", "double_breaker"],
    "abilities": [
        {"kind": "static", "affects": "self",
         "mod": {"power_when": {"amount": 1000000, "when": "attacking"}}},
        S06_TRIGGER,
    ],
}

# dm26sd1-m001: ここまで書いて first_attack_taunt だけ unsupported に残す（差し戻し）
M001_ADD = [
    {"kind": "static", "affects": {"zone": "bz", "owner": "you",
                                   "filter": {"types": ["creature"], "race_has": "アビス"}},
     "mod": {"allow": [{"action": "attack_creature", "other": {"tapped": False}}]}},
    _trig({"event": "turn_end", "player": "you"}, [
        {"op": "may", "body": [
            {"op": "modal", "count": 1, "modes": [
                [{"op": "move", "select": {"zone": "graveyard", "owner": "you",
                                           "filter": {"types": ["creature"], "race_has": "アビス", "cost_le": 6},
                                           "count": 1}, "to": "bz", "reason": "put"}],
                [{"op": "move", "select": {"zone": "mana", "owner": "you",
                                           "filter": {"types": ["creature"], "race_has": "アビス", "cost_le": 6},
                                           "count": 1}, "to": "bz", "reason": "put"}]]}]}]),
]
M001_UNSUPPORTED = [{"need": "first_attack_taunt",
                     "text": "各ターン、相手のクリーチャーがはじめて攻撃するなら、可能ならこのクリーチャーを攻撃する"}]


def _added(cid):
    if cid == "dmrp03-s06":
        return S06_ADD["abilities"]
    if cid == "dm26sd1-m001":
        return M001_ADD
    return CASES[cid]


def test_all_targets_registered():
    data = {"cards": _conv_cache.all_cards(CONVERTED)}
    registered = {c["id"]: c for c in data["cards"] if c["id"] in CASES or c["id"] == "dmrp03-s06"}
    expect = set(CASES) | {"dmrp03-s06"}
    assert set(registered) == expect, f"converted に無い対象: {expect - set(registered)}"
    for cid in expect:
        card = copy.deepcopy(registered[cid])
        assert not (card.get("source") or {}).get("unsupported"), f"{cid}: unsupported が残る"
        for ab in _added(cid):
            assert ab in (card.get("abilities") or []), f"{cid}: 誘発が登録形と違う"
        if cid == "dmrp03-s06":
            for kw in S06_ADD["keywords"]:
                assert kw in (card.get("keywords") or []), f"{cid}: キーワード {kw} が無い"
        parsed = parse_card(card, TABLES)
        whens = [a.get("when") or {} for a in parsed.abilities if a["kind"] == "trigger"]
        assert any("ord" in w for w in whens), f"{cid}: ord 誘発が無い"


def test_m001_registered_in_round196():
    """dm26sd1-m001 は第160弾（must_be_attacked の first_only 形）で解け、ラウンド196で登録された。"""
    rows = [json.loads(line) for line in open(REJECTS, encoding="utf-8")]
    assert all(r["id"] != "dm26sd1-m001" for r in rows), "m001 が rejects に残っている"
    data = {"cards": _conv_cache.all_cards(CONVERTED)}
    card = next(c for c in data["cards"] if c["id"] == "dm26sd1-m001")
    assert not (card.get("source") or {}).get("unsupported")
    for ab in M001_ADD:
        assert ab in (card.get("abilities") or []), "m001: ラウンド195までの変換が登録形に残っていない"
    taunt = {"kind": "static", "affects": "self", "mod": {"must_be_attacked": {"first_only": True}}}
    assert taunt in (card.get("abilities") or []), "m001: 第160弾の誘引が無い"
    parse_card(card, TABLES)
