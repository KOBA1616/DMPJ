"""語彙パイロット第327弾: 「そのクリーチャーの最初の攻撃の
終わりに、そのクリーチャーをアンタップする」（first_attack_end）
— ドリフト（modal＋once 既定の遅延誘発。追加語彙なし）。

センサス（rejects 2,041件を取り直し）: pure 1,892件 / multi 131件 /
空 gaps 18件（全て第312〜315弾の監査で別ブロッカー確認済み。
数え方は全行を pure/multi/空に分け、out_of_scope 行も gaps に
従って数える）。pure の大半は範囲外（gr_summon 147、aura 108＝
未承認、hyperdimensional_zone 105、dragheart 45、psychic_filter 45、
hyperdimensional_summon 41、out_of_game 23、duelist_link 20、
outside_game 12＝2026-11-06 ユーザー指示で対象外化済み、
pandora_shift 4）か評価済み DEEP/重い/延期（第318〜326弾の記録参照）。
delayed_return / draw_up_to / look_reorder / flying / does_not_untap
は新しい証拠がない限り再提案しない（第320・321弾で却下済み）。
4件組はすべて評価済み。2件組のうち、after_battle_trigger /
attack_limit_once_per_turn / cip_trigger_double /
s_trigger_suppression / enters_tapped_optional / from_hand_trigger
は第323弾で却下済み。第326弾の記録にある候補のうち、範囲内・
未評価で最小の **first_attack_end（純粋2件、multi-gap 行にも
現れない）** を選定した。

対象は dm26ex4-cho025 / dm26sd1-i004 の瞬閃と疾駆と双撃の決断
（火・コスト3・マナ1の呪文、同一カードの2印刷。canon_id は
dm26ex4-cho025）。両行とも partial あり（unsupported の断片だけ）。
by_product で原文照合済み（正本は cho025 の文面。sd1-i004 の
文面はモード2に「（「スピードアタッカー」を持つクリーチャーは
召喚酔いしない）」の注釈が付くが、注釈はデータモデルに無いため
正本の文面で登録する）。
「次の中から２回選ぶ。同じものを選んでもよい。／▶コスト３以下の
クリーチャーを１体、自分の手札から出す。／▶このターン、自分の
クリーチャー１体に「スピードアタッカー」を与える。／▶自分の
クリーチャーを１体選ぶ。このターン、そのクリーチャーの最初の攻撃の
終わりに、そのクリーチャーをアンタップする。」

結論: ドリフト（追加語彙なし）。modal op が「次の中から２回選ぶ
（同じものを選んでもよい）」をそのまま表す（count: 2,
repeat: true。12件の repeat-modal の先例。dm23rp1-008 等）。
3つのモードはいずれも既存形:
- モード1: [play_free {zone: hand, owner: you,
  filter: {types: [creature], cost_le: 3}, count: 1}]
- モード2: [choose {zone: bz, owner: you,
  filter: {types: [creature]}, count: 1} as: c,
  modify {ref: c, count: all} {grant: [speed_attacker]}
  end_of_turn]（dm22rp2x-008 と同形）
- モード3（first_attack_end）: [choose {zone: bz, owner: you,
  filter: {types: [creature]}, count: 1} as: chosen,
  delayed_trigger {event: attack_end, subject: {ref: chosen}}
  → [{op: untap, select: {ref: chosen}}] end_of_turn]
  （once は既定の true。遅延誘発は最初の attack_end で発火して
  消えるため、「最初の攻撃の終わり」そのものになる。攻撃先や
  ブロックの有無は問わない）

プロト T996（dm26ex4-cho025 型）。
次の空きは T997。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card
from tests._conv_cache import proto_card

TABLES = load_tables()

FORM = [
    {"op": "modal", "count": 2, "repeat": True,
     "modes": [
         [{"op": "play_free",
           "select": {"zone": "hand", "owner": "you",
                      "filter": {"types": ["creature"], "cost_le": 3},
                      "count": 1}}],
         [{"op": "choose",
           "select": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["creature"]}, "count": 1},
           "as": "c"},
          {"op": "modify", "select": {"ref": "c", "count": "all"},
           "mod": {"grant": ["speed_attacker"]},
           "duration": "end_of_turn"}],
         [{"op": "choose",
           "select": {"zone": "bz", "owner": "you",
                      "filter": {"types": ["creature"]}, "count": 1},
           "as": "chosen"},
          {"op": "delayed_trigger",
           "when": {"event": "attack_end", "subject": {"ref": "chosen"}},
           "effect": [{"op": "untap", "select": {"ref": "chosen"}}],
           "duration": "end_of_turn"}],
     ]},
]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_parse_and_forms():
    c996 = proto_card("T996")
    assert c996["spell"] == FORM
    d = parse_card(c996, TABLES)
    assert len(d.spell) == 1 and d.spell[0]["op"] == "modal"


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _cast_spell(e, modes, picks):
    """main で T996 を唱え、modal のモードを modes の順に選ぶ。
    picks は choose 系の決定に対する答えの列（defn の列）。
    唱えた時点で戻る。火の呪文なのでマナは火の T005 を使う。"""
    cast = False
    pick_i = 0
    for _ in range(200):
        d = e.advance()
        assert d is not None, "game ended before cast"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and not cast \
                and "play:T996" in keys:
            e.answer([keys.index("play:T996")])
            cast = True
            continue
        if cast and d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
            continue
        if cast and d["kind"] == "choose_mode":
            e.answer([keys.index(f"mode:{modes.pop(0)}")])
            continue
        if cast and d["kind"] == "choose_cards":
            want = picks[pick_i]
            pick_i += 1
            idx = next(i for i, k in enumerate(keys)
                       if k.split(":")[1] == want)
            e.answer([idx])
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


def _drive_combat(e, max_steps=200):
    for _ in range(max_steps):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main", "attack"):
            return
        keys = _keys(d)
        if d["kind"] == "block":
            if "no_block" in keys:
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


def test_mode3_first_attack_end_untaps_only_once(rules):
    """モード3: 選んだクリーチャーは最初の攻撃の終わりにアンタップ
    される。2回目の攻撃の終わりにはもうアンタップされない
    （遅延誘発は once: true の既定で消えている）。"""
    e = setup(rules, {"bz": ["T001"], "hand": ["T996", "T002"],
                      "mana": ["T005"] * 3}, {})
    e.s.cards[_bz(e, 0, "T001")].entered_turn = -1
    # モード3（T001）＋モード1（T002 を手札から出す）
    _cast_spell(e, [2, 0], ["T001", "T002"])
    t001 = _bz(e, 0, "T001")
    assert e.s.cards[t001].tapped is False
    # 1回目の攻撃: 終わりにアンタップされる
    _attack_player(e, "T001")
    _drive_combat(e)
    assert e.s.cards[t001].tapped is False
    # 2回目の攻撃: 遅延誘発はもう無いのでタップしたまま
    _attack_player(e, "T001")
    _drive_combat(e)
    assert e.s.cards[t001].tapped is True


def test_mode2_grants_speed_attacker(rules):
    """モード2: 選んだクリーチャー（召喚酔い中）にスピード
    アタッカーを与え、同じターンに攻撃できる。"""
    e = setup(rules, {"bz": ["T002"], "hand": ["T996"],
                      "mana": ["T005"] * 3}, {})
    # T002 はこのターン出たばかり（entered_turn は既定で今ターン）
    _cast_spell(e, [1, 1], ["T002", "T002"])
    before = len(e.zlist("shield", 1))
    _attack_player(e, "T002")
    _drive_combat(e)
    assert len(e.zlist("shield", 1)) == before - 1
