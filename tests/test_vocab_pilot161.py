"""語彙パイロット第161弾: attacked_this_turn_condition（このターン攻撃したか）— 新語彙なし。

「このターン、〜が攻撃していなければ／攻撃していれば」は、履歴カウンタ式
{turn_count: ...}（第3段・共通基盤）を条件に置いて表す。新語彙・エンジン変更なし。

- 攻撃できない形: 常在型の if に {cmp: [{turn_count: {kind: attack, owner, other?,
  filter?}}, "==", 0]} を置き、mod {deny: [attack_player, attack_creature]}
  （実カード dmbd17-009 の「墓地13枚より少なければ攻撃できない」と同じ条件つき常在型）。
  other: true で自分以外の攻撃を数える。原文に「自分の」とあれば owner: you、
  無ければ owner: any。「自分のパワー12000以上が攻撃していなければ」は
  filter: {power_ge: 12000}（other なし＝自分も含む）。
- 条件つき誘引形: ゲリランチャー型は常在型の if に
  {all: [{is_turn: opp}, {exists: {ref: self, filter: {tapped: true}}},
        {cmp: [{turn_count: {kind: attack_on, ref: self}}, "==", 0]}]}
  を足した must_be_attacked: true（第51弾）。
- 効果の条件形: 呪文・誘発の if / op if の cond に
  {cmp: [{turn_count: {kind: attack, owner: any}}, ">=", 1]}。
  「選んだクリーチャーが攻撃していたらターン終わりに破壊」は delayed_trigger の
  効果に {cmp: [{turn_count: {kind: attack_by, ref: <変数>}}, ">=", 1]} を置く。
"""
from pathlib import Path

import yaml
from conftest import setup, answer

from dmsim.cards.defs import load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_proto_parse():
    t292 = parse_card(_proto_card("T292"), TABLES)
    assert t292.abilities[0]["mod"]["deny"] == ["attack_player", "attack_creature"]
    t293 = parse_card(_proto_card("T293"), TABLES)
    assert t293.abilities[0]["mod"]["must_be_attacked"] is True
    parse_card(_proto_card("T294"), TABLES)


def _drive(e, stop, choose=None, max_steps=400):
    """stop(d) を満たす決定まで既定回答で進める。choose のキーがあればそれを優先する。"""
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = [o["key"] for o in d["options"]]
        if choose is not None and choose in keys:
            e.answer([keys.index(choose)])
            choose = None
            continue
        if stop(d):
            return d
        if "pass" in keys:
            e.answer([keys.index("pass")])
        elif d["kind"] == "block" and "no_block" in keys:
            e.answer([keys.index("no_block")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("stop decision not reached")


def _tap_ctrl(e, player, defn):
    """bz は共有ゾーンなので、コントローラーまで見て対象側のカードをタップする。"""
    for c in e.zlist("bz", player):
        if e.s.cards[c].defn == defn and e.s.cards[c].controller == player:
            e.s.cards[c].tapped = True
            return c
    raise AssertionError(defn)


def _cid_ctrl(e, player, defn):
    return next(c for c in e.zlist("bz", player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _attack_decision(d):
    return d["kind"] == "attack" and d["player"] == 0


def test_cannot_attack_until_another_attacks(rules):
    """様子見獣 T292: 他のクリーチャーが攻撃するまで攻撃できず、攻撃した後は攻撃できる。"""
    e = setup(rules, {"bz": ["T292", "T005"]}, {"bz": ["T001"]})
    d = _drive(e, _attack_decision)
    keys = [o["key"] for o in d["options"]]
    assert "attack:T005:player" in keys
    assert not any(k.startswith("attack:T292:") for k in keys), keys
    d = _drive(e, _attack_decision, choose="attack:T005:player")
    keys = [o["key"] for o in d["options"]]
    assert "attack:T292:player" in keys, keys


def test_conditional_taunt_lifts_after_being_attacked(rules):
    """条件誘引獣 T293: まだ攻撃されていなければ誘引が働き、一度攻撃されたら解ける。"""
    e = setup(rules, {"bz": ["T001", "T005"]}, {"bz": ["T293", "T001"]})
    _tap_ctrl(e, 1, "T293")
    _tap_ctrl(e, 1, "T001")
    t001 = _cid_ctrl(e, 0, "T001")
    d = _drive(e, _attack_decision)
    keys = [o["key"] for o in d["options"]]
    attacks = sorted(k for k in keys if k.startswith("attack:"))
    assert attacks == ["attack:T001:T293", "attack:T005:T293"], keys
    d = _drive(e, _attack_decision, choose="attack:T001:T293")
    assert e.s.cards[t001].zone == "graveyard"   # T001（2000）は T293（5000）とのバトルで破壊される
    keys = [o["key"] for o in d["options"]]
    assert "attack:T005:player" in keys, keys     # attack_on が 1 になり誘引は解ける
    assert "attack:T005:T001" in keys, keys


def _cast_t294(rules, attack: bool):
    e = setup(rules, {"bz": ["T005"], "hand": ["T294"], "mana": ["T291", "T001", "T001"]}, {"bz": []})
    t005 = _cid_ctrl(e, 0, "T005")
    answer(e, "charge", "pass")
    answer(e, "main", "play:T294")
    # ターンが相手に移るまで進める（ターン終わりの遅延誘発はその途中で解決される）。
    # 攻撃は途中の攻撃判断で choose により実行する（攻撃後は次の攻撃判断が来ないため、
    # 攻撃判断で止めずに相手のターンまで一気に進める）。
    _drive(e, lambda d: d["player"] == 1,
           choose="attack:T005:player" if attack else None)
    return e, t005


def test_delayed_destroy_if_attacked(rules):
    """終末スレイヤー呪文 T294: 選んだクリーチャーが攻撃していたら、ターン終わりに破壊される。"""
    e, t005 = _cast_t294(rules, attack=True)
    assert e.s.cards[t005].zone == "graveyard"


def test_delayed_destroy_skipped_if_not_attacked(rules):
    """攻撃していなければ、ターン終わりに破壊されない。"""
    e, t005 = _cast_t294(rules, attack=False)
    assert e.s.cards[t005].zone == "bz"
