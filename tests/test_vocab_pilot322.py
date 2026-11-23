"""語彙パイロット第322弾: trigger_when_unblocked_and_extra_breaks_per_dynamo_tap。

対象は純粋2枚（multi-gap 行にも現れない）:
- dm19-003 電脳鉄人センジュオー（水・5・3000・グレートメカオー/ダイナモ）:
  ダイナモ / ブロックされない / 「攻撃してブロックされなかった時、このターンに
  「ダイナモ」能力を使うためにタップした自分のダイナモ１体につき１枚、
  シールドを余分にブレイクする」
- dm23ex2-045（ツインパクト。クリーチャー面は同名・同能力で「１つ、シールドを
  追加でブレイクする」と読む。呪文面 センジュ・チューンは S・トリガーで
  「自分の手札の数と同じ枚数のカードを引き、その後、こうして引いた枚数と
  同じ数、手札を捨てる」）

第321弾の when {event: attack_end, subject: self, target: player,
blocked: false} の直接拡張。追加ブレイクの数は「このターンにダイナモを
使うためにタップした自分のダイナモの体数」で、既存の履歴カウンタでは
表せない（hist:tap は攻撃・ブロック等のあらゆるタップを数える）。
そこでエンジン拡張:
- 新しい turn_count kind `dynamo_tap`（defs.py の TURN_COUNT_KINDS に追加）。
  op_modify が add_of（ダイナモだけが使う mod）を適用した時、発生源の
  cid を turn_counters["dynamo_tap:<player>"] に記録する（重複は数えない。
  タップはコスト／トリガー効果として先に済み、付与が使用の完了点）。
  _turn_count でリストの体数を返す。
- 形: trigger {event: attack_end, subject: self, target: player,
  blocked: false} → [{op: break, player: opp,
  count: {turn_count: {kind: dynamo_tap, owner: you}}}]
  （通常の1ブレイクは攻撃中に済んでおり、ここで余分に N 枚割る。N=0 でも
  余分のブレイク決定（choose_shields min 0）が出るが何も割らない）
- 副次的なエンジン修正（呪文面のため）: op_set_var は値が式
  （{count: ...} 等）の時は評価して束縛する。従来は辞書のまま束縛され
  {var:} の読みが len(辞書)＝1 になっていた（プローブで確認: 手札3枚で
  set_var した {count: {zone: hand}} が draw 1枚になっていた。
  dmx12b-044 / dmrp09-020 / dmx07-020 等の既存6件も同じ誤りで、
  この修正で正しい枚数になる）。リスト・数値・真偽値は従来どおり。
  呪文面の形: [set_var hand_n {count: {zone: hand, owner: you}},
  draw {var: hand_n}, discard {zone: hand, owner: you, count: {var: hand_n}}]
  （「引いた枚数」＝唱えた時点の手札枚数と同数）。

注意: プレイヤーへの攻撃ではバトルが発生しないため、ダイナモの
battle_start トリガーはセンジュオー自身の攻撃では誘発しない。ダイナモの
使用は「攻撃できる時」の activate か、他のクリーチャーのバトル開始時に
起きる。試験カードは T986（dm19-003 型）/ T987（センジュ・チューン型）。
"""
from pathlib import Path

import pytest
from conftest import setup

from dmsim.cards.defs import (card_yaml_files, load_rules, load_tables,
                              parse_card)
from tests._conv_cache import proto_card

TABLES = load_tables()


@pytest.fixture(scope="module")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def _keys(d):
    return [o["key"] for o in d["options"]]


def _defns(e, zone, player=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, player)]


def _bz(e, player, defn):
    return next(c for c in e.bz_tops(player) if e.s.cards[c].defn == defn)


def _set_sick_free(e, player, defn):
    e.s.cards[_bz(e, player, defn)].entered_turn = -1


SENJUOH_FORM = {
    "kind": "trigger",
    "when": {"event": "attack_end", "subject": "self",
             "target": "player", "blocked": False},
    "effect": [{"op": "break", "player": "opp",
                "count": {"turn_count": {"kind": "dynamo_tap",
                                         "owner": "you"}}}]}

TUNE_SPELL = [
    {"op": "set_var", "name": "hand_n",
     "value": {"count": {"zone": "hand", "owner": "you"}}},
    {"op": "draw", "count": {"var": "hand_n"}},
    # discard はマクロで move（to: graveyard, reason: discard）に展開される
    {"op": "move", "select": {"zone": "hand", "owner": "you",
                              "count": {"var": "hand_n"}},
     "to": "graveyard", "reason": "discard"},
]


def test_proto_parse_and_forms():
    c986 = parse_card(proto_card("T986"), TABLES)
    # dynamo キーワードの展開能力（activate＋battle_start トリガー）が先に並ぶ
    assert SENJUOH_FORM in c986.abilities
    assert c986.keywords == ["dynamo", "unblockable"]
    c987 = parse_card(proto_card("T987"), TABLES)
    assert c987.spell == TUNE_SPELL
    assert c987.keywords == ["s_trigger"]


def _drive_attacks(e, plan, limit=800):
    """plan: [(attacker_defn, target, battle_start_yes, [activate_defns])]。
    target は "player" か相手クリーチャーの defn。攻撃決定では activate を
    先に済ませ、battle_start の yes_no は現在の攻撃者の計画に従う。
    S・トリガーの宣言はすべて断る。計画が終わり次のステップに来たら止める。
    戻り値は運転中に観測した dynamo_tap:0 の最大体数（ターンが変わると
    turn_counters はリセットされるため、終わってから読んでは遅い）。"""
    steps = list(plan)
    cur = None
    max_taps = 0
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return max_taps
        # ターンが変わると turn_counters はリセットされるが、直前のターンの
        # 分は prev_counters に退避される。1回の advance の中で使用と
        # ターン交代が両方起きる場合があるので両方を見る。
        for store in (e.s.turn_counters, e.s.prev_counters):
            lst = store.get("dynamo_tap:0")
            if isinstance(lst, list):
                max_taps = max(max_taps, len(lst))
        kind = d["kind"]
        keys = _keys(d)
        if not steps and kind in ("charge", "main", "attack"):
            return max_taps
        if kind in ("charge", "main", "attack"):
            if kind == "attack" and steps:
                attacker, target, _, activates = steps[0]
                todo = [a for a in activates
                        if not e.s.cards[_bz(e, 0, a)].tapped]
                if todo:
                    hit = [i for i, x in enumerate(keys)
                           if x.startswith(f"activate:{todo[0]}:")]
                    assert hit, keys
                    e.answer([hit[0]])
                    continue
                tgt = "player" if target == "player" else target
                hit = [i for i, x in enumerate(keys)
                       if x == f"attack:{attacker}:{tgt}"]
                if hit and d["player"] == 0:
                    cur = attacker
                    steps.pop(0)
                    e.answer([hit[0]])
                    continue
            if "pass" in keys:
                e.answer([keys.index("pass")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind in ("block", "declare_block"):
            if "no_block" in keys:
                e.answer([keys.index("no_block")])
            else:
                e.answer(list(range(d.get("min", 0))))
        elif kind == "yes_no":
            want = next((s[2] for s in plan if s[0] == cur), False)
            e.answer([keys.index("yes" if want else "no")])
        elif kind == "choose_cards":
            e.answer(list(range(d.get("min", 0))))
        elif kind == "declare_strigger":
            e.answer([])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    raise AssertionError("attack drive did not settle")


def _shields(e):
    return len(e.zlist("shield", 1))


def test_senjuoh_no_dynamo_use_breaks_one(rr):
    """ダイナモを使っていなければ余分なブレイクは0枚（通常の1枚だけ）。"""
    e = setup(rr, {"bz": ["T986"]}, {}, filler="T002")
    _set_sick_free(e, 0, "T986")
    before = _shields(e)
    assert _drive_attacks(e, [("T986", "player", True, [])]) == 0
    assert _shields(e) == before - 1


def test_senjuoh_one_dynamo_use_breaks_two(rr):
    """activate で他のダイナモ1体がダイナモを使うと、余分に1枚割る。"""
    e = setup(rr, {"bz": ["T986", "R069"]}, {}, filler="T002")
    _set_sick_free(e, 0, "T986")
    before = _shields(e)
    assert _drive_attacks(e, [("T986", "player", False, ["R069"])]) == 1
    assert _shields(e) == before - 2


def test_senjuoh_two_dynamo_uses_break_three(rr):
    """ダイナモ2体が activate で使うと余分に2枚割る（通常1枚＋2枚）。"""
    e = setup(rr, {"bz": ["T986", "R068", "R069"]}, {}, filler="T002")
    _set_sick_free(e, 0, "T986")
    before = _shields(e)
    assert _drive_attacks(e, [("T986", "player", False, ["R068", "R069"])]) == 2
    assert _shields(e) == before - 3


def test_senjuoh_battle_start_use_counts(rr):
    """バトル開始時のダイナモ使用も数える。R068 がタップされた T004 を攻撃し、
    バトル開始時に T986 がダイナモを使う（T986 自身はタップするのでこの
    テストでは攻撃しない。余分ブレイクの端から端までは activate 側で固定）。
    注意: 同じバトル開始時にダイナモ2体が使うと、変更前のエンジンでも
    chars キャッシュの stale 表明で落ちる既知の不具合がある（T984/T985/
    R069 のみの再現で確認済み。第322弾の変更とは無関係のため、ここでは
    ドナー1体だけの形で固定し、不具合は docs に記録する）。"""
    e = setup(rr, {"bz": ["T986", "R068"]}, {"bz": ["T004"]},
              filler="T002")
    e.s.cards[_bz(e, 1, "T004")].tapped = True
    _set_sick_free(e, 0, "R068")
    assert _drive_attacks(e, [("R068", "T004", True, [])]) == 1
    assert _shields(e) == 5   # クリーチャーへの攻撃なのでシールドは割れない


def test_tapped_for_attack_does_not_count(rr):
    """判別: ダイナモが攻撃でタップしただけでは数えない（hist:tap との違い）。
    R069 が先に攻撃してタップし、その後 T986 が攻撃しても余分は0枚。"""
    e = setup(rr, {"bz": ["T986", "R069"]}, {}, filler="T002")
    _set_sick_free(e, 0, "T986")
    _set_sick_free(e, 0, "R069")
    before = _shields(e)
    assert _drive_attacks(e, [("R069", "player", False, []),
                              ("T986", "player", True, [])]) == 0
    assert _shields(e) == before - 2   # R069 の1枚＋T986 の1枚。余分は0枚


def test_tune_spell_draws_and_discards_hand_count(rr):
    """センジュ・チューン: 手札の数だけ引き、同じ数捨てる（set_var の式評価）。
    唱えた時点で手札は T001/T002 の2枚なので、2枚引いて2枚捨てる。"""
    e = setup(rr, {"hand": ["T987", "T001", "T002"],
                   "mana": ["T030", "T030", "T030", "T030"]},
              {}, filler="T001")
    deck0 = len(e.zlist("deck", 0))
    hand0 = len(e.zlist("hand", 0))
    assert hand0 == 3
    cast = False
    for _ in range(300):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 \
                and not cast and "play:T987" in keys:
            e.answer([keys.index("play:T987")])
            cast = True
            continue
        if "T987" in _defns(e, "graveyard", 0):
            break
        if d["kind"] == "choose_cards":
            e.answer(list(range(d.get("min", 0))))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d.get("min", 0))))
    assert cast
    # 唱えた分を除く手札2枚が基準: 2枚引いて2枚捨てるので手札は2枚のまま、
    # 山札は2枚減り、墓地は捨てた2枚＋唱えた T987 自身の3枚。
    assert len(e.zlist("hand", 0)) == 2
    assert len(e.zlist("deck", 0)) == deck0 - 2
    assert len(e.zlist("graveyard", 0)) == 3
    assert "T987" in _defns(e, "graveyard", 0)
