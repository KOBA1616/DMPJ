"""語彙パイロット第326弾: 「攻撃してブロックされた時、相手の
シールドを１枚ブレイクする」（blocked_break）— ドリフト
（block イベントの確立形。追加語彙なし）。

センサス（rejects 2,043件を取り直し）: pure 1,894件 / multi 131件 /
空 gaps 18件（全て第312〜315弾の監査で別ブロッカー確認済み。
数え方は全行を pure/multi/空に分け、out_of_scope 行も gaps に
従って数える）。pure の大半は範囲外（gr_summon 147、aura 108＝
未承認、hyperdimensional_zone 105、dragheart 45、psychic_filter 45、
hyperdimensional_summon 41、out_of_game 23、duelist_link 20、
outside_game 12＝2026-11-06 ユーザー指示で対象外化済み、
pandora_shift 4）か評価済み DEEP/重い/延期（第318〜325弾の記録参照）。
delayed_return / draw_up_to / look_reorder / flying / does_not_untap
は新しい証拠がない限り再提案しない（第320・321弾で却下済み）。
4件組はすべて評価済み。2件組のうち、after_battle_trigger /
attack_limit_once_per_turn / cip_trigger_double /
s_trigger_suppression / enters_tapped_optional / from_hand_trigger
は第323弾で却下済み。第325弾の記録にある候補のうち、範囲内・
未評価で最小の **blocked_break（純粋2件、multi-gap 行にも
現れない）** を選定した。

対象は dm39-035 カンクロウ・ブラスター（自然・コスト6・マナ1の呪文）
/ dmc34-030 獣達の挽歌（自然・コスト4・マナ1の呪文）。
両行とも partial あり（unsupported の断片だけ）。by_product で
原文照合済み。
- dm39-035: 「このターン、自分のクリーチャーすべてのパワーは+4000
  され、シールドをさらに１枚ブレイクする。／このターン、自分の
  クリーチャーが相手を攻撃しブロックされた時、相手のシールドを
  １枚ブレイクする。／呪文の効果によって、このターン、相手が
  バトルゾーンにあるクリーチャーを選ぶ時、自分のクリーチャーを
  選ぶことはできない。」
- dmc34-030: 「このターンの終わりまで、自分のクリーチャーすべての
  パワーは+4000され、「このクリーチャーが相手プレイヤーを攻撃して
  ブロックされた時、相手のシールドを１枚ブレイクする」を得る。」

結論: ドリフト（追加語彙なし）。核は block イベントの確立形
（converted.yaml に129件の先例。ニンジャ・ストライク等）で、
attack_end {blocked: true} ではない。理由: ブロックが宣言されると
攻撃先はブロッカーの参照に書き換わる（combat.py:434）ため、
attack_end レコードの target はブロッカー参照になり、target:
player はブロックされた攻撃に決して一致しない（実測で確認。
subject は攻撃クリーチャーのまま、blocked: true は立つ）。
block イベントのレコードは {ev: block, subject: ブロッカー参照,
attacker: 攻撃クリーチャー参照, controller: 防御側} で、when の
attacker キーで攻撃クリーチャーを照合する。ブレイクはブロック
宣言の直後（バトルの前）に起きるが、これが実ルールのタイミング
でもある。break op は第322弾の先例。2つの形は核を共有し、
届け方だけが違う:
- 形A（dm39-035）: 呪文が3つの継続的効果を作る。
  (1) [modify {zone: bz, owner: you, filter: {types: [creature]},
  count: all} {power: 4000, breaks_add: 1} end_of_turn]
  (2) [delayed_trigger {event: block,
  attacker: {owner: you, filter: {types: [creature]}}}
  → [{op: break, player: opp, count: 1}]
  end_of_turn, once: false]（attacker の {owner, filter} 形は
  _ref_match / _subject_match が受ける。once: false は「このターン」
  のブロックすべてに及ぶため。遅延誘発の when 照合は通常の誘発と
  同じ _match_when 経路）
  (3) [modify {zone: bz, owner: you, filter: {types: [creature]},
  count: all}
  {deny: [{action: be_chosen, other: {types: [spell]}}]}
  end_of_turn]（範囲つきの選ばれない保護は第164弾の先例。
  dm25ex3-009 / dm26ex3-050 と同形。選ぶ側が相手の時だけ働く）
- 形B（dmc34-030）: 呪文が1つの継続的効果を作る。
  [modify {zone: bz, owner: you, filter: {types: [creature]},
  count: all}
  {power: 4000, gain: [{kind: trigger,
  when: {event: block, attacker: self},
  effect: [{op: break, player: opp, count: 1}]}]}
  end_of_turn]（gain による誘発能力の付与は converted.yaml に
  21件の先例。dmd26-002 と同形。付与された能力は abilities() で
  負の添字で返り、誘発時は pending に inline で持たせるため
  正常に発火する）

教訓（2つ）: (1) op_modify の select は count の既定が1なので、
「自分のクリーチャーすべて」には count: all が要る（spell の
modify に90件の先例。dm22-023 は gain 付きの同形）。count を
忘れると choose_cards の決定が出て1体だけに効く。(2) 自然の呪文を
唱えるには自然のマナが1枚要る。T030 は光/水のため唱えられず、
main の決定自体が出ない。テストのマナには自然の T001 を使う。

プロト T994（dm39-035 型）/ T995（dmc34-030 型）。
次の空きは T996。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card
from tests._conv_cache import proto_card

TABLES = load_tables()

TRIGGER = {"kind": "trigger",
           "when": {"event": "block", "attacker": "self"},
           "effect": [{"op": "break", "player": "opp", "count": 1}]}

FORM_A = [
    {"op": "modify",
     "select": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}, "count": "all"},
     "mod": {"power": 4000, "breaks_add": 1},
     "duration": "end_of_turn"},
    {"op": "delayed_trigger",
     "when": {"event": "block",
              "attacker": {"owner": "you",
                           "filter": {"types": ["creature"]}}},
     "effect": [{"op": "break", "player": "opp", "count": 1}],
     "duration": "end_of_turn", "once": False},
    {"op": "modify",
     "select": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}, "count": "all"},
     "mod": {"deny": [{"action": "be_chosen",
                       "other": {"types": ["spell"]}}]},
     "duration": "end_of_turn"},
]

FORM_B = [
    {"op": "modify",
     "select": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}, "count": "all"},
     "mod": {"power": 4000, "gain": [TRIGGER]},
     "duration": "end_of_turn"},
]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_parse_and_forms():
    c994 = proto_card("T994")
    assert c994["spell"] == FORM_A
    d = parse_card(c994, TABLES)
    assert len(d.spell) == 3
    c995 = proto_card("T995")
    assert c995["spell"] == FORM_B
    d = parse_card(c995, TABLES)
    assert len(d.spell) == 1


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _cast_spell(e, cid, mana_n):
    """main で指定の呪文を唱える（コストは mana_n 枚の T030 で払う）。
    唱えた時点で戻る（解決後の決定は出ない想定）。"""
    cast = False
    for _ in range(120):
        d = e.advance()
        assert d is not None, "game ended before cast"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and not cast \
                and f"play:{cid}" in keys:
            e.answer([keys.index(f"play:{cid}")])
            cast = True
            continue
        if cast and d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if cast and d["kind"] in ("charge", "main", "attack"):
            return
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("spell did not resolve")


def _attack_player(e, attacker_defn, player=0):
    for _ in range(120):
        d = e.advance()
        assert d is not None, "game ended before attack"
        if d["kind"] == "attack" and d.get("player") == player:
            keys = _keys(d)
            e.answer([keys.index(f"attack:{attacker_defn}:player")])
            return
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys
                 else list(range(d["min"])))
    raise AssertionError("attack decision did not appear")


def _drive_combat(e, block=False, max_steps=200):
    for _ in range(max_steps):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main", "attack"):
            return
        keys = _keys(d)
        if d["kind"] == "block":
            if block:
                guard = next((i for i, k in enumerate(keys)
                              if k != "no_block"), None)
                assert guard is not None, keys
                e.answer([guard])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")])
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("combat did not settle")


def test_granted_trigger_breaks_on_blocked_attack(rules):
    """形B: 挽歌を唱えると自分のクリーチャーはパワー+4000され、
    ブロックされた攻撃の終わりに相手のシールドを1枚割る。
    ブロックされなかった攻撃では余分に割らない。"""
    e = setup(rules, {"bz": ["T001", "T002"],
                      "hand": ["T995"], "mana": ["T001"] * 4},
              {"bz": ["T004"]})
    for dfn in ("T001", "T002"):
        e.s.cards[_bz(e, 0, dfn)].entered_turn = -1
    _cast_spell(e, "T995", 4)
    assert e.chars(_bz(e, 0, "T001"))["power"] == 6000
    # ブロックされた攻撃: 戦闘で T004 を破壊し、誘発でシールド1枚割る
    before = len(e.zlist("shield", 1))
    _attack_player(e, "T001")
    _drive_combat(e, block=True)
    assert len(e.zlist("shield", 1)) == before - 1
    # ブロックされなかった攻撃: 通常の1枚だけで、余分は割らない
    before = len(e.zlist("shield", 1))
    _attack_player(e, "T002")
    _drive_combat(e)
    assert len(e.zlist("shield", 1)) == before - 1


def test_spell_delayed_trigger_breaks_on_blocked_attack(rules):
    """形A: ブラスターを唱えると自分のクリーチャーはパワー+4000・
    さらに1枚ブレイクし、ブロックされた攻撃の終わりに相手の
    シールドを1枚割る。2回目のブロックされた攻撃でも割る
    （once: false）。"""
    e = setup(rules, {"bz": ["T001", "T002"],
                      "hand": ["T994"], "mana": ["T001"] * 6},
              {"bz": ["T004", "T004"]})
    for dfn in ("T001", "T002"):
        e.s.cards[_bz(e, 0, dfn)].entered_turn = -1
    _cast_spell(e, "T994", 6)
    assert e.chars(_bz(e, 0, "T001"))["power"] == 6000
    # 1回目のブロックされた攻撃: シールド1枚割る
    before = len(e.zlist("shield", 1))
    _attack_player(e, "T001")
    _drive_combat(e, block=True)
    assert len(e.zlist("shield", 1)) == before - 1
    # 2回目のブロックされた攻撃: 遅延誘発は残っているのでもう1枚割る
    before = len(e.zlist("shield", 1))
    _attack_player(e, "T002")
    _drive_combat(e, block=True)
    assert len(e.zlist("shield", 1)) == before - 1


def test_spell_deny_be_chosen_by_spells(rules):
    """形A: ブラスターを唱えたターン、自分のクリーチャーは相手の
    呪文に選ばれない。クリーチャーの効果からの選択は妨げない。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T994"],
                      "mana": ["T001"] * 6},
              {"hand": ["T006"], "bz": ["T004"]})
    t001 = _bz(e, 0, "T001")
    t006 = next(c for c in e.zlist("hand", 1)
                if e.s.cards[c].defn == "T006")
    t004 = _bz(e, 1, "T004")
    assert e.permits(t001, "be_chosen", other=t006)
    _cast_spell(e, "T994", 6)
    assert not e.permits(t001, "be_chosen", other=t006)
    assert e.permits(t001, "be_chosen", other=t004)
