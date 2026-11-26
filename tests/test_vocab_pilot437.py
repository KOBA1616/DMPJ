"""語彙パイロット第437弾: shield_faceup_trigger（ドリフト）。

センサス（rejects 1,895件を取り直し）: pure 1,747件
（983家族）/ multi 130件 / 空 gaps 18件。pure の大半は
範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。評価済み却下（第316〜320・
355〜436弾）は原則として再提案しない。残置群
（graveyard_replacement 残り dm25ex2-cho021、
battle_opponent_reference 残り dmr01-049、
untap_restriction 残り2件、does_not_untap 残り
dm25ex2-031、cast_limit_once_per_turn の multi 2件、
summoning_attack_rule 残り dmex07-s01、
entered_turn_attack 残り dmbd11-d05、madness 残り
dmx26-028、after_battle_trigger 残り dmrp09-074、
s_trigger_suppression 2件＝第435弾で専用ステージ
送り確定、次点の destroyed_this_turn_condition /
count_cards_drawn_this_turn、後続候補の
distinct_civ_count、将来の新規語彙候補 first_time_tap /
turn_history_entry / played_free_condition、専用
ステージ送りの power_threshold_keyword_gain）は
覆す根拠が無く再提案しない。

範囲内・最小の **shield_faceup_trigger（pure 1件、
multi にも現れない）** を選定した。本ファミリーは
第436弾で「表向きシールドのブレイク照合が未検証」
として見送られたが、未検証であって不可能と証明
されたわけではなく、本弾の実測で照合経路がすべて
既存の確立部品であることが判明したため、その評価を
覆して着手する（第435・436弾と同型）。対象は
dmd11-006 大焔団 フォルクス（火 / コスト7 /
パワー7000 / 種族 アウトレイジMAX / mana 1）。
partial は骨格＋keywords 完備で text も公式全文。
**補完あり: abilities**（partial に未構築）。

結論はドリフト（追加語彙・エンジン・defs・スキーマ
変更なし）:

- 「自分の、表向きのシールドがブレイクされた時」は
  trigger {when: {event: move, from: shield,
  reason: break, subject: {owner: you},
  face_up: true}}。シールド離脱の監視は登録済み
  dm23rp3-017 / dm23rp1-1a / dmrp21-4a の
  when {event: move, from: shield, subject:
  {owner: you}} の確立形。離れたシールドが表向き
  だったかは、第176弾でシールドを離れる move
  レコードに face_up: true が載るようになっており
  （「表向きで離れた時」誘発を when の face_up で
  書けることが第176弾の設計意図）、_match_when の
  face_up 照合はレコードを見る。ブレイクによる
  離脱は combat.py の h_break が move に付ける
  reason: break で、効果による回収（reason:
  return）や墓地送りと区別できる。
- 効果は destroy {select: {zone: bz, owner: opp,
  filter: {types: [creature], power_le: 6000},
  count: 1}} の標準形（parse で move
  （to: graveyard, reason: destroy）に正規化）。

proto T1227（dmd11-006 型）。判別役は T001
（パワー2000＝破壊対象になる攻撃役）/ T1225
（パワー9000＝power_le: 6000 の対象外）/ T061
（シールド回収呪文＝reason: return の非ブレイク
離脱）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接使う（第319弾以降の
作法）。
"""
import copy
import os
from pathlib import Path

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import (  # noqa: E402
    DefError, load_rules, load_tables, parse_card)
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()
ROOT = Path(__file__).parent.parent

TRIG = {"kind": "trigger",
        "when": {"event": "move", "from": "shield", "reason": "break",
                 "subject": {"owner": "you"}, "face_up": True},
        "effect": [{"op": "destroy",
                    "select": {"zone": "bz", "owner": "opp",
                               "filter": {"types": ["creature"],
                                          "power_le": 6000},
                               "count": 1}}]}
FORM = [TRIG]
FULL_TEXT = ("スピードアタッカー（このクリーチャーは召喚酔いしない）"
             "W・ブレイカー（このクリーチャーはシールドを２枚ブレイクする）"
             "自分の、表向きのシールドがブレイクされた時、"
             "相手のパワー6000以下のクリーチャーを１体破壊する。")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _keys(d):
    return [o.get("key") for o in d["options"]]


def _drive(e, want=None, limit=400, seen=None):
    """want(kind, keys, d) -> 答えるキーの文字列 or None。
    それ以外は pass / no_block / 最小限で流す。"""
    for _ in range(limit):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if seen is not None:
            seen.append((d["kind"], d.get("player"), list(keys)))
        if want is not None:
            k = want(d["kind"], keys, d)
            if k is not None:
                e.answer([keys.index(k)])
                continue
        if d["kind"] in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return e


def _cid(e, defn, player, zone):
    return next(c for c in e.zlist(zone, player)
                if e.s.cards[c].defn == defn)


def _make_face_up(e, defn, player=0):
    cid = _cid(e, defn, player, "shield")
    e.s.cards[cid].face_up = True
    return cid


def _attack_break(e, attacker_defn, break_cid):
    """p1 の attacker_defn でプレイヤーを攻撃し、break_cid の
    シールドをブレイクする。破壊対象の選択肢が出たら
    攻撃役自身（p1 の T001）を選ぶ。"""
    state = {"destroy_offered": False}

    def want(kind, keys, d):
        if kind == "attack" and d.get("player") == 1 \
                and f"attack:{attacker_defn}:player" in keys:
            return f"attack:{attacker_defn}:player"
        if kind == "choose_breaker":
            return max(keys, key=lambda k: int(k.split(":")[1]))
        if kind == "choose_cards":
            hit = [o.get("key") for o in d["options"]
                   if o.get("cid") is not None
                   and e.s.cards[o["cid"]].controller == 1
                   and e.s.cards[o["cid"]].defn == "T001"]
            if hit:
                state["destroy_offered"] = True
                return hit[0]
        return None

    # choose_shields は want 内で answer するため、専用ドライバを使う
    for _ in range(400):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if d["kind"] == "choose_shields":
            hit = [i for i, o in enumerate(d["options"])
                   if o.get("cid") == break_cid]
            rest = [i for i in range(len(keys)) if i not in hit]
            e.answer((hit + rest)[:d["min"]])
            continue
        k = want(d["kind"], keys, d)
        if k:
            e.answer([keys.index(k)])
            continue
        if d["kind"] in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return state


def test_proto_form(rules):
    card = proto_card("T1227")
    assert card["abilities"] == FORM
    assert card["text"] == FULL_TEXT
    assert card["keywords"] == ["speed_attacker", "double_breaker"]
    parsed = parse_card(card, TABLES)
    assert parsed.abilities[0] == {"kind": "static", "affects": "self",
                                   "mod": {"allow": ["attack_summoning_sick"]},
                                   "keyword": "speed_attacker"}
    assert parsed.abilities[1] == {"kind": "static", "affects": "self",
                                   "mod": {"breaks": 2},
                                   "keyword": "double_breaker"}
    trig = parsed.abilities[2]
    assert trig["when"] == {"event": "move", "from": "shield",
                            "reason": "break",
                            "subject": {"owner": "you"}, "face_up": True}
    assert trig["effect"] == [
        {"op": "move",
         "select": {"zone": "bz", "owner": "opp",
                    "filter": {"types": ["creature"], "power_le": 6000},
                    "count": 1},
         "to": "graveyard", "reason": "destroy"}]


def test_form_def_errors():
    base = {"id": "X437", "name": "x", "types": ["creature"],
            "civs": ["fire"], "cost": 7, "power": 7000,
            "races": ["テスト"], "mana": 1, "text": "x",
            "keywords": ["speed_attacker", "double_breaker"],
            "abilities": copy.deepcopy(FORM)}
    parse_card(copy.deepcopy(base), TABLES)
    bad = copy.deepcopy(base)
    bad["abilities"][0]["when"] = {"event": "movezz", "from": "shield",
                                   "reason": "break",
                                   "subject": {"owner": "you"},
                                   "face_up": True}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad = copy.deepcopy(base)
    bad["abilities"][0]["when"]["reason"] = "breakzz"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad = copy.deepcopy(base)
    bad["abilities"][0]["effect"] = [{"op": "explode"}]
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad = copy.deepcopy(base)
    bad["abilities"][0]["effect"][0]["select"]["filter"]["power_le"] = "6000"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def test_faceup_shield_break_destroys_attacker(rules):
    """表向きシールドがブレイクされた時、攻撃役（パワー2000）を破壊する。

    破壊対象の候補が1体だけだと選択決定は自動化されて
    提示されないため、判別用にもう1体（T004）置く。"""
    e = scenario.build(rules, {
        "p0": {"bz": ["T1227"], "shield": ["T002", "T001", "T001"]},
        "p1": {"bz": ["T001", "T004"]},
        "filler": "T002"})
    up = _make_face_up(e, "T002", 0)
    atk = _cid(e, "T001", 1, "bz")
    other = _cid(e, "T004", 1, "bz")
    state = _attack_break(e, "T001", up)
    assert state["destroy_offered"], "破壊対象の選択が提示されなかった"
    assert e.s.cards[atk].zone == "graveyard"
    assert e.s.cards[other].zone == "bz"  # 選ばなかった方は残る
    assert e.s.cards[up].zone == "hand"  # ブレイクされたシールドは手札へ
    assert e.s.cards[_cid(e, "T1227", 0, "bz")].zone == "bz"  # 発生源は残る


def test_facedown_shield_break_no_trigger(rules):
    """裏向きシールドのブレイクでは誘発しない（攻撃役は残る）。"""
    e = scenario.build(rules, {
        "p0": {"bz": ["T1227"], "shield": ["T002", "T001", "T001"]},
        "p1": {"bz": ["T001"]},
        "filler": "T002"})
    down = _cid(e, "T002", 0, "shield")
    assert e.s.cards[down].face_up is False
    atk = _cid(e, "T001", 1, "bz")
    state = _attack_break(e, "T001", down)
    assert not state["destroy_offered"]
    assert e.s.cards[atk].zone == "bz"
    assert e.s.cards[down].zone == "hand"


def test_faceup_shield_returned_no_trigger(rules):
    """表向きシールドが効果で手札に戻る（reason: return）では誘発しない。"""
    e = scenario.build(rules, {
        "p0": {"bz": ["T1227"], "hand": ["T061"], "mana": ["T001"],
               "shield": ["T002", "T001", "T001"]},
        "p1": {"bz": ["T001"]},
        "filler": "T002"})
    up = _make_face_up(e, "T002", 0)
    atk = _cid(e, "T001", 1, "bz")
    # シールド選択肢の key はすべて 'shield' で重複するため index で答える
    for _ in range(400):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if d["kind"] == "main" and "play:T061" in keys:
            e.answer([keys.index("play:T061")])
            continue
        if d["kind"] == "choose_cards":
            hit = [i for i, o in enumerate(d["options"])
                   if o.get("cid") == up]
            e.answer(hit[:1] if hit else list(range(d["min"])))
            continue
        if d["kind"] in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert e.s.cards[up].zone == "hand"  # 回収された
    assert e.s.cards[atk].zone == "bz"   # 破壊されていない


def test_opponent_faceup_shield_break_no_trigger(rules):
    """相手の表向きシールドをブレイクしても誘発しない（subject owner: you）。"""
    e = scenario.build(rules, {
        "p0": {"bz": ["T1227", "T001"]},
        "p1": {"bz": ["T001"], "shield": ["T002", "T001", "T001"]},
        "filler": "T002"})
    up = _make_face_up(e, "T002", 1)
    theirs = _cid(e, "T001", 1, "bz")

    def want(kind, keys, d):
        if kind == "attack" and d.get("player") == 0 \
                and "attack:T001:player" in keys:
            return "attack:T001:player"
        return None

    for _ in range(400):
        d = e.advance()
        if d is None:
            break
        keys = _keys(d)
        if d["kind"] == "choose_shields":
            hit = [i for i, o in enumerate(d["options"])
                   if o.get("cid") == up]
            rest = [i for i in range(len(keys)) if i not in hit]
            e.answer((hit + rest)[:d["min"]])
            continue
        k = want(d["kind"], keys, d)
        if k:
            e.answer([keys.index(k)])
            continue
        if d["kind"] in ("declare_strigger", "declare_sback"):
            e.answer([])
        elif "no_block" in keys:
            e.answer([keys.index("no_block")])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert e.s.cards[up].zone == "hand"      # ブレイク自体は成立
    assert e.s.cards[theirs].zone == "bz"    # 誘発せず相手クリーチャーは残る


def test_power_over_6000_not_destroyed(rules):
    """パワー9000の攻撃役は power_le: 6000 の対象外（誘発しても破壊できない）。"""
    e = scenario.build(rules, {
        "p0": {"bz": ["T1227"], "shield": ["T002", "T001", "T001"]},
        "p1": {"bz": ["T1225"]},
        "filler": "T002"})
    up = _make_face_up(e, "T002", 0)
    big = _cid(e, "T1225", 1, "bz")
    _attack_break(e, "T1225", up)
    assert e.s.cards[up].zone == "hand"   # ブレイクは成立
    assert e.s.cards[big].zone == "bz"    # 対象外なので残る


def test_no_source_no_trigger(rules):
    """発生源が場に無ければ、表向きシールドがブレイクされても何も起きない。"""
    e = scenario.build(rules, {
        "p0": {"shield": ["T002", "T001", "T001"]},
        "p1": {"bz": ["T001"]},
        "filler": "T002"})
    up = _make_face_up(e, "T002", 0)
    atk = _cid(e, "T001", 1, "bz")
    state = _attack_break(e, "T001", up)
    assert not state["destroy_offered"]
    assert e.s.cards[atk].zone == "bz"
    assert e.s.cards[up].zone == "hand"
