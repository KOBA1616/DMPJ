"""第3段その2b: 効果帰属レコード（バンドC2 基盤B1）と捨て札の帰属（バンドC1 U26）。

- move レコードに cause_defn / cause_kind（spell / ability）を常時載せ、when の cause で照合できる
- 収集済みレコードにも by が伝わる（従来 _apply_one が落としていて when:{by:} が捨て札で効かなかった）
- 手札ゾーンの発生源（捨てられた本人の誘発・置換）が、移動後のゾーンと発生源ゾーンの
  不一致でも拾える（_collect_triggers の lki 拡張）

proto: T252 捨て検知試験獣 / T253 捨てられ誘発試験獣 / T254 捨て置換試験獣 /
T255 呪文では離れない試験獣 / T256 除去試験呪文 / T257 破壊能力試験獣。
既存 proto: T117 強奪の呪文（相手に捨てさせる）/ T118 自捨の呪文（自分で捨てる）。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import DefError, load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def _names(e, p, zone):
    return sorted(e.s.cards[c].defn for c in e.zlist(zone, p))


def _boring(d):
    if d["kind"] in ("charge", "main", "attack"):
        keys = [o["key"] for o in d["options"]]
        for want in ("pass", "end_turn", "end_attack", "end_phase"):
            if want in keys:
                return [keys.index(want)]
        return [0]
    return [0]


def _go(e, pick=None, kinds=None, until=None, limit=600):
    """行動の解決が終わるまで進める。until が無ければ、解決後にターンの流れ
    （main / charge / attack の判断）へ戻った時点で止める（その判断は未回答で残す）。
    効果の解決中にはステップ判断は現れないので、最初のステップ判断が解決完了の合図になる。"""
    for _ in range(limit):
        d = e.advance()
        if d is None:
            return
        if until is not None and until():
            return
        if until is None and d["kind"] in ("main", "charge", "attack"):
            return
        if kinds is not None:
            kinds.append(d["kind"])
        ans = pick(d) if pick else None
        e.answer(ans if ans is not None else _boring(d))
    raise AssertionError("decisions did not settle")


def _to_main(e, player):
    for _ in range(600):
        d = e.advance()
        if d is None:
            raise AssertionError("game ended before main")
        if d["kind"] == "main" and d["player"] == player:
            return d
        e.answer(_boring(d))
    raise AssertionError("main not reached")


def _play(e, d, key_prefix):
    e.answer([next(i for i, o in enumerate(d["options"]) if o["key"].startswith(key_prefix))])


def test_proto_parse(rules):
    for cid in ("T252", "T253", "T254", "T255", "T256", "T257"):
        parse_card(_proto_card(cid), TABLES)
    bad = _proto_card("T255")
    bad["abilities"][0]["when"]["cause"] = {"kind": "bogus"}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)
    bad = _proto_card("T255")
    bad["abilities"][0]["when"]["cause"] = {"by": "bogus"}
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def test_discard_by_opp_spell_fires_hand_trigger(rules):
    """U26: 相手の呪文で捨てられた時、手札の本人の誘発（by: opp）が発火する。"""
    e = setup(rules, {"hand": ["T253", "T001"]}, {"hand": ["T117"], "mana": ["T266"] * 4})
    e.s.trace = []
    d = _to_main(e, 1)
    _play(e, d, "play:T117")

    def pick(dd):
        if dd["kind"] == "choose_cards":      # 強奪の呪文: 捨てる側(P0)が T253 を選ぶ
            return [next(i for i, o in enumerate(dd["options"]) if ":T253:" in o["key"])]
        return None
    _go(e, pick)
    assert "T253" in _names(e, 0, "graveyard")
    # 手札: 2 - 1（捨て） + 2（誘発ドロー） + 1（次の自ターン開始ドロー。_go は次ターンの
    # charge 判断で止まる） = 4。誘発が無ければ 2、二重発火なら 6 になる
    assert len(e.zlist("hand", 0)) == 4


def test_discard_by_own_spell_does_not_fire(rules):
    """U26: 自分の呪文で捨てた場合は by: opp に合わず発火しない（判別）。"""
    e = setup(rules, {"hand": ["T253", "T118"], "mana": ["T266"] * 2}, {})
    e.s.trace = []
    d = _to_main(e, 0)
    _play(e, d, "play:T118")

    def pick(dd):
        if dd["kind"] == "choose_cards":
            return [next(i for i, o in enumerate(dd["options"]) if ":T253:" in o["key"])]
        return None
    _go(e, pick)
    assert "T253" in _names(e, 0, "graveyard")
    assert len(e.zlist("hand", 0)) == 0       # ドローしていない（発火していれば 2 になる）


def test_watcher_fires_on_discard(rules):
    """U26: バトルゾーンの検知側（by: opp つき）は、相手の効果での捨て札でのみ発火する。
    収集済みレコードへの by の伝播（_apply_one の複写）が効いていることの確認を兼ねる。"""
    e = setup(rules, {"bz": ["T252"], "hand": ["T001", "T003"]},
              {"hand": ["T117"], "mana": ["T266"] * 4})
    d = _to_main(e, 1)
    _play(e, d, "play:T117")

    def pick(dd):
        if dd["kind"] == "choose_cards":
            return [next(i for i, o in enumerate(dd["options"]) if ":T001:" in o["key"])]
        return None
    _go(e, pick)
    assert "T001" in _names(e, 0, "graveyard")
    # 手札: 2 - 1（捨て） + 1（検知の誘発） + 1（次の自ターン開始ドロー） = 3。発火しなければ 2
    assert len(e.zlist("hand", 0)) == 3

    # 自分の呪文で捨てた場合は発火しない（判別）
    e = setup(rules, {"bz": ["T252"], "hand": ["T118", "T001"], "mana": ["T266"] * 2}, {})
    d = _to_main(e, 0)
    _play(e, d, "play:T118")
    _go(e, pick)
    assert "T001" in _names(e, 0, "graveyard")
    assert len(e.zlist("hand", 0)) == 0


def test_replace_fires_only_on_opponent_turn(rules):
    """U26: 手札の置換（メテオキャノン型）は相手のターン中の捨て札でのみ墓地行きを置き換える。"""
    e = setup(rules, {"hand": ["T254", "T001"]}, {"hand": ["T117"], "mana": ["T266"] * 4})
    d = _to_main(e, 1)
    _play(e, d, "play:T117")

    def pick(dd):
        if dd["kind"] == "choose_cards":
            return [next(i for i, o in enumerate(dd["options"]) if ":T254:" in o["key"])]
        return None
    _go(e, pick)
    assert "T254" in _names(e, 0, "bz")       # 墓地ではなくバトルゾーンに出た
    assert "T254" not in _names(e, 0, "graveyard")

    e = setup(rules, {"hand": ["T254", "T118"], "mana": ["T266"] * 5}, {})
    d = _to_main(e, 0)
    _play(e, d, "play:T118")
    _go(e, pick)
    assert "T254" in _names(e, 0, "graveyard")   # 自分のターンでは置換しない
    assert "T254" not in _names(e, 0, "bz")


def test_cause_spell_replacement_holds(rules):
    """B1/U108: 相手の呪文で離れる時は cause {kind: spell} の置換が合って場にとどまる。"""
    e = setup(rules, {"bz": ["T255"]}, {"hand": ["T256"], "mana": ["T266"] * 3})
    d = _to_main(e, 1)
    _play(e, d, "play:T256")
    _go(e)
    assert "T255" in _names(e, 0, "bz")
    assert "T255" not in _names(e, 0, "graveyard")


def test_cause_ability_does_not_hold(rules):
    """B1: 相手のクリーチャーの能力で離れる時は kind: spell に合わず置換しない（判別）。"""
    e = setup(rules, {"bz": ["T255"]}, {"hand": ["T257"], "mana": ["T266"] * 5})
    d = _to_main(e, 1)
    _play(e, d, "play:T257")
    _go(e)
    assert "T255" in _names(e, 0, "graveyard")
    assert "T255" not in _names(e, 0, "bz")


def test_cause_battle_has_no_cause(rules):
    """B1: バトルによる破壊は効果起因ではないので cause は付かず置換しない（判別）。"""
    e = setup(rules, {"bz": ["T255"]}, {"bz": ["T271"]})
    # まず P0 の T255 にプレイヤー攻撃させてタップさせる（攻撃できるのはタップ状態だけ）
    for _ in range(600):
        d = e.advance()
        assert d is not None
        if d["kind"] == "attack" and d["player"] == 0:
            e.answer([next(i for i, o in enumerate(d["options"]) if o["key"] == "attack:T255:player")])
            break
        e.answer(_boring(d))
    else:
        raise AssertionError("attack step not reached")
    # P1 の攻撃判断まで進める
    for _ in range(600):
        d = e.advance()
        assert d is not None
        if d["kind"] == "attack" and d["player"] == 1:
            break
        e.answer(_boring(d))
    else:
        raise AssertionError("attack step not reached")

    def pick(dd):
        if dd["kind"] == "attack":
            atk = [i for i, o in enumerate(dd["options"]) if o["key"].startswith("attack:") and "T255" in o["key"]]
            return atk[:1] or None
        return None
    atk = [i for i, o in enumerate(d["options"]) if o["key"].startswith("attack:") and "T255" in o["key"]]
    e.answer(atk[:1])
    _go(e, pick, until=lambda: "T255" not in _names(e, 0, "bz"))
    assert "T255" in _names(e, 0, "graveyard")
    assert "T255" not in _names(e, 0, "bz")
