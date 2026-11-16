"""語彙パイロット第213弾: suppress_entry_triggers（出た時能力の誘発抑制）。

2つの入口を新設した:

- move op の引数 no_trigger: true: その移動でバトルゾーンに出た
  カード自身の「出た時」能力は誘発しない（「それらのクリーチャーが
  出てそれらの能力がトリガーする時、かわりにトリガーしない」）。
  移動レコードに印を持たせ、誘発収集で発生源＝移動対象の時だけ落とす
- 常在型 suppress_triggers {whose: opp, events: [enter / attack, ...]}:
  相手のクリーチャーが出た／攻撃した出来事で誘発する、相手側の能力
  すべてを誘発させない（出た本人の能力に限らない）
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T537", "T538", "T539", "T540", "T541", "T542", "T543")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        parse_card(_proto_card(cid), TABLES)


def _hand(e, p):
    return len(e.zlist("hand", p))


def _in_bz(e, defn, ctrl=None):
    return any(e.s.cards[c].defn == defn and (ctrl is None or e.s.cards[c].controller == ctrl)
               for c in e.zlist("bz", 0))


def _drive(e, player, key, stop, limit=400):
    """player が key の行動を取るまで進める。行動直前の手札枚数を返す（ターン開始ドローを数えないため）。
    行動の後は stop() が真になり、かつ次の通常決定（main / charge）が来るまで流して誘発を解決し切る。"""
    acted = False
    before = None
    settled = False
    for _ in range(limit):
        if acted and stop():
            if settled:
                return before
        d = e.advance()
        if d is None:
            break
        keys = [o["key"] for o in d["options"]]
        if not acted and d.get("player") == player and d["kind"] in ("main", "attack") and key in keys:
            before = _hand(e, player)
            e.answer([keys.index(key)])
            acted = True
        elif acted and stop() and d["kind"] in ("main", "charge"):
            settled = True
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
        elif d["kind"] == "yes_no":
            e.answer([0])   # may は実行する
        elif d["kind"] == "pay_mana":
            e.answer(list(range(d["min"])))
        elif "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    return before


def _cast_put(rules, spell):
    """墓地の T537 を spell で出す。出した後の P0 手札枚数を返す。"""
    e = setup(rules, {"hand": [spell], "mana": ["T060", "T002"], "graveyard": ["T537"]},
              {}, filler="T002")
    before = _drive(e, 0, f"play:{spell}", lambda: _in_bz(e, "T537", 0))
    assert before is not None and _in_bz(e, "T537", 0)
    return _hand(e, 0) - (before - 1)   # 呪文1枚を消費した分を差し引いた増加分


def test_no_trigger_put_suppresses_own_cip(rules):
    # no_trigger つきで出すと、出た本人の CIP（ドロー）は誘発しない
    assert _cast_put(rules, "T538") == 0


def test_plain_put_fires_cip(rules):
    # 対照: 印なしで出すと CIP で1枚引く
    assert _cast_put(rules, "T539") == 1


def test_no_trigger_put_still_fires_observer(rules):
    # no_trigger が抑えるのは出た本人だけ。他の自分の観測誘発は誘発する
    e = setup(rules, {"hand": ["T538"], "mana": ["T060", "T002"], "graveyard": ["T537"],
                      "bz": ["T543"]},
              {}, filler="T002")
    before = _drive(e, 0, "play:T538", lambda: _in_bz(e, "T537", 0))
    assert before is not None and _in_bz(e, "T537", 0)
    # 観測獣のドローだけが効く（CIP は不発）
    assert _hand(e, 0) - (before - 1) == 1


def _summon537(rules, p0bz, p1bz=()):
    """P1 が T537 を通常召喚する。P1 の手札増加分（CIP+観測）を返す。"""
    e = setup(rules, {"bz": list(p0bz)},
              {"hand": ["T537"], "mana": ["T002", "T002", "T002"], "bz": list(p1bz)},
              filler="T002")
    before = _drive(e, 1, "play:T537", lambda: _in_bz(e, "T537", 1))
    assert before is not None and _in_bz(e, "T537", 1)
    return _hand(e, 1) - (before - 1)


def test_static_suppress_enter(rules):
    # 相手の抑制獣（enter）がいる時、P1 の CIP は誘発しない
    assert _summon537(rules, ["T540"]) == 0


def test_static_suppress_enter_control(rules):
    # 対照: 抑制獣がいなければ CIP で1枚引く
    assert _summon537(rules, []) == 1


def test_static_suppress_also_covers_observer(rules):
    # 抑制は出た本人に限らない: P1 の観測誘発も同じ出来事では誘発しない
    assert _summon537(rules, ["T540"], ["T543"]) == 0
    # 対照（抑制なし）: CIP 1枚＋観測 1枚
    assert _summon537(rules, [], ["T543"]) == 2


def test_static_suppress_does_not_cover_own_side(rules):
    # whose: opp — 自分のクリーチャーの登場は抑えられない
    e = setup(rules, {"hand": ["T537"], "mana": ["T002", "T002", "T002"], "bz": ["T540"]},
              {}, filler="T002")
    before = _drive(e, 0, "play:T537", lambda: _in_bz(e, "T537", 0))
    assert before is not None and _in_bz(e, "T537", 0)
    assert _hand(e, 0) - (before - 1) == 1


def test_static_suppress_attack(rules):
    # events: [enter, attack] の抑制獣は攻撃誘発も抑える
    def run(p1bz):
        e = setup(rules, {"bz": ["T542"]}, {"bz": list(p1bz)}, filler="T002")
        before = _drive(e, 0, "attack:T542:player", lambda: True, limit=120)
        assert before is not None
        return _hand(e, 0) - before
    assert run(["T541"]) == 0   # 攻撃誘発のドローは不発
    assert run([]) == 1         # 対照: 抑制がなければ1枚引く
    assert run(["T540"]) == 1   # enter だけの抑制では攻撃誘発は止まらない
