"""語彙パイロット第159弾: first_attack_of_turn（そのターンはじめての攻撃）— 新語彙なし。

「そのターンはじめての攻撃であれば」は、攻撃レコードに刻まれる通し番号
（履歴基盤の ord）を when で照合して表す。新語彙は足さない。

- 煽動型（ターンの初回攻撃）: when {event: attack, subject: {owner: you, ...},
  ord: {kind: attack, eq: 1}}。ord の attack は攻撃側プレイヤーごとの通し番号なので、
  subject の owner と合わせて「自分のクリーチャーによる、そのターンの最初の攻撃」になる。
  相手のクリーチャーが対象なら subject owner: opp（ord も相手側の通し番号で数える）。
- 自分型（このクリーチャーのはじめての攻撃）: when {event: attack, subject: self,
  ord: {kind: attack_by, eq: 1}}。attack_by はクリーチャー単位の通し番号なので、
  ターンの最初の攻撃でなくても、このクリーチャー自身の初回なら発火する。
- 全体型（各ターン、はじめてクリーチャーが攻撃する時）: subject owner: any +
  ord {kind: attack, eq: 1}（攻撃は通常ターンプレイヤーだけが行うため、
  プレイヤーごとの eq 1 がターンの初回と一致する）。

proto T289（煽動型）/ T290（自分型）。実挙動で初回だけ発火することと、
attack と attack_by の区別（別クリーチャーが先に攻撃しても自分型は発火する）を確かめる。
"""
from collections import Counter
from pathlib import Path

import yaml
from conftest import setup

from dmsim.defs import load_tables, parse_card

TABLES = load_tables()


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def test_pilot159_proto_parse():
    for cid in ("T289", "T290"):
        parsed = parse_card(_proto_card(cid), TABLES)
        assert parsed.abilities[0]["when"]["ord"]["eq"] == 1


def _drive_to_attack(e, atk_key=None, max_steps=300):
    """攻撃判断まで既定回答で進める。atk_key があればその攻撃を選び、続けて次の攻撃判断を返す。"""
    for _ in range(max_steps):
        d = e.advance()
        assert d is not None, "game ended unexpectedly"
        keys = [o["key"] for o in d["options"]]
        if d["kind"] == "attack" and d["player"] == 0:
            if atk_key is not None and atk_key in keys:
                e.answer([keys.index(atk_key)])
                atk_key = None
                continue
            return d
        if d["kind"] == "pay_mana":
            e.answer([0])
        elif d["kind"] == "choose_shields":
            e.answer(list(range(d["min"])))
        elif d["kind"] == "block":
            e.answer([keys.index("no_block")])
        else:
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("attack decision not reached")


def _fires(e, defn):
    return Counter(t["src"] for t in e.s.trace if t["ev"] == "attack")[defn]


def _setup(*args, **kwargs):
    e = setup(*args, **kwargs)
    e.s.trace = []
    return e


def test_turn_first_attack_fires_only_on_first(rules):
    """煽動型 T289: 1回目の攻撃でだけ引き、2回目の攻撃では引かない。"""
    e = _setup(rules, {"bz": ["T289", "T001", "T005"]}, {})
    _drive_to_attack(e, "attack:T001:player")
    assert _fires(e, "T289") == 1
    assert len(e.zlist("hand", 0)) == 1
    _drive_to_attack(e, "attack:T005:player")
    assert _fires(e, "T289") == 1
    assert len(e.zlist("hand", 0)) == 1


def test_attack_by_fires_on_own_first_even_after_others(rules):
    """自分型 T290: 他のクリーチャーが先に攻撃した後でも、自身の初回攻撃で発火する。"""
    e = _setup(rules, {"bz": ["T290", "T001", "T005"]}, {})
    _drive_to_attack(e, "attack:T001:player")
    assert _fires(e, "T290") == 0
    _drive_to_attack(e, "attack:T290:player")
    assert _fires(e, "T290") == 1
    # 同じターンにアンタップして2回目を攻撃しても発火しない（attack_by は 2 になる）
    for c in e.zlist("bz", 0):
        if e.s.cards[c].defn == "T290":
            e.s.cards[c].tapped = False
    _drive_to_attack(e, "attack:T290:player")
    assert _fires(e, "T290") == 1
