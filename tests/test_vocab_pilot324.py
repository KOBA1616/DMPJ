"""語彙パイロット第324弾: 「自分のクリーチャー１体はその数（自分の
クリーチャーの数）のシールドを追加でブレイクする」（breaks_equal_creature_count）
— エンジン拡張（スキーマのみ。実行時の新規評価はなし）。

センサス（rejects 2,047件を取り直し）: pure 1,898件 / multi 131件 /
空 gaps 18件（全て第312〜315弾の監査で別ブロッカー確認済み）。
pure の大半は範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 105 / dragheart 45 / psychic_filter 45 /
hyperdimensional_summon 41 / out_of_game 23 / duelist_link 20 /
outside_game 12＝対象外化済み / pandora_shift 4）か評価済み
DEEP・重い・延期（第318〜323弾の記録参照）。delayed_return /
draw_up_to / look_reorder / flying / does_not_untap は第320・321弾で
却下済みで再提案しない。第323弾の記録でドリフト候補として残した
**breaks_equal_creature_count（純粋2件、multi-gap 行にも現れない）**
を選定した。

対象は dm24ex2-024 / dm26ex4-cho021（同名カード
ジョジョジョ・マキシマムの2印刷）。両行とも partial は dm24ex2-024
のみ骨格あり（unsupported は breaks_equal_creature_count だけ。
dm26ex4-cho021 は partial 空）。by_product で原文照合済み。
- dm24ex2-024（無色・コスト9・マナ1）: 「G・ゼロ：バトルゾーンまたは
  マナゾーンに自分のジョーカーズが合計11枚以上あれば、この呪文をコストを
  支払わずに唱えてもよい。自分のクリーチャーを数える。このターン、
  自分のクリーチャー１体はその数のシールドを追加でブレイクし、
  そのクリーチャーの攻撃中、相手は呪文を唱えられない。」
- dm26ex4-cho021（同名・同コスト）: G・ゼロの文言が
  「自分の、ジョーカーズとマナゾーンにあるジョーカーズ・カードが
  合計11以上なら」と異なる（by_product の原文のまま。効果は同一）。

結論: エンジン拡張（スキーマのみ）。3つの既存の形の組み合わせだが、
1点だけスキーマの拡張が必要だった:
- breaks_add の辞書形に {var: 名前} を許可（dmsim/cards/defs.py
  Checker.mod。第324弾）。実行時は op_modify の _bake_refs が生成時に
  数値へ焼くため core.py の変更は不要。{amount, count} 形（第170弾）
  は攻撃時に数え直すためここでは使えない（解決時の数を固定するため）。
  なお {var:} の読みが1になる latent bug は第322弾で修正済み。
- G・ゼロ: free_if {cmp: [{count: {zone: [bz, mana], owner: you,
  filter: {race_has: ジョーカーズ}}}, '>=', 11]}（free_if の cmp＋
  count 形は既存。zone の配列は zones_of が受ける）。
- 数えて付与: [set_var n {count: {zone: bz, owner: you,
  filter: {types: [creature]}}}; choose {zone: bz, owner: you,
  filter: {types: [creature]}, count: 1} as chosen;
  modify {ref: chosen} {breaks_add: {var: n}} end_of_turn]
  （breaks_add の {var:} は op_modify の _bake_refs で生成時に数値へ
  焼かれるため、解決時の数が固定される。第322弾の set_var 式評価修正が
  前提。動的な count 形（第170弾の {amount, count}）は攻撃時に数え直す
  ためここでは使わない）。
- 攻撃中の呪文封じ: delayed_trigger {event: attack,
  subject: {ref: chosen}} → [modify {zone: hand, owner: opp,
  filter: {types: [spell]}} {deny: [cast]} during_attack]
  duration end_of_turn, once: false（遅延誘発は subject: {ref: 変数名}
  で「その〜」を指せる。deny cast の during_attack 形は
  dmex13-064 の先例。once: false は「そのクリーチャーの攻撃中」が
  攻撃のたびに適用されるため）。

プロト T990（dm24ex2-024 型）/ T991（dm26ex4-cho021 型。呪文部分は
同一で G・ゼロの文言だけが違う）。次の空きは T992。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card
from tests._conv_cache import proto_card

TABLES = load_tables()
IDS = ("T990", "T991")

FREE_IF = {
    "cmp": [{"count": {"zone": ["bz", "mana"], "owner": "you",
                       "filter": {"race_has": "ジョーカーズ"}}},
            ">=", 11]}

SPELL = [
    {"op": "set_var", "name": "n",
     "value": {"count": {"zone": "bz", "owner": "you",
                         "filter": {"types": ["creature"]}}}},
    {"op": "choose",
     "select": {"zone": "bz", "owner": "you",
                "filter": {"types": ["creature"]}, "count": 1},
     "as": "chosen"},
    {"op": "modify", "select": {"ref": "chosen"},
     "mod": {"breaks_add": {"var": "n"}}, "duration": "end_of_turn"},
    {"op": "delayed_trigger",
     "when": {"event": "attack", "subject": {"ref": "chosen"}},
     "effect": [{"op": "modify",
                 "select": {"zone": "hand", "owner": "opp",
                            "filter": {"types": ["spell"]}},
                 "mod": {"deny": ["cast"]},
                 "duration": "during_attack"}],
     "duration": "end_of_turn", "once": False},
]


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_parse_and_forms():
    for cid in IDS:
        card = proto_card(cid)
        assert card["free_if"] == FREE_IF, cid
        assert card["spell"] == SPELL, cid
        d = parse_card(card, TABLES)
        assert d.free_if is not None
        assert len(d.spell) == 4


def _keys(d):
    return [o["key"] for o in d["options"]]


def _bz(e, p, defn):
    return next(c for c in e.bz_tops(p) if e.s.cards[c].defn == defn)


def _main_keys(e, max_steps=30):
    """次の main 決定（player 0）の選択肢を返す。"""
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended before main"
        if d["kind"] == "main" and d.get("player") == 0:
            return _keys(d)
        keys = _keys(d)
        e.answer([keys.index("pass")] if "pass" in keys
                 else list(range(d["min"])))
    raise AssertionError("main decision did not appear")


def test_free_if_with_eleven_jokers(rules):
    """G・ゼロ: ジョーカーズがバトルゾーン＋マナゾーンで合計11枚あれば
    無料で唱えられる（マナはタップされない）。"""
    e = setup(rules, {"hand": ["T990"], "mana": ["T408"] * 11}, {})
    keys = _main_keys(e)
    assert "play:T990:free" in keys
    e.answer([keys.index("play:T990:free")])
    for _ in range(60):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main", "attack"):
            break
        keys = _keys(d)
        if d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert all(not e.s.cards[c].tapped for c in e.zlist("mana", 0))


def test_free_if_needs_eleven(rules):
    """G・ゼロ: ジョーカーズが10枚では無料選択肢は出ない（通常唱えは出る）。"""
    e = setup(rules, {"hand": ["T990"], "mana": ["T408"] * 10}, {})
    keys = _main_keys(e)
    assert "play:T990:free" not in keys
    assert "play:T990" in keys


def _cast_spell(e, choose_key="bz:T001:"):
    """main で T990 を唱え、クリーチャーを1体選ぶ。pay_mana・
    choose_cards に汎用的に答える。"""
    cast = False
    for _ in range(120):
        d = e.advance()
        assert d is not None, "game ended before cast"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and not cast \
                and "play:T990" in keys:
            e.answer([keys.index("play:T990")])
            cast = True
            continue
        if cast and d["kind"] == "choose_cards" \
                and any(k.startswith("bz:") for k in keys):
            hit = [i for i, k in enumerate(keys)
                   if k.startswith(choose_key)]
            assert hit, keys
            e.answer([hit[0]])
            return
        if d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("spell did not resolve")


def _attack_player(e, attacker_defn):
    for _ in range(30):
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


def _drive_combat(e, probe=None, max_steps=200):
    """攻撃の解決が終わるまで進める。probe(cid) が与えられれば、
    攻撃中の各決定でそのカードの cast 可否を記録する。"""
    probes = []
    for _ in range(max_steps):
        d = e.advance()
        if d is None or d["kind"] in ("charge", "main", "attack"):
            return probes
        if probe is not None:
            probes.append(e.permits(probe, "cast"))
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


def test_spell_grants_breaks_equal_creature_count(rules):
    """呪文: 自分のクリーチャーが3体いれば、選んだ1体は余分に3枚割る
    （通常1枚＋3枚＝4枚）。"""
    e = setup(rules, {"bz": ["T001", "T002", "T004"],
                      "hand": ["T990"], "mana": ["T030"] * 9}, {})
    for dfn in ("T001", "T002", "T004"):
        e.s.cards[_bz(e, 0, dfn)].entered_turn = -1
    _cast_spell(e)
    before = len(e.zlist("shield", 1))
    _attack_player(e, "T001")
    _drive_combat(e)
    assert len(e.zlist("shield", 1)) == before - 4


def test_spell_denies_cast_during_chosen_attack(rules):
    """呪文: 選んだクリーチャーの攻撃中、相手は呪文を唱えられない。
    攻撃が終われば唱えられるようになる。"""
    e = setup(rules, {"bz": ["T001", "T002"],
                      "hand": ["T990"], "mana": ["T030"] * 9},
              {"hand": ["T006"]})
    for dfn in ("T001", "T002"):
        e.s.cards[_bz(e, 0, dfn)].entered_turn = -1
    t006 = next(c for c in e.zlist("hand", 1)
                if e.s.cards[c].defn == "T006")
    assert e.permits(t006, "cast")
    _cast_spell(e)
    _attack_player(e, "T001")
    probes = _drive_combat(e, probe=t006)
    assert probes and not all(probes), probes
    assert e.permits(t006, "cast")


def test_spell_no_denial_for_unchosen_attack(rules):
    """呪文: 選ばれなかったクリーチャーの攻撃中は、相手は呪文を唱えられる
    （対照）。"""
    e = setup(rules, {"bz": ["T001", "T002"],
                      "hand": ["T990"], "mana": ["T030"] * 9},
              {"hand": ["T006"]})
    for dfn in ("T001", "T002"):
        e.s.cards[_bz(e, 0, dfn)].entered_turn = -1
    t006 = next(c for c in e.zlist("hand", 1)
                if e.s.cards[c].defn == "T006")
    _cast_spell(e)
    _attack_player(e, "T002")
    probes = _drive_combat(e, probe=t006)
    assert probes and all(probes), probes
