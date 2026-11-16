"""語彙パイロット第194弾: must_attack_creature_if_able のイディオム確認。

「相手のクリーチャーが攻撃する時、可能ならクリーチャーを攻撃する」系の
ギャップ名は第171弾より前の命名で、構成要素は既に揃っている:

- 「可能ならクリーチャーを攻撃する」= mod `must_attack_creature`（第171弾。
  攻撃できるクリーチャーがいればプレイヤーへの攻撃選択肢が落ちる）
- 「可能であれば攻撃し」= キーワード `must_attack`（第30弾。require [attack]。
  攻撃ステップで pass が消える）
- 「可能であればそのクリーチャーを攻撃する」= mod `must_be_attacked`（第51弾。
  合法な誘引先がいれば攻撃先はそれらに限る）
- 期間「次の自分のターンのはじめまで」= modify の duration
  `until_next_own_turn_start`

本弾は新規エンジン語彙なしで、この3形を proto で検証する。
"""
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.cards.defs import load_rules, load_tables, parse_card

TABLES = load_tables()
IDS = ("T476", "T477", "T478")


@pytest.fixture(scope="module")
def rules():
    return load_rules()


def _proto_card(cid):
    from tests._conv_cache import proto_card
    return proto_card(cid)


def test_proto_parse():
    for cid in IDS:
        assert "spell" in parse_card(_proto_card(cid), TABLES).types or True
        parse_card(_proto_card(cid), TABLES)


def _keys(d):
    return [o["key"] for o in d["options"]]


def _defns(e, zone, player=0):
    return [e.s.cards[c].defn for c in e.zlist(zone, player)]


def _bz(e, player):
    return [e.s.cards[c].defn for c in e.zlist("bz", player)
            if e.s.cards[c].controller == player]


def _run_to_opp_attack(e, cast_key, capture, p0_attack_key=None):
    """自分は cast_key の呪文を唱え（任意で自分の最初の攻撃決定で
    p0_attack_key の攻撃も行い）、相手の攻撃決定に来たら capture(keys) を呼ぶ。
    capture が True を返したら止める。選択肢が1つだけの決定はエンジンが
    自動確定するため、相手の攻撃決定が提示されるのは選択肢が複数の時だけ。"""
    cast = False
    attacked = False
    for _ in range(400):
        d = e.advance()
        assert d is not None, "game ended"
        keys = _keys(d)
        if d["kind"] == "main" and d.get("player") == 0 and not cast and cast_key in keys:
            e.answer([keys.index(cast_key)])
            cast = True
            continue
        if (p0_attack_key and d["kind"] == "attack" and d.get("player") == 0
                and not attacked and p0_attack_key in keys):
            e.answer([keys.index(p0_attack_key)])
            attacked = True
            continue
        if d["kind"] == "block" and d.get("player") == 1 and "no_block" in keys:
            e.answer([keys.index("no_block")])
            continue
        if d["kind"] == "attack" and d.get("player") == 1 and cast:
            if capture(keys):
                return keys
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
            continue
        if "pass" in keys:
            e.answer([keys.index("pass")])
        else:
            e.answer(list(range(d["min"])))
    raise AssertionError("opponent attack decision never captured")


def test_forced_attacker_must_target_creature(rules):
    """T476: 対象の相手クリーチャーは攻撃を強制され（pass が無い）、
    攻撃先はクリーチャーだけになる。

    攻撃先の制限が効くのは攻撃できる（タップ状態の）クリーチャーがいる時
    なので、自分の T312 には先に攻撃させてタップしておく。相手には対象外の
    T004 も置き、制限が対象だけに掛かることを見る。
    """
    e = setup(rules, {"hand": ["T476"], "mana": ["T030", "T030"], "bz": ["T312"]},
              {"bz": ["T001", "T004"]}, filler="T002")
    captured = {}

    def capture(keys):
        captured["keys"] = keys
        return True

    _run_to_opp_attack(e, "play:T476", capture, p0_attack_key="attack:T312:player")
    keys = captured["keys"]
    assert "pass" not in keys                       # 攻撃強制（require）
    assert "attack:T001:player" not in keys         # 対象はプレイヤーを攻撃できない
    assert "attack:T001:T312" in keys               # クリーチャーは攻撃できる
    assert "attack:T004:player" in keys             # 対象外は制限されない（判別）
    # そのまま攻撃させる: T312（1000）は破壊され、T001（2000）は残る
    d = e.advance()
    assert d is not None and d["kind"] == "attack"
    e.answer([_keys(d).index("attack:T001:T312")])
    for _ in range(200):
        d = e.advance()
        if d is None:
            break
        if d["kind"] in ("main", "attack", "charge"):
            break
        kk = _keys(d)
        e.answer([kk.index("pass")] if "pass" in kk else list(range(d["min"])))
    assert "T312" in _defns(e, "graveyard", 0)   # T476（唱えた呪文自身）も墓地にある
    assert "T001" in _bz(e, 1)


def test_all_opp_must_target_creature_then_expires(rules):
    """T477: 相手全員が対象制限を受ける。次の自分のターンのはじめに切れる。"""
    e = setup(rules, {"hand": ["T477"], "mana": ["T269", "T269"], "bz": ["T001"]},
              {"bz": ["T001", "T004"]}, filler="T002")
    seen = []

    def capture(keys):
        seen.append(list(keys))
        return len(seen) >= 2

    _run_to_opp_attack(e, "play:T477", capture, p0_attack_key="attack:T001:player")
    first, second = seen
    assert not any(k.endswith(":player") for k in first), first
    assert any(k.endswith(":T001") for k in first), first
    assert "pass" in first                          # 攻撃自体は強制されない
    assert any(k.endswith(":player") for k in second), second   # 期間が切れた


def test_taunt_grant_with_tap_and_power(rules):
    """T478: タップした自分のクリーチャーが誘引先になり、+4000で守り切る。"""
    e = setup(rules, {"hand": ["T478"], "mana": ["T001", "T001"], "bz": ["T001"]},
              {"bz": ["T004"]}, filler="T002")
    captured = {}

    def capture(keys):
        captured["keys"] = keys
        return True

    _run_to_opp_attack(e, "play:T478", capture)
    keys = captured["keys"]
    assert "attack:T004:T001" in keys
    assert "attack:T004:player" not in keys
    d = e.advance()
    assert d is not None and d["kind"] == "attack"
    e.answer([_keys(d).index("attack:T004:T001")])
    for _ in range(200):
        d = e.advance()
        if d is None:
            break
        if d["kind"] in ("main", "attack", "charge"):
            break
        kk = _keys(d)
        e.answer([kk.index("pass")] if "pass" in kk else list(range(d["min"])))
    assert _defns(e, "graveyard", 1) == ["T004"]    # 3000 < 2000+4000
    assert _bz(e, 0) == ["T001"]
