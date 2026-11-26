"""語彙パイロット第358弾: destroy_after_attacking_on_entry_turn
（ドリフト）。

センサス（rejects 1,975件を取り直し）: pure 1,827件 /
multi 148件。pure の大半は範囲外（gr_summon 147 /
aura 108＝未承認 / hyperdimensional_zone 105 / dragheart 45 /
psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。残りは pure 1〜4件の小家族が多数で、
評価済み却下（第316〜320・355〜357弾: negate_effects /
opponent_choice_branch / shield_grant /
cost_matching_selection / per_civilization_selection /
flying / delayed_return / draw_up_to / look_reorder /
does_not_untap / フィールド系 / unblocked_creature_attack /
has_ability_filter / mana_tap_trigger / attack_end_trigger /
must_attack_next_turn 系）は再提案しない。範囲内・未評価で
最小の destroy_after_attacking_on_entry_turn（pure 1件、
multi にも現れない）を選定した:
dm22rp1-039 落下男「相手のクリーチャーが、出たターンに
攻撃する時、その攻撃の後、そのクリーチャーを破壊する」。
partial は骨格（keywords [slayer] のみ）で、未解決は
unsupported の本 gap 1件だけ。

結論はドリフト（追加語彙なし）。部品はすべて確立済み:
- 攻撃誘発の第三者観測形 {event: attack, subject:
  {owner: opp, filter}} は dm30-041 / dm24rp1-066 の
  登録先例があり、filter に第134弾の
  entered_this_turn: true（「このターン中に出た」）を重ねる。
- 「その攻撃の後」は第319弾形A／第355弾の delayed_trigger
  {when: {event: attack_end, subject: 同形},
  duration: during_attack}。during_attack のため、この
  攻撃の attack_end だけに一致し別の攻撃へ漏れない。
- 破壊対象は発火レコードの event.subject（attack_end の
  subject は攻撃したクリーチャー自身。第355弾が
  event.target を使ったのと対の参照）。

proto T1076（落下男型）/ T1077（パワー3000アタッカー、
スピードアタッカー付き。出たターンに攻撃するには召喚酔いの
回避が要り、落下男の条項が現実に狙うのも SA 等で出た
ターンに攻撃するクリーチャー）/
T1078（パワー1000ブロッカー）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接包む（第319弾以降の作法）。
実挙動テストでは「出たターン」の再現に、対象クリーチャーの
entered_turn を現在のターンへ合わせる（第134弾の
filter_match テストと同じ操作。フィルタ自体の意味論は
第134弾で固定済みで、本弾は誘発→遅延→破壊の連鎖を見る）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

_OPP_NEW = {"owner": "opp", "filter": {"entered_this_turn": True}}
TRIGGER = {"kind": "trigger",
           "when": {"event": "attack", "subject": _OPP_NEW},
           "effect": [{"op": "delayed_trigger",
                       "when": {"event": "attack_end",
                                "subject": _OPP_NEW},
                       "duration": "during_attack",
                       "effect": [{"op": "destroy",
                                   "select": {"ref": "event.subject"}}]}]}
FORM = [TRIGGER]

# parse 後は destroy マクロが move（to: graveyard, reason: destroy）
# に展開される。parse 比較は展開形で行う。
PARSED_TRIGGER = copy.deepcopy(TRIGGER)
PARSED_TRIGGER["effect"][0]["effect"] = [
    {"op": "move", "select": {"ref": "event.subject"},
     "to": "graveyard", "reason": "destroy"}]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1076")
    assert c["abilities"] == FORM
    assert c["keywords"] == ["slayer"]
    d = parse_card(copy.deepcopy(c), TABLES)
    assert PARSED_TRIGGER in d.abilities


def test_form_raw_parse():
    d = parse_card({"id": "TX358", "name": "x",
                    "types": ["creature"], "civs": ["darkness"],
                    "cost": 2, "power": 2000,
                    "keywords": ["slayer"],
                    "abilities": [copy.deepcopy(TRIGGER)]}, TABLES)
    assert PARSED_TRIGGER in d.abilities


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive_attack(e, attacker, attacker_owner, block_with=None,
                  mark_entered=False):
    """attacker でプレイヤーを攻撃する。block_with があれば
    そのブロッカーでブロックする。mark_entered=True なら
    attacker の entered_turn を常に現在のターンに合わせ、
    「出たターンに攻撃する」状況を再現する（第134弾の作法）。
    攻撃したターンの2つ先のターンまで進めて状態を返す。"""
    state = {"attacked": False, "attack_turn": None}
    for _ in range(1500):
        if state["attacked"] and e.s.turn >= state["attack_turn"] + 2:
            break
        if mark_entered:
            for c in e.bz_tops(attacker_owner):
                if e.cdef(c).id == attacker:
                    e.s.cards[c].entered_turn = e.s.turn
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        if kind == "attack":
            hit = [i for i, k in enumerate(keys)
                   if k == f"attack:{attacker}:player"]
            if hit and not state["attacked"]:
                state["attacked"] = True
                state["attack_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            hit = [i for i, k in enumerate(keys)
                   if block_with and k.startswith(f"bz:{block_with}:")]
            if hit:
                e.answer([hit[0]])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return state


def test_entered_this_turn_attacker_destroyed_after_attack(rules):
    """出たターンに攻撃した相手クリーチャー（3000）は、
    ブロックされずに攻撃した後、破壊される。"""
    e = _build(rules, {"bz": ["T1076"]}, {"bz": ["T1077"]})
    st = _drive_attack(e, "T1077", 1, mark_entered=True)
    assert st["attacked"]
    assert "T1077" in _defns(e, "graveyard", 1)   # 攻撃の後に破壊
    assert "T1077" not in _defns(e, "bz", 1)
    assert "T1076" in _defns(e, "bz", 0)          # 観測者は残る


def test_entered_this_turn_attacker_destroyed_even_after_winning_battle(rules):
    """出たターンに攻撃した相手クリーチャーが小ブロッカー
    （1000）に勝っても、バトルの後に破壊される。"""
    e = _build(rules, {"bz": ["T1076", "T1078"]}, {"bz": ["T1077"]})
    st = _drive_attack(e, "T1077", 1, block_with="T1078",
                       mark_entered=True)
    assert st["attacked"]
    assert "T1078" in _defns(e, "graveyard", 0)   # バトル敗北
    assert "T1077" in _defns(e, "graveyard", 1)   # バトルの後に破壊
    assert "T1077" not in _defns(e, "bz", 1)
    assert "T1076" in _defns(e, "bz", 0)


def test_not_entered_this_turn_attacker_survives(rules):
    """前ターンからいる相手クリーチャーが攻撃しても
    破壊されない（entered_this_turn で除外される）。"""
    e = _build(rules, {"bz": ["T1076"]}, {"bz": ["T1077"]})
    st = _drive_attack(e, "T1077", 1, mark_entered=False)
    assert st["attacked"]
    assert "T1077" in _defns(e, "bz", 1)
    assert "T1077" not in _defns(e, "graveyard", 1)


def test_own_entered_this_turn_attacker_survives(rules):
    """自分のクリーチャーが出たターンに攻撃しても破壊
    されない（subject の owner: opp で自分の側は対象外）。"""
    e = _build(rules, {"bz": ["T1076", "T1077"]}, {"bz": ["T1078"]})
    st = _drive_attack(e, "T1077", 0, mark_entered=True)
    assert st["attacked"]
    assert "T1077" in _defns(e, "bz", 0)
    assert "T1077" not in _defns(e, "graveyard", 0)
