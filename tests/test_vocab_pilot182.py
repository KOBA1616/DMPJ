"""語彙パイロット第182弾: play_restriction（実行制限）。

「〜を実行できない」「〜を出せない」は常在型の範囲付与（affects）＋mod deny の
イディオムで表す。核は既存語彙で、回数制限だけ新しい deny 辞書形を追加した。
- 常在型: {kind: static, affects: {zone: hand, owner, filter}, mod: {deny: [summon, cast]}}
  （filter の式値は _subject_match が解決時に計算する。「自分の手札の枚数以下」は
  cost_le: {count: {zone: hand, owner: opp}}。「自分のターン中」は static の if: {is_turn: you}。
  S・トリガー使用禁止は affects {zone: shield}＋deny: [s_trigger]）。
- 期間つき（「次の相手のターン中」）: CIP 誘発から op modify（dynamic: true、
  duration: until_next_own_turn_start）。
- 回数制限（新語彙）: deny: [{action: summon, max_per_turn: 1, count: enter}]。
  そのターンに hist:<count>:<controller> が max_per_turn 以上なら禁止。
  「出す」＝バトルゾーンへの出現全般なので count: enter を明記する。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()
PROTOS = ("T418", "T419", "T420", "T421", "T422", "T423")


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in PROTOS:
        assert parse_card(_proto_card(cid), TABLES) is not None
    t419 = parse_card(_proto_card("T419"), TABLES)
    static = next(a for a in t419.abilities
                  if a["kind"] == "static" and isinstance(a.get("affects"), dict))
    assert static["affects"]["filter"]["cost_le"] == {"count": {"zone": "hand", "owner": "opp"}}
    assert static["mod"] == {"deny": ["summon", "cast"]}
    assert len([a for a in t419.abilities if a["kind"] == "trigger"]) == 2
    t421 = parse_card(_proto_card("T421"), TABLES)
    trig = next(a for a in t421.abilities if a["kind"] == "trigger")
    deny = trig["effect"][0]["mod"]["deny"]
    assert deny == [{"action": "summon", "max_per_turn": 1, "count": "enter"},
                    {"action": "enter_bz", "max_per_turn": 1, "count": "enter"}]
    assert parse_card(_proto_card("T418"), TABLES).keywords == ["triple_breaker"]
    assert parse_card(_proto_card("T422"), TABLES).keywords == ["blocker", "double_breaker"]


def test_invalid_max_per_turn():
    base = {"id": "test-pr-bad", "name": "試験制限不良", "types": ["creature"],
            "civs": ["water"], "cost": 3,
            "source": {"official": "test-pr-bad", "review": "pending"}}
    for bad in ({"deny": [{"action": "summon", "max_per_turn": 0}]},
                {"deny": [{"action": "summon", "max_per_turn": "1"}]},
                {"deny": [{"action": "summon", "max_per_turn": 1, "count": "bogus"}]},
                {"deny": [{"action": "summon", "max_per_turn": 1, "other_key": 1}]}):
        with pytest.raises(DefError):
            parse_card({**base, "abilities": [{"kind": "static", "affects": "self", "mod": bad}]}, TABLES)


def _cid(e, player, defn, zone="bz"):
    return next(c for c in e.zlist(zone, player)
                if e.s.cards[c].defn == defn and e.s.cards[c].controller == player)


def _drive(e, want, max_steps=600):
    """want(d, keys) が真になるまで既定回答で進める。決定を返して止まる。"""
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = [o["key"] for o in d["options"]]
        if want(d, keys):
            return d, keys
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")] if "no" in keys else [0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("condition never met")


def _play_p0(e, tid, max_steps=400):
    """p0 が手札から tid を出す（任意の誘発には no で答える）。"""
    played = False
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d["player"] == 0 and not played and f"play:{tid}" in keys:
            played = True
            e.answer([keys.index(f"play:{tid}")])
            continue
        if played and (d["player"] != 0 or d["kind"] == "attack"):
            return   # 出した側のメインが終わった = CIP まで解決済み
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")] if "no" in keys else [0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError(f"{tid} was never played")


def test_t418_non_light_cannot_play(rules):
    """T418: 光ではないクリーチャー／呪文は誰も実行できない。光は実行できる。"""
    e = setup(rules, {"bz": ["T418"], "hand": ["T001"], "mana": ["T001", "T001"]},
              {"hand": ["T001", "T004"], "mana": ["T004", "T004", "T004"]})
    t001_me = _cid(e, 0, "T001", "hand")
    t001_opp = _cid(e, 1, "T001", "hand")
    t004_opp = _cid(e, 1, "T004", "hand")
    assert not e.permits(t001_me, "summon")
    assert not e.permits(t001_opp, "summon")
    assert e.permits(t004_opp, "summon")
    # 自分のメイン: 光でない T001 は選択肢に出ない（メイン決定自体が pass だけになり自動回答される）
    assert "play:T001" not in [o["key"] for o in e._play_options(0)]
    # 相手ターン: T004 は出せるが T001 は出せない
    d, keys = _drive(e, lambda d, k: d["kind"] == "main" and d["player"] == 1)
    assert "play:T004" in keys and "play:T001" not in keys
    e.answer([keys.index("play:T004")])
    _drive(e, lambda d, k: e.s.cards[t004_opp].zone == "bz")
    assert e.s.cards[t004_opp].zone == "bz"
    assert e.s.cards[t001_opp].zone == "hand"


def test_t419_hand_size_cap(rules):
    """T419: 相手は自分の手札の枚数以下のコストを実行できない（境界つき）。"""
    e = setup(rules, {"bz": ["T419"]}, {"hand": ["T001", "T004"]})
    assert not e.permits(_cid(e, 1, "T001", "hand"), "summon")   # コスト2 <= 手札2
    assert e.permits(_cid(e, 1, "T004", "hand"), "summon")       # コスト3 > 手札2
    e = setup(rules, {"bz": ["T419"]}, {"hand": ["T003", "T001"]})
    assert not e.permits(_cid(e, 1, "T003", "hand"), "cast")     # 呪文コスト2 <= 手札2


def test_t419_draw_on_opponent_play(rules):
    """T419: 相手が実行した時、自分は2枚引く。ドロー後の手札3枚ではコスト3が不可、コスト6が可。"""
    e = setup(rules, {"bz": ["T419"]},
              {"hand": ["T414", "T004"], "mana": ["T004", "T004", "T004", "T020", "T020", "T020"]})
    t414 = _cid(e, 1, "T414", "hand")
    t004 = _cid(e, 1, "T004", "hand")
    played = False
    for _ in range(600):
        if len(e.zlist("hand", 0)) == 2 and e.s.cards[t414].zone == "bz":
            break
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "main" and d["player"] == 1 and not played:
            assert "play:T414" in keys and "play:T004" not in keys   # ドロー後3枚: 6可・3不可
            played = True
            e.answer([keys.index("play:T414")])
        elif d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")] if "no" in keys else [0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    else:
        raise AssertionError("draw trigger never resolved")
    assert played
    assert len(e.zlist("hand", 0)) == 2        # 相手の実行による2ドロー
    assert e.s.cards[t414].zone == "bz"
    assert e.s.cards[t004].zone == "hand"      # コスト3は出せなかった


def test_t420_bounce_and_next_turn_power_cap(rules):
    """T420: CIPで相手パワー5000以下を全バウンス＋次の相手のターン中そのパワーを出せない。"""
    e = setup(rules, {"hand": ["T420"], "mana": ["T003"] * 8},
              {"bz": ["T001", "T004"], "hand": ["T040"], "mana": ["T003"] * 7})
    t001 = _cid(e, 1, "T001")
    t004 = _cid(e, 1, "T004")
    t040 = _cid(e, 1, "T040", "hand")
    _play_p0(e, "T420")
    assert e.s.cards[t001].zone == "hand" and e.s.cards[t004].zone == "hand"
    assert e.s.cards[_cid(e, 0, "T420")].zone == "bz"
    # 相手ターン: パワー6000の T040 は出せるが、パワー5000以下の2体は出せない
    d, keys = _drive(e, lambda d, k: d["kind"] == "main" and d["player"] == 1)
    assert "play:T040" in keys and "play:T001" not in keys and "play:T004" not in keys
    e.answer([keys.index("play:T040")])
    _drive(e, lambda d, k: e.s.cards[t040].zone == "bz")
    assert e.s.cards[t040].zone == "bz"
    # 自分の次のターン開始で制限は切れる
    d, keys = _drive(e, lambda d, k: d["kind"] == "charge" and d["player"] == 0)
    assert e.permits(t001, "summon") and e.permits(t001, "enter_bz")


def test_t421_one_creature_per_turn(rules):
    """T421: 次の相手のターン中、相手はクリーチャーを1体までしか出せない。
    呪文は制限されないので、1体出した後の相手メインは呪文の選択肢で再提示され、
    そこで2体目の不可と permits を確認できる。"""
    e = setup(rules, {"hand": ["T421"], "mana": ["T004"] * 4 + ["T020"] * 3},
              {"hand": ["T001", "T004", "T030", "T003"],
               "mana": ["T001", "T001", "T004", "T004", "T004", "T003", "T003"]})
    t001 = _cid(e, 1, "T001", "hand")
    t004 = _cid(e, 1, "T004", "hand")
    t030 = _cid(e, 1, "T030", "hand")
    _play_p0(e, "T421")
    assert e.permits(t001, "summon")   # まだ1体も出していない
    d, keys = _drive(e, lambda d, k: d["kind"] == "main" and d["player"] == 1)
    assert "play:T001" in keys
    e.answer([keys.index("play:T001")])
    _drive(e, lambda d, k: e.s.cards[t001].zone == "bz")
    assert e.s.cards[t001].zone == "bz"
    # 1体出した後の相手メイン: 呪文は出せるが、2体目のクリーチャーは出せない
    d, keys = _drive(e, lambda d, k: d["kind"] == "main" and d["player"] == 1)
    assert "play:T003" in keys
    assert "play:T004" not in keys and "play:T030" not in keys and "play:T001" not in keys
    assert not e.permits(t004, "summon") and not e.permits(t004, "enter_bz")
    assert not e.permits(t030, "summon")
    # 自分の次のターン開始で制限は切れる
    e.answer([keys.index("pass")])
    d, keys = _drive(e, lambda d, k: d["kind"] == "charge" and d["player"] == 0)
    assert e.permits(t004, "summon") and e.permits(t004, "enter_bz")


def test_t422_own_turn_only(rules):
    """T422: 自分のターン中だけ、相手は多色ではないクリーチャーを出せない。"""
    e = setup(rules, {"bz": ["T422"]},
              {"hand": ["T001", "T030"], "mana": ["T001", "T001", "T004", "T003"]})
    t001 = _cid(e, 1, "T001", "hand")
    t030 = _cid(e, 1, "T030", "hand")
    assert not e.permits(t001, "summon")   # 自分のターン中: 単色は不可
    assert e.permits(t030, "summon")       # 多色は可
    d, keys = _drive(e, lambda d, k: d["kind"] == "main" and d["player"] == 1)
    assert e.permits(t001, "summon")       # 相手のターン: 制限は切れている
    assert "play:T001" in keys


def _break_shield_with_attack(e, attacker_defn):
    """p1 の attacker_defn で p0 を攻撃し、シールドを1枚ブレイクする。
    declare_strigger 決定が出た時の選択肢を返す（出なければ None）。"""
    seen_strigger = None
    for _ in range(600):
        if _in_hand(e, "T416"):
            break
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "declare_strigger":
            seen_strigger = keys
            e.answer([])
        elif d["kind"] == "attack" and d["player"] == 1 and f"attack:{attacker_defn}:player" in keys:
            e.answer([keys.index(f"attack:{attacker_defn}:player")])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_cards":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([keys.index("no")] if "no" in keys else [0])
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    assert _in_hand(e, "T416"), "shield was never broken"
    return seen_strigger


def _in_hand(e, defn):
    return any(e.s.cards[c].defn == defn for c in e.zlist("hand", 0))


def test_t423_strigger_denied(rules):
    """T423: 自分のシールドの S・トリガーは使えない（対照: 無ければ宣言できる）。"""
    # 対照: T423 が無ければ declare_strigger が出る
    e = setup(rules, {"shield": ["T416"]}, {"bz": ["T001"]})
    seen = _break_shield_with_attack(e, "T001")
    assert seen is not None and "strigger:T416" in seen
    assert _in_hand(e, "T416")
    # T423 があると declare_strigger 自体が出ない
    e = setup(rules, {"bz": ["T423"], "shield": ["T416"]}, {"bz": ["T001"]})
    seen = _break_shield_with_attack(e, "T001")
    assert seen is None
    assert _in_hand(e, "T416")
