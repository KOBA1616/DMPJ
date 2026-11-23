"""語彙パイロット第336弾: break_limit（ブレイク数の上限）。

対象（pure 3件）:
- dm29-001 光神龍ラル・アブゾーバー（相手のクリーチャーは攻撃
  1回につきシールドを1枚しかブレイクできない）
- dm16-008 インパクト・アブソーバー（どのクリーチャーにも
  クロスされていない時、クリーチャーは攻撃1回につき1枚しか
  ブレイクできない。両プレイヤー対象）
- dm26rp1-039 我竜塔最高層 ローズ・キャッスル（表向きの
  シールドゾーンから、相手のクリーチャーは最大1つしか
  ブレイクできない）

新 mod breaks_max（エンジン拡張）: chars の集約で、breaks の
max 合成と breaks_add の適用の後に、breaks と break_opts の
各値を上限で切り取る。複数あれば最小を採る。発生源は通常の
常在型（bz から・シールドゾーンから・ギアの if 条件つき）で
よいため、対象のスコープは affects と if で表せる。

proto: T1018（ラル型）/ T1019（ギア型）/ T1020（城型）。

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

STATIC_001 = [{
    "kind": "static",
    "affects": {"owner": "opp", "filter": {"types": ["creature"]}},
    "mod": {"breaks_max": 1},
}]

ABIL_008 = [
    {"kind": "replace",
     "when": {"event": "move", "from": "bz", "to": "graveyard",
              "reason": "destroy", "subject": "crossed"},
     "instead": [{"op": "move", "select": {"ref": "crossed"},
                  "to": "shield", "reason": "put"}]},
    {"kind": "static",
     "affects": {"owner": "any", "filter": {"types": ["creature"]}},
     "if": {"not": {"exists": {"ref": "self",
                               "filter": {"crossed": True}}}},
     "mod": {"breaks_max": 1}},
]

TRIG_039 = [
    {"kind": "trigger", "zone": "shield", "if": {"face_up": True},
     "when": {"event": "battle_start",
              "subject": {"owner": "you",
                          "filter": {"types": ["creature"]}}},
     "effect": [{"op": "modify", "select": {"ref": "event.opponent"},
                 "mod": {"power": -4000}, "duration": "during_attack"}]},
    {"kind": "trigger", "zone": "shield", "if": {"face_up": True},
     "when": {"event": "battle_start",
              "opponent": {"owner": "you",
                           "filter": {"types": ["creature"]}}},
     "effect": [{"op": "modify", "select": {"ref": "event.subject"},
                 "mod": {"power": -4000}, "duration": "during_attack"}]},
]

ABIL_039 = TRIG_039 + [{
    "kind": "static", "zone": "shield", "if": {"face_up": True},
    "affects": {"owner": "opp", "filter": {"types": ["creature"]}},
    "mod": {"breaks_max": 1},
}]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_forms(rules):
    c = proto_card("T1018")
    assert c["abilities"] == STATIC_001
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 1
    c = proto_card("T1019")
    assert c["abilities"] == ABIL_008
    d = parse_card(c, TABLES)
    assert len(d.abilities) == 2
    c = proto_card("T1020")
    assert c["abilities"] == ABIL_039
    d = parse_card(c, TABLES)
    assert len(d.abilities) >= 3


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _cid(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _breaks(e, p, defn):
    return e.chars(_cid(e, p, defn))["breaks"]


def test_breaks_control(rules):
    e = _build(rules, {"bz": ["T1014"]}, {})
    assert _breaks(e, 0, "T1014") == 3      # トリプル・ブレイカー素の値


def test_ral_caps_opponent_only(rules):
    e = _build(rules, {"bz": ["T1014"]}, {"bz": ["T1018", "T1014"]})
    assert _breaks(e, 0, "T1014") == 1      # 相手のラルで上限1
    assert _breaks(e, 1, "T1014") == 3      # 自分のクリーチャーは対象外


def test_castle_caps_from_shield(rules):
    e = _build(rules, {"bz": ["T1014"]}, {"shield": ["T1020"]})
    cid = next(c for c in e.zlist("shield", 1)
               if e.s.cards[c].defn == "T1020")
    assert _breaks(e, 0, "T1014") == 3      # 裏向きでは働かない
    e.s.cards[cid].face_up = True
    assert _breaks(e, 0, "T1014") == 1      # 表向きで上限1


def test_gear_caps_all_until_crossed(rules):
    e = _build(rules, {"bz": ["T1019", "T1014"]}, {"bz": ["T1014"]})
    assert _breaks(e, 0, "T1014") == 1      # 未クロス: 両者とも上限1
    assert _breaks(e, 1, "T1014") == 1
    gear = _cid(e, 0, "T1019")
    host = _cid(e, 0, "T1014")
    e.s.cards[gear].crossed = e.s.ref(host)  # クロスした状態にする
    assert _breaks(e, 0, "T1014") == 3      # クロスされると上限は消える
    assert _breaks(e, 1, "T1014") == 3


def _attack_player(e, attacker_defn):
    """attacker でプレイヤーを攻撃し、choose_shields の (min, max) と
    解決後の相手シールド枚数を返す。"""
    before = len(e.zlist("shield", 1))
    seen = {}
    for _ in range(600):
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_shields":
            seen["minmax"] = (d["min"], d["max"])
            e.answer(list(range(d["min"])))
            # 解決を次の決定まで進める
            for _ in range(60):
                d2 = e.advance()
                if d2 is None or d2["kind"] in ("charge", "main",
                                                "attack"):
                    break
                k2 = [o["key"] for o in d2["options"]]
                if d2["kind"] == "declare_strigger":
                    e.answer([])
                elif "pass" in k2:
                    e.answer([k2.index("pass")])
                else:
                    e.answer(list(range(d2["min"])))
            return seen["minmax"], len(e.zlist("shield", 1))
        if d["kind"] == "attack" and d.get("player") == 0 \
                and f"attack:{attacker_defn}:player" in keys:
            e.answer([keys.index(f"attack:{attacker_defn}:player")])
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
    raise AssertionError("attack did not reach choose_shields")


def test_attack_breaks_one_with_ral(rules):
    e = _build(rules, {"bz": ["T1014"]}, {"bz": ["T1018"]})
    assert len(e.zlist("shield", 1)) == 5
    mm, after = _attack_player(e, "T1014")
    assert mm == (1, 1)                      # 選べるのは1枚だけ
    assert after == 4                        # 実際に1枚だけ割れる


def test_attack_breaks_three_without_ral(rules):
    e = _build(rules, {"bz": ["T1014"]}, {})
    mm, after = _attack_player(e, "T1014")
    assert mm == (3, 3)
    assert after == 2
