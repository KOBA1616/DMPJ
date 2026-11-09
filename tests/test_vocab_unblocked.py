"""第2段・小パイロットその1: unblocked 小拡張（attack_end レコードへの blocked 追加）。

- attack タスクは phase 2 でブロック成立時に t["blocked"] を立てていたが、攻撃の終わりに
  作る attack_end レコード {ev, subject, target, controller, broke} へ伝播しておらず、
  「ブロックされなかった時」を when で書けなかった（gap unblocked_trigger、単独11件。
  設計 design-full-bandA.md の unblocked-trigger 単位）。
- 変更: combat.py の attack_end レコードに "blocked": bool(t.get("blocked")) を追加し、
  events.py の _match_when に broke と同じ形の blocked 照合を追加。defs.when は
  blocked が bool でなければ DefError とする検証を追加（schema にも blocked を追加）。
- ガードマンで攻撃先が変更された場合はブロックではない（507.2b。ブロッククリーチャーに
  ならない）ので、phase 2 は t["blocked"] を立てず blocked: false のままになる（正しい）。
- attack_end の発火条件自体は変えていない。攻撃が途中で取り除かれた場合に attack_end が
  発火するかは設計側でも未確定（公式確認待ち）のため、現行の発火範囲のまま記録だけを足す。
- 発火の観測はエンジンの trace（解決された誘発の因果記録）で attack_end の解決回数を数える。
- proto: T208（blocked: false、対象指定なし）／T209（blocked: true）／
  T210（target: player 併記。dmex15-a041 型）。
"""
from collections import Counter
from pathlib import Path

import pytest
import yaml
from conftest import setup

from dmsim.defs import DefError, card_yaml_files, load_rules, load_tables, parse_card

TABLES = load_tables()


@pytest.fixture(scope="session")
def rr():
    return load_rules(card_yaml_files() + [Path(__file__).parent / "rule_cards.yaml"])


def _proto_card(cid):
    with open(Path(__file__).parent.parent / "data" / "cards" / "proto.yaml") as f:
        data = yaml.safe_load(f)
    return next(c for c in data["cards"] if c["id"] == cid)


def _setup(*args, **kwargs):
    e = setup(*args, **kwargs)
    e.s.trace = []      # 誘発の因果記録を有効にする（発火回数の実測用）
    return e


def _fires(e, defn):
    return Counter(t["src"] for t in e.s.trace if t["ev"] == "attack_end")[defn]


def _flush(e, steps=60):
    for _ in range(steps):
        if not e.s.pending:
            return
        d = e.advance()
        if d is None:
            return
        keys = [o["key"] for o in d["options"]]
        e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))


def _run_attack(e, att_defn, block_key=None):
    """P0 のターンで att_defn がプレイヤーを攻撃し、P0 のターンが終わるまで進める。"""
    def drive(d, keys):
        if d["kind"] == "attack":
            e.answer([keys.index(f"attack:{att_defn}:player")])
            return True
        if d["kind"] == "choose_shields":
            e.answer([0])
            return True
        if d["kind"] == "block":
            e.answer([keys.index(block_key)] if block_key else [keys.index("no_block")])
            return True
        return False

    for _ in range(300):
        d = e.advance()
        if d is None or (d["player"] == 1 and d["kind"] == "charge"):
            return   # P1 の最初のチャージ判断＝P0 のターンは終わっている
        keys = [o["key"] for o in d["options"]]
        if not drive(d, keys):
            e.answer([keys.index("pass")] if "pass" in keys else list(range(d["min"])))
    raise AssertionError("turn did not end")


def test_proto_parse(rr):
    """T208〜T210 が parse でき、blocked の when が検証を通る。非 bool は DefError。"""
    for cid in ("T208", "T209", "T210"):
        parse_card(_proto_card(cid), TABLES)
    card = next(c for c in rr.cards.values() if c.id == "T208")
    assert card.face(None).abilities[0]["when"]["blocked"] is False
    bad = _proto_card("T208")
    bad["abilities"][0]["when"]["blocked"] = "no"
    with pytest.raises(DefError):
        parse_card(bad, TABLES)


def test_unblocked_fires(rr):
    """ブロックされなかった攻撃の終わりに、blocked: false の誘発が発火して1枚引く。"""
    e = _setup(rr, {"bz": ["T208"]}, {})
    _run_attack(e, "T208")
    _flush(e)
    assert _fires(e, "T208") == 1
    assert len(e.zlist("hand", 0)) == 1


def test_blocked_does_not_fire_unblocked_form(rr):
    """ブロックされた攻撃では blocked: false の誘発は発火しない。
    （攻撃先がブロッカーに移るため target でも外れるが、blocked の照合自体でも落ちることを、
    対象指定のない T208 で確認する）"""
    e = _setup(rr, {"bz": ["T208"]}, {"bz": ["T004"]})
    _run_attack(e, "T208", block_key="bz:T004:0")
    _flush(e)
    assert any(e.s.cards[c].defn == "T004" for c in e.zlist("graveyard", 1))   # バトルは行われた
    assert _fires(e, "T208") == 0
    assert len(e.zlist("hand", 0)) == 0


def test_blocked_true_form_fires_when_blocked(rr):
    """blocked: true の形は、ブロックされた攻撃の終わりにだけ発火する。"""
    e = _setup(rr, {"bz": ["T209"]}, {"bz": ["T004"]})
    _run_attack(e, "T209", block_key="bz:T004:0")
    _flush(e)
    assert _fires(e, "T209") == 1
    assert len(e.zlist("hand", 0)) == 1


def test_blocked_true_form_silent_when_unblocked(rr):
    """blocked: true の形は、ブロックされなかった攻撃では発火しない。"""
    e = _setup(rr, {"bz": ["T209"]}, {})
    _run_attack(e, "T209")
    _flush(e)
    assert _fires(e, "T209") == 0
    assert len(e.zlist("hand", 0)) == 0


def test_target_player_form(rr):
    """target: player との併記（dmex15-a041 型）: プレイヤーへの無封鎖攻撃で発火する。"""
    e = _setup(rr, {"bz": ["T210"]}, {})
    _run_attack(e, "T210")
    _flush(e)
    assert _fires(e, "T210") == 1
    assert len(e.zlist("hand", 0)) == 1
