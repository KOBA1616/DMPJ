"""語彙パイロット第364弾: blocking_power
（新規語彙: mod power_when への opponent_filter 追加）。

センサス（rejects 1,969件を取り直し）: pure 1,821件 /
multi 130件 / 空 gaps 18件。pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone
105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 /
duelist_link 20 / outside_game 12 / pandora_shift 4）。
残りは pure 1〜4件の小家族が多数で、評価済み却下
（第316〜320・355〜363弾: negate_effects /
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
state_condition_destruction /
cannot_be_tapped_by_opponent /
unblockable_only_when_attacking_creatures /
s_trigger_suppression / broken_shields_no_s_trigger /
civ_blocker / attack_limit_once_per_turn /
entered_turn_attack / conditional_s_trigger /
block_break / battle_does_not_occur_when_blocking /
battle_win_destroy 系）は再提案しない。
本弾で個別に評価して見送った候補:
blocker_cost_restriction（pure 1、dmr05-105。
be_blocked の deny はブロックする側のコストで
切り替えられず新語彙が要る）、reveal_hand（pure 2。
表向き手札という状態がエンジンに無く、公開そのものを
表す語彙が無い）、cannot_stack（pure 1、dmrp04m-s07。
「上に置くことはできない」の配置否定の mod が無い）、
summon_from_mana（pure 2。dmex15-a021 は split の
誤認修正待ち、dmr19-010 はマナから盤上へ重ねる op が
無く、2件で形が相異なり均一でない）、
shield_leave_protection（pure 2。no_leave は
バトルゾーンを離れる移動だけに効き、シールドゾーン
には及ばない）、turn_wide_attack_restriction
（pure 2。dmr09-037 は攻撃誘発の継続制限、
dm26ex4-cho033 は CIP の「このターン」制限で形が
相異なり、ターン全体への制限付与の語彙も無い）、
race_declaration（pure 2。種族の宣言そのものを表す
語彙が無い）、rarity_filter（pure 2。レアリティは
フィルタのキーに無い）。範囲内・未評価で最小の
blocking_power（pure 1件、multi にも現れない）を選定した:
dm34-025 ワダツミ・フィッシュ「進化ではない
クリーチャーをブロックしている時、このクリーチャーの
パワーは+2000される」。

結論は最小の新規語彙1つ: mod power_when に
opponent_filter（フィルタ）を追加する
（battle_power の opponent_filter、第122弾と同義）。
既存部品だけでは正確に表せない:
- power_when {when: blocking}（第131弾）は「ブロック
  している時」の範囲（ブロック宣言から攻撃の終わり
  まで）そのものだが、バトルの相手を参照するキーが
  無く、無条件に +2000 してしまう（進化クリーチャーを
  ブロックした時まで上がる）。
- battle_power {opponent_filter} は相手条件は付け
  られるが、効くのはバトル中だけであり、「ブロック
  している時」とは範囲が異なる（エンジンの docstring
  も両者を区別している）ため流用は近似になる。
- static の if は発生源自身やゾーンの存在条件しか
  見られず、「いま自分がブロックしている攻撃
  クリーチャー」を指せない。
opponent_filter の意味論: when: blocking では攻撃
クリーチャー、when: attacking では攻撃対象の
クリーチャーが「相手」。相手がプレイヤーの時と
when: not_attacking では相手が定まらないため付かない。
defs の検証・schema（card.schema.json 再生成）に
キーを追加し、エンジンは core._power_when で照合する。
新規の状態フィールドは無いため Rust の state.rs
ミラーは不要（rust_schema_sync は状態フィールドのみ）。

proto T1095（dm34-025 型）/ T1096（進化ではない
パワー4000アタッカー）/ T1097（進化クリーチャーの
パワー4000アタッカー）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接包む（第319弾以降の
作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import DefError, load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

STATIC = {"kind": "static", "affects": "self",
          "mod": {"power_when": {"amount": 2000, "when": "blocking",
                                 "opponent_filter":
                                     {"not_types": ["evolution"]}}}}
FORM = [STATIC]
KEYWORDS = ["blocker", "cannot_attack"]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1095")
    assert c["abilities"] == FORM
    assert c["keywords"] == KEYWORDS
    assert c["types"] == ["creature"]
    assert c["cost"] == 3 and c["power"] == 3000
    d = parse_card(copy.deepcopy(c), TABLES)
    assert STATIC in d.abilities
    for tid in ("T1096", "T1097"):
        parse_card(proto_card(tid), TABLES)


def test_form_raw_parse():
    d = parse_card({"id": "TX364", "name": "x",
                    "types": ["creature"], "civs": ["water"],
                    "cost": 3, "power": 3000,
                    "races": ["フィッシュ", "オリジン"],
                    "keywords": list(KEYWORDS),
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    assert STATIC in d.abilities


def test_bad_opponent_filter_rejected():
    """opponent_filter の中身は通常のフィルタとして検証される。"""
    bad = {"id": "TX364B", "name": "x", "types": ["creature"],
           "civs": ["water"], "cost": 3, "power": 3000,
           "abilities": [{"kind": "static", "affects": "self",
                          "mod": {"power_when":
                                  {"amount": 2000, "when": "blocking",
                                   "opponent_filter": {"bogus": 1}}}}]}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def _build(rules, p0, p1):
    return scenario.build(rules, {"p0": p0, "p1": p1,
                                  "filler": "T002", "seed": 1,
                                  "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _cid(e, tid, p):
    return next(c for c in e.bz_tops(p) if e.cdef(c).id == tid)


def test_chars_power_blocking_non_evolution_vs_evolution(rules):
    """特性レベル: ブロック中（攻撃タスクが blocked で
    自分が target）のパワーは、攻撃クリーチャーが進化で
    なければ 3000+2000、進化なら 3000 のまま。
    攻撃タスクが無ければ常に 3000。"""
    e = _build(rules, {"bz": ["T1095"]}, {"bz": ["T1096", "T1097"]})
    blk = _cid(e, "T1095", 0)
    atk_ne = _cid(e, "T1096", 1)
    atk_ev = _cid(e, "T1097", 1)
    assert e.chars(blk)["power"] == 3000          # 平常時
    e.s.tasks.append({"t": "attack", "attacker": e.s.ref(atk_ne),
                      "target": e.s.ref(blk), "blocked": True,
                      "phase": 4, "cp": False})
    assert e.chars(blk)["power"] == 5000          # 非進化をブロック中
    e.s.tasks.pop()
    e.s.tasks.append({"t": "attack", "attacker": e.s.ref(atk_ev),
                      "target": e.s.ref(blk), "blocked": True,
                      "phase": 4, "cp": False})
    assert e.chars(blk)["power"] == 3000          # 進化をブロック中は付かない
    e.s.tasks.pop()
    assert e.chars(blk)["power"] == 3000


def _drive_attack(e, attacker, block_with=None):
    """p1 の attacker でプレイヤーを攻撃する。block_with が
    あればそのブロッカー（p0）でブロックし、無ければ
    ブロックしない。攻撃したターンの2つ先のターンまで
    進めて状態を返す（第359弾の作法）。"""
    state = {"attacked": False, "attack_turn": None}
    for _ in range(1500):
        if state["attacked"] and e.s.turn >= state["attack_turn"] + 2:
            break
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


def test_blocks_non_evolution_attacker_wins_with_bonus(rules):
    """進化ではないパワー4000の攻撃をブロックすると、
    +2000 を受けた 5000 でバトルに勝ち、攻撃側が破壊
    される。ワダツミ型は残る。"""
    e = _build(rules, {"bz": ["T1095"]}, {"bz": ["T1096"]})
    st = _drive_attack(e, "T1096", block_with="T1095")
    assert st["attacked"]
    assert "T1096" in _defns(e, "graveyard", 1)   # 5000 に負ける
    assert "T1095" in _defns(e, "bz", 0)


def test_blocks_evolution_attacker_no_bonus_loses(rules):
    """進化クリーチャーのパワー4000の攻撃をブロック
    しても +2000 は付かず、3000 のままバトルに負けて
    破壊される。攻撃側は残る。"""
    e = _build(rules, {"bz": ["T1095"]}, {"bz": ["T1097"]})
    st = _drive_attack(e, "T1097", block_with="T1095")
    assert st["attacked"]
    assert "T1095" in _defns(e, "graveyard", 0)   # 3000 のまま負ける
    assert "T1097" in _defns(e, "bz", 1)


def test_no_block_no_bonus_shield_breaks(rules):
    """ブロックしなければ修整は関係なく、シールドが
    1枚ブレイクされ、両者ともバトルゾーンに残る。"""
    e = _build(rules, {"bz": ["T1095"]}, {"bz": ["T1096"]})
    shields = len(e.zlist("shield", 0))
    st = _drive_attack(e, "T1096", block_with=None)
    assert st["attacked"]
    assert len(e.zlist("shield", 0)) == shields - 1
    assert "T1095" in _defns(e, "bz", 0)
    assert "T1096" in _defns(e, "bz", 1)
