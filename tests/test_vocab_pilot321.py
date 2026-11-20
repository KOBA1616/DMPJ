"""語彙パイロット第321弾: 「相手プレイヤーを攻撃してブロックされなかった時」
（trigger_when_unblocked）— ドリフト（attack_end の blocked: false 照合）。

センサス（rejects 2,053件を取り直し）: pure 1,906件 / multi 131件 /
空 gaps 18件（全て第312〜315弾の監査で別ブロッカー確認済み）。
pure の大半は範囲外（gr_summon 147 / aura 108＝未承認 /
hyperdimensional_zone 112 / dragheart 45 / psychic_filter 46 /
hyperdimensional_summon 42 / out_of_game 23 / duelist_link 20 /
outside_game 12＝対象外化済み / pandora_shift 4）か評価済み
DEEP・重い・延期（第318〜320弾の記録参照）。フィールド系と
does_not_untap（2件）は第316・318弾の評価どおり却下。
flying / delayed_return / draw_up_to / look_reorder は
第319・320弾で却下済み。範囲内・未評価で最小の
trigger_when_unblocked（純粋2件、multi-gap 行にも現れない）を選定した。

対象は dm19-050 大鉄漢シルバスターズ / dm19-069 食いしん坊
チャロック。両行とも partial は骨格（abilities 無し）で、
未解決は「このクリーチャーが相手プレイヤーを攻撃して
ブロックされなかった時」の1節のみ（notes は「ダイナモ能力の
仕組みを表す語彙が無い」としているが、ダイナモは第76弾で
keywords.yaml 定義済み）。

結論: ドリフト（追加語彙なし）。「ブロックされなかった時」は
attack_end レコードの blocked: false 照合で書ける
（第175弾 T385 / 第219弾で確立、登録先例は同じダイナモの
dm20-016 風使いのシャイアン＝attack_end {subject: self,
target: player, blocked: false} そのもの）:
- 形A（dm19-050）: trigger {event: attack_end, subject: self,
  target: player, blocked: false} → may [draw 1]。
- 形B（dm19-069）: 同じ when → may [move {zone: deck,
  from_top: 1} to mana, reason: put]。

プロト T984（形A）/ T985（形B）。次の空きは T986。
"""
import pytest
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card
from tests._conv_cache import proto_card

TABLES = load_tables()
IDS = ("T984", "T985")

FORM_A = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "may", "body": [{"op": "draw", "count": 1}]}]}
FORM_B = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "may", "body": [
        {"op": "move",
         "select": {"zone": "deck", "owner": "you", "from_top": 1},
         "to": "mana", "reason": "put"}]}]}


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def test_proto_parse_and_forms():
    for cid, form in (("T984", FORM_A), ("T985", FORM_B)):
        card = proto_card(cid)
        assert card["abilities"] == [form], cid
        assert card["keywords"] == ["dynamo"], cid
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


def _drive_combat(e, block=False, may_yes=True, max_steps=160):
    """攻撃の解決が終わる（次の charge / main / attack 決定か
    ゲーム終了）まで進める。block=True なら相手の T004 で
    ブロックさせる。yes_no（may の諮問）には may_yes で答える。"""
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
        elif d["kind"] == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("combat did not settle")


def test_unblocked_draws(rules):
    """形A: ブロックされなかった攻撃の終わりに1枚引ける。"""
    e = setup(rules, {"bz": ["T984"]}, {}, filler="T002")
    e.s.cards[_bz(e, 0, "T984")].entered_turn = -1
    before = len(e.zlist("hand", 0))
    _attack_player(e, "T984")
    _drive_combat(e)
    assert len(e.zlist("hand", 0)) == before + 1


def test_unblocked_draw_may_decline(rules):
    """形A: 「引いてもよい」ので辞退できる（対照）。"""
    e = setup(rules, {"bz": ["T984"]}, {}, filler="T002")
    e.s.cards[_bz(e, 0, "T984")].entered_turn = -1
    before = len(e.zlist("hand", 0))
    _attack_player(e, "T984")
    _drive_combat(e, may_yes=False)
    assert len(e.zlist("hand", 0)) == before


def test_blocked_no_draw(rules):
    """形A: ブロックされた攻撃では発火しない（判別）。"""
    e = setup(rules, {"bz": ["T984"]}, {"bz": ["T004"]}, filler="T002")
    e.s.cards[_bz(e, 0, "T984")].entered_turn = -1
    before = len(e.zlist("hand", 0))
    _attack_player(e, "T984")
    _drive_combat(e, block=True)
    assert len(e.zlist("hand", 0)) == before


def test_unblocked_mana_charge(rules):
    """形B: ブロックされなかった攻撃の終わりに山札の上1枚を
    マナゾーンに置ける。"""
    e = setup(rules, {"bz": ["T985"]}, {}, filler="T002")
    e.s.cards[_bz(e, 0, "T985")].entered_turn = -1
    before = len(e.s.zones["mana"][0])
    deck_before = len(e.zlist("deck", 0))
    _attack_player(e, "T985")
    _drive_combat(e)
    assert len(e.s.zones["mana"][0]) == before + 1
    assert len(e.zlist("deck", 0)) == deck_before - 1


def test_blocked_no_mana_charge(rules):
    """形B: ブロックされた攻撃では発火しない（判別）。"""
    e = setup(rules, {"bz": ["T985"]}, {"bz": ["T004"]}, filler="T002")
    e.s.cards[_bz(e, 0, "T985")].entered_turn = -1
    before = len(e.s.zones["mana"][0])
    _attack_player(e, "T985")
    _drive_combat(e, block=True)
    assert len(e.s.zones["mana"][0]) == before
