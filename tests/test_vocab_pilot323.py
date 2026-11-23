"""語彙パイロット第323弾: 「相手プレイヤーを攻撃してブロックされなかった時」
（unblocked_condition）— ドリフト（第321弾の確立形そのもの）。

センサス（rejects 2,049件を取り直し）: pure 1,900件 / multi 131件 /
空 gaps 18件（全て第312〜315弾の監査で別ブロッカー確認済み）。
pure の大半は範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 / duelist_link 20 /
outside_game 12＝対象外化済み / pandora_shift 4）か評価済み
DEEP・重い・延期（第318〜322弾の記録参照）。4件組はすべて評価済み
（victory_icon_filter、dokindam_gacha、cost_sum_of_revealed、
climax_dorongo、shield_manipulation、spell_replay、summon_lock、
opponent_chooses_deck_position、dynamic_name_reference_filter）。
3件組も大半が評価済み DEEP／延期。delayed_return / draw_up_to /
look_reorder / flying / does_not_untap は第320・321弾で却下済みで
再提案しない。範囲内・未評価で最小の純粋2件組を走査し、
after_battle_trigger（2件の構造が不均一・partial 空）、
attack_limit_once_per_turn（静的制限と時限呪文面で不均一）、
cip_trigger_double（トリガー二重化はエンジン作業が重い）、
s_trigger_suppression（抑制の条件が2件で異なる）、
breaks_equal_creature_count（別途ドリフト候補として記録）、
enters_tapped_optional（partial 空・他節が重い）、
from_hand_trigger（2件の構造が不均一）を却下し、
**unblocked_condition（純粋2件、multi-gap 行にも現れない）**を選定した。

対象は dmx04-011 ケロディ二郎 / dmx09-049 誕生の祈。両行とも
partial は空（unsupported に unblocked_condition だけが残る）で、
by_product（x04.jsonl / x09.jsonl）で原文照合済み。両カードとも
単一能力のクリーチャーで、全文がこの1節だけ:
- dmx04-011（水・コスト4・パワー2000・ゲル・フィッシュ/ハンター・
  マナ1）: 「このクリーチャーが相手プレイヤーを攻撃して
  ブロックされなかった時、バトルゾーンにあるクリーチャーを１体選び、
  持ち主の手札に戻してもよい。」
- dmx09-049（自然・コスト3・パワー2000・ビーストフォーク・
  マナ1）: 「このクリーチャーが相手プレイヤーを攻撃して
  ブロックされなかった時、自分の山札を見る。その中からクリーチャーを
  １体選び、相手に見せてから自分の手札に加えてもよい。その後、
  山札をシャッフルする。」

結論: ドリフト（追加語彙なし）。「ブロックされなかった時」は
第321弾で確立した attack_end {subject: self, target: player,
blocked: false} そのもので、ギャップ名の違いだけが残っていた。
効果側も既存の形:
- 形A（dmx04-011）: may [move {zone: bz, owner: any, filter: {types:
  [creature]}, count: 1} to hand, reason: return]（手札に戻すは
  既存の return 形。dm23rp1-057 等の先例）。
- 形B（dmx09-049）: may [choose {zone: deck, owner: you,
  look: true, filter: {types: [creature]}, count: 1} as t;
  move {ref: t, count: all} to hand, reason: draw; shuffle]
  （山札を見てクリーチャーを手札に加えるはアポロニア・ドラゴン
  の先例と同形。look: true が相手に見せる部分を担う）。

プロト T988（形A）/ T989（形B）。次の空きは T990。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card
from tests._conv_cache import proto_card

TABLES = load_tables()
IDS = ("T988", "T989")

FORM_A = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "may", "body": [
        {"op": "move",
         "select": {"zone": "bz", "owner": "any", "filter": {"types": ["creature"]},
                    "count": 1},
         "to": "hand", "reason": "return"}]}]}
FORM_B = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "may", "body": [
        {"op": "choose",
         "select": {"zone": "deck", "owner": "you", "look": True,
                    "filter": {"types": ["creature"]}, "count": 1},
         "as": "t"},
        {"op": "move", "select": {"ref": "t", "count": "all"},
         "to": "hand", "reason": "draw"},
        {"op": "shuffle"}]}]}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_parse_and_forms():
    for cid, form in (("T988", FORM_A), ("T989", FORM_B)):
        card = proto_card(cid)
        assert card["abilities"] == [form], cid
        d = parse_card(card, TABLES)
        assert len(d.abilities) >= 1


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _attack_player(e, attacker_defn):
    for _ in range(20):
        d = e.advance()
        assert d is not None, "game ended before attack"
        if d["kind"] == "attack":
            keys = _keys(d)
            e.answer([keys.index(f"attack:{attacker_defn}:player")])
            return
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys
                 else list(range(d["min"])))
    raise AssertionError("attack decision did not appear")


def _drive_combat(e, block=False, may_yes=True, choose_key=None,
                  max_steps=200):
    """攻撃の解決が終わる（次の charge / main / attack 決定か
    ゲーム終了）まで進める。block=True なら相手の T004 で
    ブロックさせる。yes_no（may の諮問）には may_yes で答える。
    choose_cards では choose_key（前方一致）があればその選択肢を
    選ぶ。"""
    for _ in range(max_steps):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main", "attack"):
            return d
        keys = _keys(d)
        if d["kind"] == "block":
            guard = next((i for i, k in enumerate(keys)
                          if k != "no_block"), None)
            if block and guard is not None:
                e.answer([guard])
            elif "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("yes" if may_yes else "no")])
        elif d["kind"] == "choose_cards":
            if choose_key is not None:
                hit = [i for i, k in enumerate(keys)
                       if k.startswith(choose_key)]
                assert hit, keys
                e.answer([hit[0]])
            else:
                e.answer(list(range(d["min"])))
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("combat did not settle")


def test_unblocked_bounces_opponent_creature(rules):
    """形A: ブロックされなかった攻撃の終わりに、相手のクリーチャーを
    持ち主の手札に戻せる。"""
    e = setup(rules, {"bz": ["T988"]}, {"bz": ["T004"]}, filler="T002")
    e.s.cards[_bz(e, 0, "T988")].entered_turn = -1
    t004 = _bz(e, 1, "T004")
    _attack_player(e, "T988")
    _drive_combat(e, choose_key="bz:T004:")
    assert e.s.cards[t004].zone == "hand"
    assert e.s.cards[t004].owner == 1
    assert len(e.bz_tops(1)) == 0


def test_unblocked_bounce_may_decline(rules):
    """形A: 「戻してもよい」ので辞退できる（対照）。"""
    e = setup(rules, {"bz": ["T988"]}, {"bz": ["T004"]}, filler="T002")
    e.s.cards[_bz(e, 0, "T988")].entered_turn = -1
    _attack_player(e, "T988")
    _drive_combat(e, may_yes=False)
    assert len(e.bz_tops(1)) == 1


def test_blocked_no_bounce(rules):
    """形A: ブロックされた攻撃では発火しない（判別）。"""
    e = setup(rules, {"bz": ["T988"]}, {"bz": ["T004"]}, filler="T002")
    e.s.cards[_bz(e, 0, "T988")].entered_turn = -1
    _attack_player(e, "T988")
    _drive_combat(e, block=True)
    assert len(e.bz_tops(1)) == 1


def test_unblocked_searches_creature_to_hand(rules):
    """形B: ブロックされなかった攻撃の終わりに、山札からクリーチャーを
    1体手札に加えられる（山札は T002 で満たされている）。"""
    e = setup(rules, {"bz": ["T989"]}, {}, filler="T002")
    e.s.cards[_bz(e, 0, "T989")].entered_turn = -1
    before = len(e.zlist("hand", 0))
    deck_before = len(e.zlist("deck", 0))
    _attack_player(e, "T989")
    _drive_combat(e)
    assert len(e.zlist("hand", 0)) == before + 1
    assert len(e.zlist("deck", 0)) == deck_before - 1
    assert e.s.cards[e.zlist("hand", 0)[-1]].defn == "T002"


def test_unblocked_search_may_decline(rules):
    """形B: 「加えてもよい」ので辞退できる（対照）。"""
    e = setup(rules, {"bz": ["T989"]}, {}, filler="T002")
    e.s.cards[_bz(e, 0, "T989")].entered_turn = -1
    before = len(e.zlist("hand", 0))
    deck_before = len(e.zlist("deck", 0))
    _attack_player(e, "T989")
    _drive_combat(e, may_yes=False)
    assert len(e.zlist("hand", 0)) == before
    assert len(e.zlist("deck", 0)) == deck_before


def test_blocked_no_search(rules):
    """形B: ブロックされた攻撃では発火しない（判別）。"""
    e = setup(rules, {"bz": ["T989"]}, {"bz": ["T004"]}, filler="T002")
    e.s.cards[_bz(e, 0, "T989")].entered_turn = -1
    before = len(e.zlist("hand", 0))
    deck_before = len(e.zlist("deck", 0))
    _attack_player(e, "T989")
    _drive_combat(e, block=True)
    assert len(e.zlist("hand", 0)) == before
    assert len(e.zlist("deck", 0)) == deck_before
