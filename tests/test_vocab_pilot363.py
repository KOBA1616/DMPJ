"""語彙パイロット第363弾: attack_on_entry_turn_punished
（ドリフト）。

センサス（rejects 1,970件を取り直し）: pure 1,822件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜362弾: negate_effects /
opponent_choice_branch / shield_grant /
cost_matching_selection / per_civilization_selection /
flying / delayed_return / draw_up_to / look_reorder /
does_not_untap / フィールド系 / unblocked_creature_attack /
has_ability_filter / mana_tap_trigger / attack_end_trigger /
must_attack_next_turn 系 / civ_all_present /
keyword_exists_condition / 入場時タップ付与系 /
バトル勝敗破壊系 / same_power_destroy /
after_battle_trigger / cast_event_trigger /
attack_event_trigger / block_event_target /
bottom_deck_mill / turn_draw_trigger /
variable_breaks_by_count / count_face_up_shields /
power_per_civilization / trigger_when_played_free /
first_time_cast_or_summon / cross_event_trigger /
mana_enters_untapped / first_time_tap /
mirror_opponent_draw / draw_mirror / spell_return /
fixed_breaks_plus_one / king_cell / ignore_breaker /
graveyard_lock / being_attacked_power /
state_condition_destruction 等）は再提案しない。
本弾で個別に評価して見送った候補:
unblockable_only_when_attacking_creatures（pure 2、
dm09-030 / dm09-050。partial の注記どおり be_blocked の
deny は攻撃対象で切り替えられず、対象依存のブロック
否定は新語彙が要る）、s_trigger_suppression（pure 2。
dm27-051 は「このクリーチャーがブレイクする
シールド」紐づけ、dm28-025 は条件つき全体抑制で
形が相異なり均一でない）、broken_shields_no_s_trigger
（pure 2。ブレイク発生源に紐づく S・トリガー禁止で
抑制語彙の新設が要る）、civ_blocker（pure 2。文明限定
ブロッカーは宣言フィルタに攻撃側文明の照合が無く、
同文明バトル敗北時の置換も併記され重い）、
attack_limit_once_per_turn（pure 2。dm23bd7-004 は
攻撃のみ・dm23bd7-012 は呪文面で攻撃＋ブロック各1回と
範囲が相異なり均一でなく、ターン内攻撃回数の上限を
数える常在形も無い）、entered_turn_attack（pure 2。
promoy16-008 は自他両面の2条項、dmbd11-d05 は単体で
形が相異なる）、conditional_s_trigger（pure 2。
両件とも代替コスト・初回誘発・モーダル等の重い他条項が
残り、本 gap 単独では登録できない）、block_break
（pure 1、dm33-001。ブロックしたクリーチャー自身が
シールドをブレイクする処理はブロック解決中のブレイク
帰属が別機構）、battle_does_not_occur_when_blocking
（pure 1、dm06-072。バトルそのものの取消しは置換の
語彙が無い）。範囲内・未評価で最小の
attack_on_entry_turn_punished（pure 1件、multi にも
現れない）を選定した:
dm22rp2x-023 試練の大地ダン・ティラン「相手の
クリーチャーが出たターンに攻撃する時、相手はその
クリーチャーを自身のマナゾーンに置く」。
partial はマッハファイターの展開形1能力を持ち、
未解決は unsupported の本 gap 1件だけ。

結論はドリフト（追加語彙なし）。部品はすべて確立済み:
- 攻撃誘発の第三者観測形 {event: attack, subject:
  {owner: opp, filter: {entered_this_turn: true}}} は
  第358弾の確立形そのもの（登録先例 dm22rp1-039 落下男）。
- 第358弾との違いはタイミングだけ: 本条項は「その攻撃の
  後」ではなく「攻撃する時」に即時置くため、
  delayed_trigger を挟まず、誘発の効果で直接
  move {select: {ref: event.subject}, to: mana,
  reason: put} する。move to: mana / reason: put は
  dm22rp1-047 等の登録形。
- 「相手は…自身のマナゾーンに置く」は対象が
  event.subject に固定され選択の余地が無いため、
  行為者が相手であることは効果の形に影響しない
  （置き先はそのクリーチャーの持ち主のマナゾーンで、
  move の既定の帰属どおり）。

proto T1092（dm22rp2x-023 型。partial 既存の
マッハファイター展開形＋本弾の確立形の2能力）/
T1093（パワー3000アタッカー、スピードアタッカー付き。
出たターンに攻撃するには召喚酔いの回避が要る）/
T1094（パワー2000の攻撃対象役）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接包む（第319弾以降の
作法）。実挙動テストでは「出たターン」の再現に、対象
クリーチャーの entered_turn を現在のターンへ合わせる
（第134弾・第358弾の作法）。
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
MACH = {"kind": "trigger",
        "when": {"event": "move", "to": "bz", "subject": "self"},
        "effect": [{"op": "modify", "select": {"ref": "self"},
                    "mod": {"allow": [{"action": "attack_creature",
                                       "other": {"tapped": False}}]},
                    "duration": "end_of_turn"}]}
TRIGGER = {"kind": "trigger",
           "when": {"event": "attack", "subject": _OPP_NEW},
           "effect": [{"op": "move",
                       "select": {"ref": "event.subject"},
                       "to": "mana", "reason": "put"}]}
FORM = [MACH, TRIGGER]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1092")
    assert c["abilities"] == FORM
    assert c["types"] == ["creature"]
    assert c["cost"] == 4 and c["power"] == 5000
    d = parse_card(copy.deepcopy(c), TABLES)
    assert TRIGGER in d.abilities
    for tid in ("T1093", "T1094"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX363", "name": "x",
                    "types": ["creature"], "civs": ["nature"],
                    "cost": 4, "power": 5000,
                    "races": ["ガイア・コマンド"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert TRIGGER in d.abilities


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive_attack(e, attacker, attacker_owner, target="player",
                  mark_entered=False):
    """attacker で攻撃する。target は "player" か対象
    クリーチャーの defn id。mark_entered=True なら attacker の
    entered_turn を常に現在のターンに合わせ、「出たターンに
    攻撃する」状況を再現する（第134弾・第358弾の作法）。
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
                   if k == f"attack:{attacker}:{target}"]
            if hit and not state["attacked"]:
                state["attacked"] = True
                state["attack_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            if "no_block" in keys:
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


def test_entered_this_turn_attacker_put_into_own_mana(rules):
    """出たターンにプレイヤーを攻撃した相手クリーチャー
    （3000）は、攻撃する時に自身のマナゾーンに置かれ、
    シールドはブレイクされない（攻撃が成立しない）。"""
    e = _build(rules, {"bz": ["T1092"]}, {"bz": ["T1093"]})
    shields = len(e.zlist("shield", 0))
    st = _drive_attack(e, "T1093", 1, mark_entered=True)
    assert st["attacked"]
    assert "T1093" in _defns(e, "mana", 1)        # 相手自身のマナへ
    assert "T1093" not in _defns(e, "bz", 1)
    assert "T1093" not in _defns(e, "mana", 0)    # 自分のマナではない
    assert len(e.zlist("shield", 0)) == shields   # ブレイクなし
    assert "T1092" in _defns(e, "bz", 0)          # 観測者は残る


def test_entered_this_turn_attacker_on_creature_put_into_mana_no_battle(rules):
    """出たターンにクリーチャーを攻撃した場合も、その
    クリーチャーはマナゾーンに置かれ、バトルは行われない
    （攻撃対象は残る）。攻撃対象は、先に自身が攻撃して
    タップ状態になることで作る（アンタップ状態の
    クリーチャーへの攻撃選択肢は出ないため）。"""
    e = _build(rules, {"bz": ["T1092", "T1094"]}, {"bz": ["T1093"]})
    state = {"target_attacked": False, "attacked": False,
             "attack_turn": None}
    for _ in range(1500):
        if state["attacked"] and e.s.turn >= state["attack_turn"] + 2:
            break
        for c in e.bz_tops(1):
            if e.cdef(c).id == "T1093":
                e.s.cards[c].entered_turn = e.s.turn
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        kind = d["kind"]
        pl = d.get("player")
        if kind == "attack" and pl == 0 \
                and not state["target_attacked"]:
            hit = [i for i, k in enumerate(keys)
                   if k == "attack:T1094:player"]
            if hit:
                state["target_attacked"] = True
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "attack" and pl == 1 \
                and state["target_attacked"] \
                and not state["attacked"]:
            hit = [i for i, o in enumerate(d["options"])
                   if o["key"].startswith("attack:T1093:")
                   and o.get("target") != "player"]
            if hit:
                state["attacked"] = True
                state["attack_turn"] = e.s.turn
                e.answer([hit[0]])
            elif "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "block":
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert state["target_attacked"] and state["attacked"]
    assert "T1093" in _defns(e, "mana", 1)
    assert "T1093" not in _defns(e, "bz", 1)
    assert "T1094" in _defns(e, "bz", 0)          # バトルなしで残る
    assert "T1094" not in _defns(e, "graveyard", 0)


def test_not_entered_this_turn_attacker_attacks_normally(rules):
    """前ターンからいる相手クリーチャーが攻撃しても
    置かれない（entered_this_turn で除外される）。
    シールドは通常どおり1枚ブレイクされる。"""
    e = _build(rules, {"bz": ["T1092"]}, {"bz": ["T1093"]})
    shields = len(e.zlist("shield", 0))
    st = _drive_attack(e, "T1093", 1, mark_entered=False)
    assert st["attacked"]
    assert "T1093" in _defns(e, "bz", 1)
    assert "T1093" not in _defns(e, "mana", 1)
    assert len(e.zlist("shield", 0)) == shields - 1


def test_own_entered_this_turn_attacker_unaffected(rules):
    """自分のクリーチャーが出たターンに攻撃しても置かれない
    （subject の owner: opp で自分の側は対象外）。"""
    e = _build(rules, {"bz": ["T1092", "T1093"]}, {"bz": ["T1094"]})
    shields = len(e.zlist("shield", 1))
    st = _drive_attack(e, "T1093", 0, mark_entered=True)
    assert st["attacked"]
    assert "T1093" in _defns(e, "bz", 0)
    assert "T1093" not in _defns(e, "mana", 0)
    assert len(e.zlist("shield", 1)) == shields - 1


def test_entered_this_turn_opponent_creature_not_attacking_stays(rules):
    """出たターンでも、攻撃しなければ置かれない
    （誘発は攻撃イベントに紐づく）。"""
    e = _build(rules, {"bz": ["T1092"]}, {"bz": ["T1093"]})
    for _ in range(300):
        for c in e.bz_tops(1):
            if e.cdef(c).id == "T1093":
                e.s.cards[c].entered_turn = e.s.turn
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        else:
            e.answer(list(range(d.get("min", 0))))
        if e.s.turn >= 4:
            break
    assert "T1093" in _defns(e, "bz", 1)
    assert "T1093" not in _defns(e, "mana", 1)
