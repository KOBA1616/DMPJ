"""語彙パイロット第328弾: 滅亡の光（filter_not_race＋
first_attack_end 各クリーチャー）— ドリフト（not_race_has＋
once_per_turn 付き付与型誘発。追加語彙なし）。

センサス（rejects 2,039件を取り直し）: pure 1,890件 / multi 131件 /
空 gaps 18件（全て第312〜315弾の監査で別ブロッカー確認済み。
数え方は全行を pure/multi/空に分け、out_of_scope 行も gaps に
従って数える）。pure の大半は範囲外（gr_summon 147、aura 108＝
未承認、hyperdimensional_zone 105、dragheart 45、psychic_filter 45、
hyperdimensional_summon 41、out_of_game 23、duelist_link 20、
outside_game 12＝2026-11-06 ユーザー指示で対象外化済み、
pandora_shift 4）か評価済み DEEP/重い/延期（第318〜327弾の記録参照）。
delayed_return / draw_up_to / look_reorder / flying / does_not_untap
は新しい証拠がない限り再提案しない（第320・321弾で却下済み）。
4件組はすべて評価済み。2件組のうち、after_battle_trigger /
attack_limit_once_per_turn / cip_trigger_double /
s_trigger_suppression / enters_tapped_optional / from_hand_trigger
は第323弾で却下済み。第327弾の記録にある候補のうち、範囲内・
未評価で最小の **dmex15-b019 滅亡の光（multi-gap 2件。
filter_not_race＋first_attack_end）** を選定した。

対象は dmex15-b019 滅亡の光（闇/火・コスト9・マナ1の呪文）。
partial あり（アタック・チャンスは declare＋play_free で変換済み）。
by_product で原文照合済み。canon_id は dmex15-b019 で aliases 無し。
「アタック・チャンス：クリエイター（自分のクリエイターが攻撃する
時、この呪文をコストを支払わずに唱えてもよい）／ゴッド、フェニッ
クス、クリエイター以外のクリーチャーをすべて破壊する。／このターン、
ゴッド、フェニックス、またはクリエイターそれぞれの最初の攻撃の
終わりに、そのクリーチャーをアンタップする。」

結論: ドリフト（追加語彙なし）。2つの条項はいずれも既存形:
- filter_not_race: [destroy {zone: bz, owner: any,
  filter: {types: [creature],
  not_race_has: [ゴッド, フェニックス, クリエイター]}, count: all}]
  （not_race_has は第81弾。リスト形式も対応。destroy の zone
  select＋count: all は dm38-013 の先例。「すべて」は両プレイヤー
  のため owner: any）
- first_attack_end 各クリーチャー: [modify {zone: bz, owner: any,
  filter: {any_of: [{race_has: ゴッド}, {race_has: フェニックス},
  {race_has: クリエイター}]}, count: all},
  mod: {gain: [{kind: trigger,
  when: {event: attack_end, subject: self},
  effect: [{op: untap, select: {ref: self}}], once_per_turn: true}]},
  duration: end_of_turn]
  （「それぞれ」（各クリーチャーごと）のため、単一の once 遅延誘発
  （第327弾）では書けない。各クリーチャーに「最初の攻撃の終わりに
  アンタップする」を与え、once_per_turn（48件の先例）で各体1回に
  制限する。race_has は単一文字列のため、3種族は any_of（第138弾）
  で並べる。untap {ref: self} は134件の先例。owner: any は条文に
  「自分の」が無いため両プレイヤー。アタック・チャンスは partial
  どおり declare＋play_free）

プロト T997（dmex15-b019 型）。
次の空きは T998。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card
from tests._conv_cache import proto_card

TABLES = load_tables()

DECLARE = {"kind": "declare", "zone": "hand",
           "when": {"event": "attack",
                    "subject": {"owner": "you",
                                "filter": {"race_has": "クリエイター"}}},
           "effect": [{"op": "play_free", "select": {"ref": "self"}}]}

TRIGGER = {"kind": "trigger",
           "when": {"event": "attack_end", "subject": "self"},
           "effect": [{"op": "untap", "select": {"ref": "self"}}],
           "once_per_turn": True}

FORM = [
    {"op": "destroy",
     "select": {"zone": "bz", "owner": "any",
                "filter": {"types": ["creature"],
                           "not_race_has": ["ゴッド", "フェニックス",
                                            "クリエイター"]},
                "count": "all"}},
    {"op": "modify",
     "select": {"zone": "bz", "owner": "any",
                "filter": {"any_of": [{"race_has": "ゴッド"},
                                      {"race_has": "フェニックス"},
                                      {"race_has": "クリエイター"}]},
                "count": "all"},
     "mod": {"gain": [TRIGGER]},
     "duration": "end_of_turn"},
]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_parse_and_forms():
    c997 = proto_card("T997")
    assert c997["abilities"] == [DECLARE]
    assert c997["spell"] == FORM
    d = parse_card(c997, TABLES)
    assert len(d.spell) == 2


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _cast_spell(e, cid, mana_n):
    """main で指定の呪文を唱える（コストは火5＋闇4のマナで払う。
    多色呪文には両文明のマナが要る）。唱えた時点で戻る。"""
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


def test_destroy_only_non_god_phoenix_creator(rules):
    """filter_not_race: ゴッド／フェニックス／クリエイター以外は
    両プレイヤーとも破壊される。ゴッドは両プレイヤーとも残る。
    残ったゴッドは付与された誘発（once_per_turn）を持つ。"""
    e = setup(rules, {"bz": ["T053", "T001"], "hand": ["T997"],
                      "mana": ["T005"] * 5 + ["T056"] * 4},
              {"bz": ["T004", "T055"]})
    _cast_spell(e, "T997", 9)
    assert e.s.cards[_bz(e, 0, "T053")].zone == "bz"
    assert e.s.cards[_bz(e, 1, "T055")].zone == "bz"
    gy0 = [c for c in e.zlist("graveyard", 0)]
    gy1 = [c for c in e.zlist("graveyard", 1)]
    assert any(e.s.cards[c].defn == "T001" for c in gy0)
    assert any(e.s.cards[c].defn == "T004" for c in gy1)
    for p, dfn in ((0, "T053"), (1, "T055")):
        trigs = [ab for _, ab in e.abilities(_bz(e, p, dfn), "trigger")]
        assert any(ab.get("once_per_turn") for ab in trigs), (p, trigs)


def test_each_god_untaps_after_first_attack_end(rules):
    """first_attack_end 各クリーチャー: ゴッドは最初の攻撃の終わりに
    アンタップされる。2回目の攻撃の終わりにはもうアンタップ
    されない（once_per_turn）。"""
    e = setup(rules, {"bz": ["T053"], "hand": ["T997"],
                      "mana": ["T005"] * 5 + ["T056"] * 4}, {})
    e.s.cards[_bz(e, 0, "T053")].entered_turn = -1
    _cast_spell(e, "T997", 9)
    t053 = _bz(e, 0, "T053")
    assert e.s.cards[t053].tapped is False
    _attack_player(e, "T053")
    _drive_combat(e)
    assert e.s.cards[t053].tapped is False
    _attack_player(e, "T053")
    _drive_combat(e)
    assert e.s.cards[t053].tapped is True
