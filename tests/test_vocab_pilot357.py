"""語彙パイロット第357弾: return_any_number（ドリフト）。

センサス（rejects 1,976件を取り直し）: pure の大半は範囲外
（gr_summon 147 / aura 108＝未承認 / hyperdimensional_zone 105 /
dragheart 45 / psychic_filter 45 / hyperdimensional_summon 41 /
out_of_game 23 / duelist_link 20 / outside_game 12 /
pandora_shift 4）。残りは pure 1〜4件の小家族が多数。
評価済み却下（第316〜320弾: negate_effects /
opponent_choice_branch / shield_grant /
cost_matching_selection / per_civilization_selection /
flying / delayed_return / draw_up_to / look_reorder /
does_not_untap / フィールド系）は再提案しない。
cost_may_per_count の残り1件（dmex17-031）は第346弾で
「コスト条項だけでは登録できない」と評価済みのため対象外。
本弾で個別に評価して見送った候補:
- unblocked_creature_attack（pure 1）: attack_unblocked
  イベントはプレイヤー対象の攻撃でしか発火しない
  （combat の phase 4）ため、クリーチャー対象への拡張は
  エンジン変更が要り「最小の語彙」ではない。
- has_ability_filter（pure 1）: 「マナ爆誕能力を持つ」
  「マーシャル・タッチ能力を持つ」の照合は能力保持フィルタ
  の新設が要り、対象も能力種別が混在して不均一。
- mana_tap_trigger（pure 1）: 支払いのマナタップの
  イベント化（エンジン変更）が前提。
- attack_end_trigger（pure 1、dmrp21-002）: 残る節は
  手札に戻してタマシードの上に置く重ね置きで別機構。
- must_attack_next_turn / must_attack_self_next_turn
  （各 pure 1）: 次の相手ターン中の全相手クリーチャーへの
  強制攻撃は第354弾の must_be_attacked（誘引）とは持続と
  対象が違い、両カードとも重い他条項が残る。
範囲内・未評価で最小の return_any_number
（pure 1件、multi にも現れない）を選定した。

対象は pure 1件すべて: dmex08-049 十極 ジョバンチュ /
Genesis of Drillball（ツインパクト）。partial は faces が
プレースホルダの stub で、未解決は unsupported の
return_any_number 1件だけ。クリーチャー面の他条項は
キーワードで表せる（ブロッカー / 相手プレイヤーを
攻撃できない＝ cannot_attack_player、いずれも登録済み
キーワード）。本弾は gap 本体の条項
「自分のターンの終わりに、コスト9のカードを好きな枚数、
自分の墓地から手札に戻す」の形を確立する（追加語彙なし）:

- ターン終了誘発 {event: turn_end, player: you} は
  dm10-041 等の登録先例どおり。
- 「好きな枚数」は choose {count: any} の既存イディオム
  （dm22-043 の登録形、dm24ex1-sp7 の partial 先例）
  → move {ref: pick, count: all} で手札へ。
- 「コスト9のカード」は filter {cost_le: 9, cost_ge: 9}
  （dmrp21-002 の partial で declared 値で使われた
  cost_le/cost_ge 対の固定値版）。

注意: 呪文面（Genesis of Drillball: 山札の上2枚を
シールド化＋手札に加える自分のシールドカードすべてに
次の自分のターンのはじめまで S・トリガーを与える）は
本弾の対象外。ラウンド392では呪文面も含めた全体形を
検証し、表せなければ refined gap で差し戻すこと。

proto T1073（049のクリーチャー面型）/ T1074（コスト9の
戻し対象フィクスチャ）/ T1075（コスト8の対照）。

注意: conftest を import すると DMSIM_SKIP_CONVERTED が
復活するので scenario.build を直接包む（第355弾の作法）。
"""
import copy
import os

os.environ.pop("DMSIM_SKIP_CONVERTED", None)

import pytest  # noqa: E402
from dmsim.cards.defs import load_rules, load_tables, parse_card  # noqa: E402
from dmsim.engine import scenario  # noqa: E402
from tests._conv_cache import proto_card  # noqa: E402

TABLES = load_tables()

FORM = [{"kind": "trigger",
         "when": {"event": "turn_end", "player": "you"},
         "effect": [
             {"op": "choose",
              "select": {"zone": "graveyard", "owner": "you",
                         "filter": {"cost_le": 9, "cost_ge": 9},
                         "count": "any"},
              "as": "pick"},
             {"op": "move",
              "select": {"ref": "pick", "count": "all"},
              "to": "hand", "reason": "return"}]}]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_form(rules):
    c = proto_card("T1073")
    assert c["abilities"] == FORM
    assert c["keywords"] == ["blocker", "cannot_attack_player"]
    d = parse_card(copy.deepcopy(c), TABLES)
    assert d.abilities == parse_card(
        {"id": "TX357", "name": "x", "types": ["creature"],
         "civs": ["light"], "cost": 3, "power": 4000,
         "keywords": ["blocker", "cannot_attack_player"],
         "abilities": copy.deepcopy(FORM)}, TABLES).abilities
    assert d.keywords == ["blocker", "cannot_attack_player"]


def test_form_raw_parse():
    d = parse_card({"id": "TX357", "name": "x",
                    "types": ["creature"], "civs": ["light"],
                    "cost": 3, "power": 4000,
                    "keywords": ["blocker", "cannot_attack_player"],
                    "abilities": copy.deepcopy(FORM)}, TABLES)
    # キーワードは parse で static に展開されるため、誘発は
    # メンバーシップで確認する（第356弾の作法）
    trig = [a for a in d.abilities if a.get("kind") == "trigger"]
    assert len(trig) == 1
    assert trig[0]["when"] == {"event": "turn_end", "player": "you"}
    assert trig[0]["effect"] == FORM[0]["effect"]


def _build(rules):
    return scenario.build(
        rules, {"p0": {"bz": ["T1073"],
                       "graveyard": ["T1074", "T1074", "T1075"]},
                "p1": {},
                "filler": "T002", "seed": 1, "deck_size": 20})


def _defns(e, zone, p):
    if zone == "bz":
        return sorted(e.cdef(c).id for c in e.bz_tops(p))
    return sorted(e.cdef(c).id for c in e.zlist(zone, p))


def _drive(e, picker, max_turn, limit=4000):
    """max_turn（開始ターン+2＝相手ターン終了後）まで進める。
    choose_cards 判断は picker(options) -> [index...] で答え、
    発火回数を返す。"""
    start = e.s.turn
    fired = 0
    for _ in range(limit):
        if e.s.turn >= start + max_turn:
            break
        d = e.advance()
        assert d is not None, "game ended"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "choose_cards":
            fired += 1
            e.answer(picker(d["options"]))
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    return fired


def _pick_defn(options, defn, n=None):
    # choose_cards の選択肢は key が "zone:<defn>:<n>" 形式
    idx = [i for i, o in enumerate(options)
           if o["key"].split(":")[1] == defn]
    return idx if n is None else idx[:n]


# ---------- 実挙動 ----------

def test_returns_chosen_cost9_cards_at_own_turn_end(rules):
    """自分のターンの終わりに、墓地のコスト9カードを
    好きな枚数（ここでは2枚とも）手札に戻せる。
    コスト8はフィルタで選べない。"""
    e = _build(rules)
    fired = _drive(e, lambda opts: _pick_defn(opts, "T1074"), 1)
    assert fired == 1
    assert _defns(e, "hand", 0).count("T1074") == 2
    assert _defns(e, "graveyard", 0) == ["T1075"]


def test_may_return_zero(rules):
    """「好きな枚数」は0枚でもよい（選ばなければ何も戻らない）。"""
    e = _build(rules)
    fired = _drive(e, lambda opts: [], 1)
    assert fired == 1
    assert _defns(e, "hand", 0).count("T1074") == 0
    assert _defns(e, "graveyard", 0) == ["T1074", "T1074", "T1075"]


def test_may_return_one_of_two(rules):
    """2枚あるうち1枚だけ戻すこともできる。"""
    e = _build(rules)
    fired = _drive(e, lambda opts: _pick_defn(opts, "T1074", 1), 1)
    assert fired == 1
    assert _defns(e, "hand", 0).count("T1074") == 1
    assert _defns(e, "graveyard", 0) == ["T1074", "T1075"]


def test_not_triggered_at_opponent_turn_end(rules):
    """相手のターンの終わりには誘発しない
    （開始ターン+2＝相手ターン終了後まで進めて発火は1回だけ）。"""
    e = _build(rules)
    fired = _drive(e, lambda opts: [], 2)
    assert fired == 1
    assert _defns(e, "graveyard", 0) == ["T1074", "T1074", "T1075"]
